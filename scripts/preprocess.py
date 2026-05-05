"""
Velib-Pulse — prétraitement des données
Convertit les CSV exportés depuis Supabase en un fichier data.json compact
utilisé par l'application statique heatmap.

Usage:
    py scripts/preprocess.py

Sortie:
    public/data.json  (~9 MB brut, ~2 MB gzippé par Vercel)

Format de sortie:
{
  "stations": [[lat, lon, "nom", capacite], ...],   // 1 entrée par station
  "data": {
    "1_0":   [[meca, ebike, docks], null, ...],     // key = "{dow}_{slot_min}"
    "1_15":  [...],                                  // valeur = tableau de N éléments
    ...                                              //   null si pas de données
  }
}
"""

import csv
import json
from pathlib import Path

BASE     = Path(__file__).parent.parent
DATA_DIR = BASE / "data"
OUT_FILE = BASE / "public" / "data.json"

STATIONS_CSV = DATA_DIR / "Station Information.csv"
AVAIL_CSV    = DATA_DIR / "Velib Aggregated Availability.csv"


def main() -> None:
    # ── 1. Stations ────────────────────────────────────────────────────────
    print("📍 Lecture des stations…")
    stations_meta: dict[str, dict] = {}
    with open(STATIONS_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            stations_meta[row["station_id"]] = {
                "lat": float(row["lat"]),
                "lon": float(row["lon"]),
                "name": row["name"],
                "cap": int(row["capacity"]),
            }

    # Ordre stable pour l'index
    station_ids  = list(stations_meta.keys())
    station_idx  = {sid: i for i, sid in enumerate(station_ids)}
    stations_arr = [
        [
            stations_meta[sid]["lat"],
            stations_meta[sid]["lon"],
            stations_meta[sid]["name"],
            stations_meta[sid]["cap"],
        ]
        for sid in station_ids
    ]
    N = len(station_ids)
    print(f"   → {N} stations")

    # ── 2. Disponibilités agrégées ─────────────────────────────────────────
    print("📊 Lecture des disponibilités agrégées…")
    data: dict[str, list] = {}
    skipped = 0

    with open(AVAIL_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i % 100_000 == 0 and i > 0:
                print(f"   {i:,} lignes lues…")

            sid = row["station_id"]
            if sid not in station_idx:
                skipped += 1
                continue

            key = f"{row['dow']}_{row['slot_min']}"
            if key not in data:
                data[key] = [None] * N

            data[key][station_idx[sid]] = [
                int(row["avg_mechanical"]),
                int(row["avg_ebike"]),
                int(row["avg_docks"]),
            ]

    print(f"   → {len(data)} créneaux (dow × slot_min)")
    if skipped:
        print(f"   ⚠ {skipped} lignes ignorées (station inconnue)")

    # ── 3. Écriture ────────────────────────────────────────────────────────
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    print(f"💾 Écriture de {OUT_FILE}…")

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {"stations": stations_arr, "data": data},
            f,
            ensure_ascii=False,
            separators=(",", ":"),  # compact, sans espaces
        )

    size_mb = OUT_FILE.stat().st_size / 1_000_000
    print(f"✅ Terminé — {OUT_FILE.name} ({size_mb:.1f} Mo)")
    print(f"   (Vercel servira ~{size_mb/4:.1f} Mo après gzip)")


if __name__ == "__main__":
    main()
