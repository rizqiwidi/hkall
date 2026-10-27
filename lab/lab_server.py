#!/usr/bin/env python3
"""hkall lab — vulnerable local test server (OWN DEVICE ONLY, binds 127.0.0.1).

Run:  python3 lab/lab_server.py [port]
Endpoints (semua read-only, untuk latihan modul websec):
  /sqli?x=...        SQLi: kalau x berisi quote/OR/-- -> HTTP 500 (vuln naive)
  /xss?q=...         XSS: echo q apa adanya (reflected, unescaped)
  /user/<id>         IDOR: id 1-3 -> 200 + data, id>3 -> 404
  /act               CSRF: no token, no SameSite (vuln)
  /load              load test: buat ddos/ab/wrk/siege
POST /...            echo body (buat latihan sqli POST)
"""
import sys
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, HTTPServer

class L(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _q(self, key):
        return parse_qs(urlparse(self.path).query).get(key, [""])[0]
    def _send(self, code, body):
        self.send_response(code)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        p = self.path
        if "sqli" in p:
            x = self._q("x")
            if "'" in x or '"' in x or "OR" in x.upper() or "--" in x:
                self._send(500, b"SQL ERROR: near quote")
            else:
                self._send(200, b"ok " + x.encode())
        elif "xss" in p:
            x = self._q("q")
            self._send(200, b"<html><body>hi " + x.encode() + b"</body></html>")  # reflected, unescaped
        elif "/user/" in p:
            i = p.rsplit("/", 1)[1]
            if i.isdigit() and int(i) <= 3:
                self._send(200, f"{{'id':{i},'name':'res{i}','secret':'s{i}'}}".encode())
            else:
                self._send(404, b"not found")
        elif p.startswith("/act"):
            self._send(200, b"no token checked")  # csrf-vulnerable
        elif p.startswith("/load"):
            self._send(200, b"load ok")
        else:
            self._send(200, b"lab")
    def do_POST(self):
        ln = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(ln).decode()
        self._send(200, b"posted:" + body.encode())

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8090
    print(f"lab server on http://127.0.0.1:{port}  (ctrl-c to stop)")
    HTTPServer(("127.0.0.1", port), L).serve_forever()
