"""Serve the trading dashboard and its local account API."""

import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from trading import TradeError, buy_stock, get_state, init_db, sell_stock

INDEX = Path(__file__).with_name("index.html")
APP_JS = Path(__file__).with_name("app.js")
API_TOKEN = os.environ.get("FINANCE_API_TOKEN", "northstar-local-dev-token")


class Handler(BaseHTTPRequestHandler):
    def respond(self, status, body, content_type="application/json; charset=utf-8"):
        data = json.dumps(body).encode() if content_type.startswith("application/json") else body
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def authorized(self):
        supplied = self.headers.get("Authorization", "")
        if hmac.compare_digest(supplied, f"Bearer {API_TOKEN}"):
            return True
        self.respond(401, {"error": "Invalid API token"})
        return False

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length < 1 or length > 4096:
            raise TradeError("Invalid request size")
        data = json.loads(self.rfile.read(length))
        if not isinstance(data, dict):
            raise TradeError("Invalid order")
        return data

    def do_GET(self):
        path = urlsplit(self.path).path
        if path.startswith("/api/agent/"):
            if not self.authorized():
                return
            if path == "/api/agent/profile":
                profile = get_state()["profile"]
                name = "Investor" if profile["name"] == "Demo Investor" else profile["name"]
                return self.respond(200, {"name": name, "cash": profile["cash"]})
            if path == "/api/agent/portfolio":
                state = get_state()
                return self.respond(200, {"portfolio": state["portfolio"], "quotes": state["stocks"]})
            return self.respond(404, {"error": "Not found"})
        if path == "/api/state":
            return self.respond(200, get_state())
        if path in ("/", "/index.html"):
            return self.respond(200, INDEX.read_bytes(), "text/html; charset=utf-8")
        if path == "/app.js":
            return self.respond(200, APP_JS.read_bytes(), "application/javascript; charset=utf-8")
        self.respond(404, {"error": "Not found"})

    def do_POST(self):
        path = urlsplit(self.path).path
        if path not in ("/api/trade", "/api/agent/buy", "/api/agent/sell"):
            return self.respond(404, {"error": "Not found"})
        if path.startswith("/api/agent/") and not self.authorized():
            return
        try:
            data = self.read_json()
            side = data.get("side") if path == "/api/trade" else path.rsplit("/", 1)[-1]
            if side not in ("buy", "sell"):
                raise TradeError("Choose buy or sell.")
            result = (buy_stock if side == "buy" else sell_stock)(data.get("symbol"), data.get("quantity"))
            if path == "/api/trade":
                self.respond(200, {"trade": result, "state": get_state()})
            else:
                self.respond(200, {key: value for key, value in result.items() if key != "account_type"})
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self.respond(400, {"error": str(exc)})


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("FINANCE_PORT", "8000"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Trading app: http://127.0.0.1:{port}", flush=True)
    server.serve_forever()
