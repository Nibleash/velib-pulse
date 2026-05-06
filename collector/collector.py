"""Velib-Pulse collector — agrégation incrémentale (quota borné).

Au lieu de stocker des snapshots bruts, on UPSERT directement les sommes
dans aggregated_availability via RPC. Le stockage est borné à ~1 M lignes
quelles que soit la durée de collecte.
"""
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from supabase import create_client

STATION_STATUS_URL = "https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole/station_status.json"
STATION_INFO_URL   = "https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole/station_information.json"

PARIS_TZ = ZoneInfo("Europe/Paris")

supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])


def _build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=2,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


session = _build_session()


def _to_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _extract_bikes_by_type(status: dict) -> tuple[int, int]:
    mechanical = 0
    ebike = 0
    for bike_type in status.get("num_bikes_available_types", []):
        mechanical += _to_int(bike_type.get("mechanical"))
        ebike += _to_int(bike_type.get("ebike"))
    return mechanical, ebike


def fetch(url: str) -> list[dict]:
    response = session.get(url, timeout=10)
    response.raise_for_status()
    payload = response.json()
    return payload.get("data", {}).get("stations", [])


def upsert_station_info(stations: list[dict]) -> None:
    rows = [
        {
            "station_id": s["station_id"],
            "name":       s["name"],
            "lat":        s["lat"],
            "lon":        s["lon"],
            "capacity":   s["capacity"],
        }
        for s in stations
    ]
    # Passe par la RPC SECURITY DEFINER pour contourner RLS
    supabase.rpc("upsert_station_information", {"stations": rows}).execute()


def upsert_aggregated(statuses: list[dict], captured_at: datetime) -> None:
    """Incrémente les sommes dans aggregated_availability (pas de purge nécessaire)."""
    paris_time = captured_at.astimezone(PARIS_TZ)
    dow      = paris_time.isoweekday()                                     # 1=Lun…7=Dim
    slot_min = paris_time.hour * 60 + (paris_time.minute // 15) * 15      # 0…1425

    rows = []
    for status in statuses:
        if not (status.get("is_installed") and status.get("is_renting")):
            continue
        station_id = status.get("station_id")
        if station_id is None:
            continue
        meca, ebike = _extract_bikes_by_type(status)
        rows.append(
            {
                "station_id": station_id,
                "dow": dow,
                "slot_min": slot_min,
                "meca": meca,
                "ebike": ebike,
                "docks": _to_int(status.get("num_docks_available")),
            }
        )

    if not rows:
        print(f"[{captured_at.isoformat()}] ⚠ aucune station exploitable")
        return

    # Envoi en batch via la fonction RPC définie dans schema.sql
    supabase.rpc("upsert_aggregated_availability", {"snapshots": rows}).execute()


def run() -> None:
    now = datetime.now(timezone.utc)
    statuses = fetch(STATION_STATUS_URL)
    infos    = fetch(STATION_INFO_URL)

    upsert_station_info(infos)
    upsert_aggregated(statuses, now)
    print(f"[{now.isoformat()}] ✓ {len(statuses)} stations — agrégation incrémentale")


if __name__ == "__main__":
    run()
