import http.client
import json
import os
import sys
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

# Set required env vars before importing server.py
os.environ.setdefault("DB_PASSWORD", "ci-dummy-password")
os.environ.setdefault("MCP_API_TOKEN", "test-secret-token-256bit")
os.environ.setdefault("LOKI_URL", "http://127.0.0")

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import server  # noqa: E402


@pytest.fixture
def live_mcp_server(monkeypatch):
    monkeypatch.setattr(server, "MCP_API_TOKEN", "test-secret-token-256bit")
    audits = []

    def fake_emit(event: dict) -> None:
        audits.append(event)

    monkeypatch.setattr(server, "emit_audit", fake_emit)

    httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.MCPHandler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield port, audits
    finally:
        httpd.shutdown()
        httpd.server_close()


# --- 1. SQL Governance Policy Tests ---

@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM cluster_nodes",
        "SELECT node_name, cpu_pct FROM node_telemetry WHERE cpu_pct > 80;",
        "SELECT s.message, c.node_name FROM system_logs s JOIN cluster_nodes c ON s.node_id = c.id",
        "SELECT * FROM public.performance_metrics",
    ],
)
def test_validate_sql_allows_valid_selects(sql):
    ok, reason, cleaned = server.validate_sql(sql)
    assert ok is True
    assert reason == "Policy check passed"
    assert not cleaned.endswith(";")


@pytest.mark.parametrize(
    "sql,expected_fragment",
    [
        ("", "Empty SQL"),
        ("   ", "Only SELECT queries are permitted"),
        ("SELECT * FROM cluster_nodes; DROP TABLE cluster_nodes;", "Multi-statement"),
        ("SELECT * FROM cluster_nodes -- comment", "SQL comments"),
        ("SELECT * FROM cluster_nodes /* block */", "SQL comments"),
        ("EXPLAIN SELECT * FROM cluster_nodes", "Only SELECT"),
        ("INSERT INTO cluster_nodes VALUES ('n1')", "Only SELECT"),
        ("UPDATE cluster_nodes SET status='down'", "Only SELECT"),
        ("DELETE FROM cluster_nodes", "Only SELECT"),
        ("SELECT * FROM cluster_nodes WHERE 1=1 UNION SELECT * FROM pg_shadow", "Blocked keyword or catalog"),
        ("SELECT pg_sleep(10) FROM cluster_nodes", "Blocked keyword or catalog"),
        ("SELECT * FROM information_schema.tables", "Blocked keyword or catalog"),
        ("SELECT * FROM pg_catalog.pg_roles", "Blocked keyword or catalog"),
        ("SELECT 1", "must reference at least one allowlisted table"),
        ("SELECT * FROM unauthorized_secret_table", "not in the governed allowlist"),
        ("SELECT * FROM cluster_nodes JOIN secrets_vault ON 1=1", "not in the governed allowlist"),
    ],
)
def test_validate_sql_blocks_violations(sql, expected_fragment):
    ok, reason, _ = server.validate_sql(sql)
    assert ok is False
    assert expected_fragment in reason


# --- 2. Row Limit Clamping & Tool Execution Tests ---

def test_query_telemetry_clamps_row_limits(monkeypatch):
    captured_sql = []

    def fake_query(sql, params=None):
        captured_sql.append(sql)
        return [{"node": "sys2-controller"}]

    monkeypatch.setattr(server, "run_readonly_query", fake_query)
    monkeypatch.setattr(server, "emit_audit", lambda e: None)

    # Excessive limit clamped to MAX_ROWS (100)
    res_high = server.execute_tool("query_telemetry", {"sql": "SELECT * FROM cluster_nodes", "limit": 9999})
    assert res_high.get("isError") is not True
    assert "LIMIT 100" in captured_sql[-1]

    # Zero/negative limit clamped to 1
    res_low = server.execute_tool("query_telemetry", {"sql": "SELECT * FROM cluster_nodes", "limit": -5})
    assert res_low.get("isError") is not True
    assert "LIMIT 1" in captured_sql[-1]


def test_describe_table_enforces_allowlist(monkeypatch):
    monkeypatch.setattr(server, "emit_audit", lambda e: None)
    res = server.execute_tool("describe_table", {"table_name": "pg_shadow"})
    assert res["isError"] is True
    assert "GOVERNANCE_BLOCKED" in res["content"][0]["text"]


# --- 3. Constant-Time Bearer Auth & 401 Audit Emission Tests ---

def test_healthz_unauthenticated(live_mcp_server):
    port, _ = live_mcp_server
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    conn.request("GET", "/healthz")
    resp = conn.getresponse()
    body = json.loads(resp.read().decode("utf-8"))
    assert resp.status == 200
    assert body["status"] == "ok"


@pytest.mark.parametrize(
    "auth_header",
    [
        None,
        "",
        "Basic dXNlcjpwYXNz",
        "Bearer ",
        "Bearer wrong-token-value",
    ],
)
def test_mcp_rejects_unauthorized_and_emits_audit(live_mcp_server, auth_header):
    port, audits = live_mcp_server
    headers = {"Content-Type": "application/json"}
    if auth_header is not None:
        headers["Authorization"] = auth_header

    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    conn.request("POST", "/mcp", body=payload, headers=headers)
    resp = conn.getresponse()
    body = json.loads(resp.read().decode("utf-8"))

    assert resp.status == 401
    assert body["error"]["code"] == -32001
    assert len(audits) == 1
    assert audits[0]["status"] == "UNAUTHORIZED"
    assert audits[0]["tool"] == "auth"


def test_mcp_accepts_valid_bearer_token(live_mcp_server):
    port, audits = live_mcp_server
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer test-secret-token-256bit",
    }
    payload = json.dumps({"jsonrpc": "2.0", "id": 42, "method": "tools/list"})
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    conn.request("POST", "/mcp", body=payload, headers=headers)
    resp = conn.getresponse()
    body = json.loads(resp.read().decode("utf-8"))

    assert resp.status == 200
    assert body["id"] == 42
    assert len(body["result"]["tools"]) == 4
    assert len(audits) == 0


def test_emit_audit_pushes_loki_payload(monkeypatch):
    captured = {}
    done = threading.Event()

    class DummyResp:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(req, timeout=2):
        captured["url"] = req.full_url
        captured["data"] = json.loads(req.data.decode("utf-8"))
        done.set()
        return DummyResp()

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        server.emit_audit({"tool": "auth", "status": "UNAUTHORIZED", "reason": "test"})
        assert done.wait(timeout=2), "Background Loki push thread did not execute"

    stream = captured["data"]["streams"][0]
    assert stream["stream"]["job"] == "governed-pg-mcp"
    assert stream["stream"]["status"] == "UNAUTHORIZED"
    assert stream["stream"]["tool"] == "auth"
