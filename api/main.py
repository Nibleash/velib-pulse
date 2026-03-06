"""Velib-Pulse API — aggregated availability per day-of-week & 15-min slot."""
import os
from typing import Literal
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client

app = FastAPI(title="Velib-Pulse API")

ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)

supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

BikeType = Literal["mechanical", "ebike", "docks"]

COLUMN = {
    "mechanical": "avg_mechanical",
    "ebike":      "avg_ebike",
    "docks":      "avg_docks",
}


@app.get("/availability")
def get_availability(
    dow:      int      = Query(..., ge=1, le=7, description="Day of week: 1=Mon … 7=Sun"),
    slot_min: int      = Query(..., ge=0, le=1425, multiple_of=15, description="Minutes since midnight, step 15"),
    type:     BikeType = Query("ebike"),
):
    """
    Returns averaged availability for every station for a given
    day-of-week + 15-min slot, joined with station coordinates.
    """
    col = COLUMN[type]

    rows = (
        supabase
        .table("aggregated_availability")
        .select(f"station_id, {col}")
        .eq("dow", dow)
        .eq("slot_min", slot_min)
        .execute()
        .data
    )

    # Enrich with lat/lon from station_information
    station_ids = [r["station_id"] for r in rows]
    geo = (
        supabase
        .table("station_information")
        .select("station_id, name, lat, lon")
        .in_("station_id", station_ids)
        .execute()
        .data
    )
    geo_map = {g["station_id"]: g for g in geo}

    return [
        {
            "station_id": r["station_id"],
            "name":       geo_map[r["station_id"]]["name"],
            "lat":        geo_map[r["station_id"]]["lat"],
            "lon":        geo_map[r["station_id"]]["lon"],
            "value":      r[col],
        }
        for r in rows
        if r["station_id"] in geo_map
    ]


@app.get("/slots")
def get_slots():
    """Returns the list of valid 15-min slots as HH:MM strings."""
    return [f"{m // 60:02d}:{m % 60:02d}" for m in range(0, 1440, 15)]
