"""Velib-Pulse collector — agrégation incrémentale (quota borné).

Au lieu de stocker des snapshots bruts, on UPSERT directement les sommes
dans aggregated_availability via RPC. Le stockage est borné à ~1 M lignes
quelles que soit la durée de collecte.
"""
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests
from supabase import create_client

STATION_STATUS_URL = "https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole/station_status.json"
STATION_INFO_URL   = "https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole/station_information.json"

PARIS_TZ = ZoneInfo("Europe/Paris")

supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])


def fetch(url: str) -> list[dict]:
    return requests.get(url, timeout=10).json()["data"]["stations"]


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

    rows = [
        {
            "station_id": s["station_id"],
            "dow":        dow,
            "slot_min":   slot_min,
            "meca":       next((t["mechanical"] for t in s["num_bikes_available_types"] if "mechanical" in t), 0),
            "ebike":      next((t["ebike"]      for t in s["num_bikes_available_types"] if "ebike"      in t), 0),
            "docks":      s["num_docks_available"],
        }
        for s in statuses
        if s.get("is_installed") and s.get("is_renting")
    ]

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
