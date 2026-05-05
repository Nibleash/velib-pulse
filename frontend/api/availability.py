"""Velib-Pulse API — aggregated availability per day-of-week & 15-min slot."""
import os
from urllib.parse import parse_qs
from http.server import BaseHTTPRequestHandler
from supabase import create_client

supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

COLUMN = {
    "mechanical": "avg_mechanical",
    "ebike":      "avg_ebike",
    "docks":      "avg_docks",
}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query_string = self.path.split('?', 1)[1] if '?' in self.path else ''
        params = parse_qs(query_string)
        
        dow = int(params.get('dow', [1])[0])
        slot_min = int(params.get('slot_min', [480])[0])
        type_param = params.get('type', ['ebike'])[0]
        
        col = COLUMN.get(type_param, "avg_ebike")
        
        rows = (
            supabase
            .table("aggregated_availability")
            .select(f"station_id, {col}")
            .eq("dow", dow)
            .eq("slot_min", slot_min)
            .execute()
            .data
        )
        
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
        
        result = [
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
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        import json
        self.wfile.write(json.dumps(result).encode())
