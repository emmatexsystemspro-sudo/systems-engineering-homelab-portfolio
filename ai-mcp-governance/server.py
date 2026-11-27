import hashlib
import hmac
import json
import os
import re
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import psycopg2
import psycopg2.extras

DB_HOST = os.getenv("DB_HOST", "192.168.1.31")
DB_PORT = int(os.getenv("DB_PORT", "6433"))
DB_NAME = os.getenv("DB_NAME", "cluster_telemetry_mcp")
DB_USER = os.getenv("DB_USER", "mcp_readonly")
DB_PASSWORD = os.environ["DB_PASSWORD"]
MCP_API_TOKEN = os.getenv("MCP_API_TOKEN", "").strip()
LOKI_URL = os.getenv("LOKI_URL", "http://192.168.1")
MAX_ROWS = int(os.getenv("MAX_ROWS", "100"))
STATEMENT_TIMEOUT_MS = int(os.getenv("STATEMENT_TIMEOUT_MS", "3000"))

ALLOWED_TABLES = frozenset({
    "cluster_nodes",
    "node_telemetry",
    "performance_metrics",
    "replication_smoke_test",
    "system_logs",
    "telemetry_logs",
})

BLOCKED_TOKENS = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|copy|execute|prepare|deallocate|vacuum|analyze|cluster|reindex|lock|set|reset|show|listen|notify|do|call|merge|pg_sleep|pg_read_file|pg_read_binary_file|pg_ls_dir|pg_stat_file|lo_import|lo_export|dblink|pg_catalog|information_schema|pg_shadow|pg_authid|pg_roles|pg_user)\b",
    re.IGNORECASE,
)
TABLE_REF_PATTERN = re.compile(r"\b(?:from|join)\s+([a-zA-Z0-9_.\"']+)", re.IGNORECASE)


def emit_audit(event: dict) -> None:
    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "service": "governed-pg-mcp",
        **event,
    }
    line = json.dumps(record, default=str)
    print(line, flush=True)

    def _push():
        try:
            payload = json.dumps({
                "streams": [{
                    "stream": {
                        "job": "governed-pg-mcp",
                        "namespace": "lab-apps",
                        "status": record.get("status", "INFO"),
                        "tool": record.get("tool", "system"),
                    },
                    "values": [[str(time.time_ns()), line]],
                }]
            }).encode("utf-8")
            req = urllib.request.Request(
                LOKI_URL,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=2):
                pass
        except Exception as exc:
            print(json.dumps({"ts": record["ts"], "loki_push_error": str(exc)}), flush=True)

    threading.Thread(target=_push, daemon=True).start()


def validate_sql(raw_sql: str) -> tuple[bool, str, str]:
    if not raw_sql or not isinstance(raw_sql, str):
        return False, "Empty SQL query", ""
    cleaned = raw_sql.strip().rstrip(";").strip()
    if ";" in cleaned:
        return False, "Multi-statement SQL rejected by governance policy", ""
    if "--" in cleaned or "/*" in cleaned:
        return False, "SQL comments rejected by governance policy", ""
    if not re.match(r"^(select|with)\b", cleaned, re.IGNORECASE):
        return False, "Only SELECT queries are permitted", ""
    blocked_match = BLOCKED_TOKENS.search(cleaned)
    if blocked_match:
        return False, f"Blocked keyword or catalog referenced: {blocked_match.group(1)}", ""
    tables = TABLE_REF_PATTERN.findall(cleaned)
    if not tables:
        return False, "Query must reference at least one allowlisted table", ""
    for tbl in tables:
        norm = tbl.strip('"').strip("'").split(".")[-1].lower()
        if norm not in ALLOWED_TABLES:
            return False, f"Table '{norm}' is not in the governed allowlist", ""
    return True, "Policy check passed", cleaned


def run_readonly_query(sql: str, params=None) -> list[dict]:
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        connect_timeout=3,
        options=f"-c default_transaction_read_only=on -c statement_timeout={STATEMENT_TIMEOUT_MS}",
    )
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SET TRANSACTION READ ONLY;")
                cur.execute(sql, params)
                rows = cur.fetchall()
                return [dict(r) for r in rows]
    finally:
        conn.close()


TOOLS = [
    {
        "name": "list_allowed_tables",
        "description": "List PostgreSQL tables approved for read-only AI governance access in cluster_telemetry.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "describe_table",
        "description": "Return column names and data types for an allowlisted telemetry table.",
        "inputSchema": {
            "type": "object",
            "properties": {"table_name": {"type": "string"}},
            "required": ["table_name"],
            "additionalProperties": False,
        },
    },
    {
        "name": "query_telemetry",
        "description": "Execute a governed, read-only SELECT query against allowlisted cluster_telemetry tables (max 100 rows).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "Read-only SELECT query targeting allowlisted tables."},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 25},
            },
            "required": ["sql"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_replication_health",
        "description": "Run a curated health check across cluster_nodes and replication_smoke_test.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
]


def execute_tool(name: str, args: dict) -> dict:
    start = time.monotonic()
    if name == "list_allowed_tables":
        tables = sorted(ALLOWED_TABLES)
        emit_audit({"tool": name, "status": "ALLOWED", "row_count": len(tables), "duration_ms": round((time.monotonic() - start) * 1000, 2)})
        return {"content": [{"type": "text", "text": json.dumps({"allowed_tables": tables}, indent=2)}]}

    if name == "describe_table":
        tbl = str(args.get("table_name", "")).strip().lower()
        if tbl not in ALLOWED_TABLES:
            emit_audit({"tool": name, "status": "BLOCKED", "reason": f"Unapproved table: {tbl}", "duration_ms": round((time.monotonic() - start) * 1000, 2)})
            return {"isError": True, "content": [{"type": "text", "text": f"GOVERNANCE_BLOCKED: Table '{tbl}' is not in ALLOWED_TABLES."}]}
        rows = run_readonly_query(
            "SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_schema = 'public' AND table_name = %s ORDER BY ordinal_position",
            (tbl,),
        )
        emit_audit({"tool": name, "status": "ALLOWED", "table": tbl, "row_count": len(rows), "duration_ms": round((time.monotonic() - start) * 1000, 2)})
        return {"content": [{"type": "text", "text": json.dumps({"table": tbl, "columns": rows}, indent=2, default=str)}]}

    if name == "check_replication_health":
        nodes = run_readonly_query("SELECT * FROM cluster_nodes LIMIT 20")
        smoke = run_readonly_query("SELECT * FROM replication_smoke_test LIMIT 10")
        emit_audit({"tool": name, "status": "ALLOWED", "row_count": len(nodes) + len(smoke), "duration_ms": round((time.monotonic() - start) * 1000, 2)})
        return {"content": [{"type": "text", "text": json.dumps({"cluster_nodes": nodes, "replication_smoke_test": smoke}, indent=2, default=str)}]}

    if name == "query_telemetry":
        raw_sql = args.get("sql", "")
        sql_hash = hashlib.sha256(raw_sql.encode("utf-8")).hexdigest()[:16]
        ok, reason, cleaned_sql = validate_sql(raw_sql)
        if not ok:
            emit_audit({
                "tool": name,
                "status": "BLOCKED",
                "reason": reason,
                "sql_sha256": sql_hash,
                "sql_preview": raw_sql[:200],
                "duration_ms": round((time.monotonic() - start) * 1000, 2),
            })
            return {"isError": True, "content": [{"type": "text", "text": f"GOVERNANCE_BLOCKED: {reason}"}]}

        req_limit = int(args.get("limit", 25))
        safe_limit = max(1, min(req_limit, MAX_ROWS))
        bounded_sql = f"SELECT * FROM ({cleaned_sql}) AS _mcp_governed LIMIT {safe_limit}"
        try:
            rows = run_readonly_query(bounded_sql)
            emit_audit({
                "tool": name,
                "status": "ALLOWED",
                "reason": reason,
                "sql_sha256": sql_hash,
                "sql_preview": cleaned_sql[:200],
                "applied_limit": safe_limit,
                "row_count": len(rows),
                "duration_ms": round((time.monotonic() - start) * 1000, 2),
            })
            return {"content": [{"type": "text", "text": json.dumps({"row_count": len(rows), "applied_limit": safe_limit, "rows": rows}, indent=2, default=str)}]}
        except Exception as exc:
            emit_audit({
                "tool": name,
                "status": "ERROR",
                "reason": str(exc),
                "sql_sha256": sql_hash,
                "sql_preview": cleaned_sql[:200],
                "duration_ms": round((time.monotonic() - start) * 1000, 2),
            })
            return {"isError": True, "content": [{"type": "text", "text": f"DB_EXECUTION_ERROR: {exc}"}]}

    return {"isError": True, "content": [{"type": "text", "text": f"Unknown tool: {name}"}]}


class MCPHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def _send_json(self, code: int, body: dict):
        data = json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/healthz":
            self._send_json(200, {"status": "ok", "service": "governed-pg-mcp", "pool_port": DB_PORT})
        else:
            self._send_json(404, {"error": "Not found"})

    def _is_authorized(self) -> bool:
        if not MCP_API_TOKEN:
            return False
        auth_header = self.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return False
        supplied = auth_header[7:].strip()
        if not supplied:
            return False
        return hmac.compare_digest(supplied.encode("utf-8"), MCP_API_TOKEN.encode("utf-8"))

    def do_POST(self):
        if self.path != "/mcp":
            self._send_json(404, {"error": "Not found"})
            return
        if not self._is_authorized():
            forwarded = self.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            client_ip = forwarded or (self.client_address[0] if self.client_address else "unknown")
            emit_audit({
                "tool": "auth",
                "status": "UNAUTHORIZED",
                "reason": "Missing or invalid Bearer token",
                "client_ip": client_ip,
                "path": self.path,
            })
            self._send_json(
                401,
                {"jsonrpc": "2.0", "id": None, "error": {"code": -32001, "message": "Unauthorized: valid Bearer token required"}},
            )
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        try:
            req = json.loads(raw.decode("utf-8"))
        except Exception:
            self._send_json(400, {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}})
            return
        req_id = req.get("id")
        method = req.get("method", "")
        params = req.get("params") or {}
        if method == "initialize":
            self._send_json(200, {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "governed-pg-mcp", "version": "1.0.0"},
                    "capabilities": {"tools": {}},
                },
            })
        elif method == "notifications/initialized":
            self.send_response(204)
            self.end_headers()
        elif method == "tools/list":
            self._send_json(200, {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}})
        elif method == "tools/call":
            tool_name = params.get("name", "")
            tool_args = params.get("arguments") or {}
            result = execute_tool(tool_name, tool_args)
            self._send_json(200, {"jsonrpc": "2.0", "id": req_id, "result": result})
        else:
            self._send_json(200, {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method not found: {method}"}})

if __name__ == "__main__":
    emit_audit({"status": "STARTUP", "db_host": DB_HOST, "db_port": DB_PORT, "db_name": DB_NAME})
    server = ThreadingHTTPServer(("0.0.0.0", 8080), MCPHandler)
    server.serve_forever()
