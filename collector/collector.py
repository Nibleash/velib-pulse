"""Velib-Pulse collector — fetch GBFS every 15min and store in Supabase."""
import os
import requests
from datetime import datetime, timezone
from supabase import create_client

STATION_STATUS_URL = "https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole/station_status.json"
STATION_INFO_URL   = "https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole/station_information.json"

print(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
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
    supabase.table("station_information").upsert(rows).execute()


def insert_snapshots(stations: list[dict], captured_at: datetime) -> None:
    rows = [
        {
            "station_id":        s["station_id"],
            "captured_at":       captured_at.isoformat(),
            "mechanical":        next((t["mechanical"] for t in s["num_bikes_available_types"] if "mechanical" in t), 0),
            "ebike":             next((t["ebike"]      for t in s["num_bikes_available_types"] if "ebike"      in t), 0),
            "docks_available":   s["num_docks_available"],
        }
        for s in stations
        if s.get("is_installed") and s.get("is_renting")
    ]
    supabase.table("station_snapshots").insert(rows).execute()


def purge_old_snapshots() -> None:
    """Keep only 3 rolling weeks."""
    supabase.rpc("purge_old_snapshots").execute()


def run() -> None:
    now = datetime.now(timezone.utc)
    statuses = fetch(STATION_STATUS_URL)
    infos    = fetch(STATION_INFO_URL)

    upsert_station_info(infos)
    insert_snapshots(statuses, now)
    purge_old_snapshots()
    print(f"[{now.isoformat()}] ✓ {len(statuses)} stations collected")


if __name__ == "__main__":
    run()
