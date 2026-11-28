import json, time, urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

LOG_PATH = "/var/log/governance-alerts.jsonl"
LOKI_URL = "http" + "://127.0.0.1:3100/loki/api/v1/push"

def push_loki(record):
    payload = {"streams": [{"stream": {"job": "governance-incident-alerts", "source": "grafana-unified-alerting", "environment": "homelab"}, "values": [[str(int(time.time() * 1e9)), json.dumps(record)]]}]}
    req = urllib.request.Request(LOKI_URL, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=3).read()

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode(errors="ignore")
        try:
            body = json.loads(raw) if raw else {}
        except Exception:
            body = {"raw": raw}
        alerts = body.get("alerts", ())
        record = {"received_at": int(time.time()), "status": body.get("status", "firing"), "alert_count": len(alerts), "title": body.get("title", "governance-alert"), "alerts": [{"status": a.get("status"), "labels": a.get("labels", {}), "annotations": a.get("annotations", {})} for a in alerts] if alerts else body}
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps(record) + "\n")
        try:
            push_loki(record)
        except Exception as e:
            print("Loki mirror error:", repr(e), flush=True)
        print("Recorded governance alert:", record.get("title"), flush=True)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ACCEPTED")
    def log_message(self, fmt, *args):
        pass

if __name__ == "__main__":
    print("Governance Webhook Receiver listening on 127.0.0.1:9095", flush=True)
    HTTPServer(("127.0.0.1", 9095), Handler).serve_forever()
