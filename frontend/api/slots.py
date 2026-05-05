"""Return the list of valid 15-min slots as HH:MM strings."""
from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        slots = [f"{m // 60:02d}:{m % 60:02d}" for m in range(0, 1440, 15)]
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(slots).encode())
