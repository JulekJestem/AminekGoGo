"""Tiny local web server and same-origin proxy for AminekGoGo's live spawn feed."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen
from threading import Lock
from time import monotonic, sleep
import json

UPSTREAM = "https://pokecoords.iflowgo.com/iflowgopokecoords/api/v1/nearby"
ALLOWED = {"lat", "lon", "radius_km", "layers", "limit"}
PHOTON = "https://photon.komoot.io/api/"
GEOCODE_CACHE = {}
GEOCODE_LOCK = Lock()
LAST_GEOCODE = 0.0


class AminekGoGoHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/api/geocode":
            return self.geocode(parse_qs(urlsplit(self.path).query))
        if path != "/api/nearby":
            return super().do_GET()

        params = parse_qs(urlsplit(self.path).query)
        query = {key: params[key][0] for key in ALLOWED if params.get(key)}
        try:
            lat, lon = float(query["lat"]), float(query["lon"])
            radius = float(query.get("radius_km", "25"))
            if not -90 <= lat <= 90 or not -180 <= lon <= 180:
                raise ValueError("Coordinates are out of range")
            if not 1 <= radius <= 25:
                raise ValueError("Radius must be between 1 and 25 km")
            query["layers"] = "spawns"
            query["limit"] = "800"
        except (KeyError, ValueError) as error:
            return self.send_json(400, {"error": str(error)})

        request = Request(
            f"{UPSTREAM}?{urlencode(query)}",
            headers={"Accept": "application/json", "User-Agent": "AminekGoGo local web app"},
        )
        try:
            with urlopen(request, timeout=25) as response:
                body = response.read()
                self.send_response(response.status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        except HTTPError as error:
            self.send_json(error.code, {"error": f"iFlowGo returned HTTP {error.code}"})
        except (URLError, TimeoutError) as error:
            self.send_json(502, {"error": f"Could not reach iFlowGo: {error}"})

    def geocode(self, params):
        global LAST_GEOCODE
        query = (params.get("q", [""])[0] or "").strip()[:160]
        if len(query) < 2:
            return self.send_json(400, {"error": "Enter at least two characters to search."})
        cache_key = query.casefold()
        cached = GEOCODE_CACHE.get(cache_key)
        if cached:
            return self.send_json(200, cached)

        upstream_params = {"q": query, "limit": "5", "lang": "en"}
        request = Request(
            f"{PHOTON}?{urlencode(upstream_params)}",
            headers={"Accept": "application/json", "User-Agent": "AminekGoGo/1.0 (local Pokémon GO spawn radar)"},
        )
        try:
            # Keep this single-process public demo client below one request per second.
            with GEOCODE_LOCK:
                pause = 1.0 - (monotonic() - LAST_GEOCODE)
                if pause > 0:
                    sleep(pause)
                LAST_GEOCODE = monotonic()
                with urlopen(request, timeout=20) as response:
                    data = json.loads(response.read().decode("utf-8"))
            GEOCODE_CACHE[cache_key] = data
            return self.send_json(200, data)
        except HTTPError as error:
            self.send_json(error.code, {"error": f"Place search returned HTTP {error.code}"})
        except (URLError, TimeoutError, ValueError) as error:
            self.send_json(502, {"error": f"Could not reach place search: {error}"})

    def send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    print("AminekGoGo is running at http://localhost:8000")
    ThreadingHTTPServer(("127.0.0.1", 8000), AminekGoGoHandler).serve_forever()
