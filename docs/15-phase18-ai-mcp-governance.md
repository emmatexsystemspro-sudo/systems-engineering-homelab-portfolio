# Phase 18 — Read-Only PostgreSQL MCP Server & AI Governance Guardrails

## Overview
Phase 18 introduces a **governed Model Context Protocol (MCP) server** (`governed-pg-mcp`) running on K3s (`namespace: lab-apps`, worker `sys3-databasehost`) that exposes cluster telemetry from PostgreSQL 15 to AI agents through **defense-in-depth governance controls**. Every layer—from Kubernetes pod security to SQL AST/token validation, PgBouncer transaction pooling, PostgreSQL role privileges, and immutable Loki audit streaming—enforces strict least-privilege read-only boundaries.

## Defense-in-Depth Architecture

```text
[AI Agent / MCP Client]
         │  JSON-RPC 2.0 (POST /mcp)
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ K3s Pod: governed-pg-mcp (sys3-databasehost / 192.168.1.32)      │
│ • Non-root UID 10001, readOnlyRootFilesystem, drop ALL caps     │
│ • Policy Engine: SELECT-only, 6-table allowlist, catalog block  │
│ • Row Ceiling: enforced LIMIT <= 100 + BEGIN READ ONLY          │
└───────────┬─────────────────────────────────────┬───────────────┘
            │ SCRAM-SHA-256 (port 6433)           │ Async HTTP Push
            ▼                                     ▼
┌───────────────────────────────┐   ┌─────────────────────────────┐
│ PgBouncer Standby Pooler      │   │ Grafana Loki (192.168.1.36) │
│ (sys2-controller:6433)        │   │ • Stream: {job="governed-   │
│ • Alias: cluster_telemetry_mcp│   │   pg-mcp"}                  │
│ • pool_mode = transaction     │   │ • Logs ts, status, reason,  │
└───────────┬───────────────────┘   │   sql_sha256, duration_ms   │
            │                       └─────────────────────────────┘
            ▼
┌───────────────────────────────────────────────────────────────┐
│ PostgreSQL 15 Standby Replica (sys3-databasehost:5543)        │
│ • Role: mcp_readonly (SELECT-only on approved public tables)  │
│ • default_transaction_read_only = on, statement_timeout = 3s  │
└───────────────────────────────────────────────────────────────┘
```

## Multi-Layer Governance Controls

| Layer | Control Mechanism | Enforcement Detail |
| :--- | :--- | :--- |
| **Runtime & K8s** | Pod Security Hardening | Runs as `UID 10001`, `allowPrivilegeEscalation: false`, `readOnlyRootFilesystem: true`, `capabilities.drop: ["ALL"]`, `RuntimeDefault` seccomp profile. |
| **MCP Policy Gate** | SQL Validation & Allowlist | Rejects non-`SELECT` statements, multi-statement `;` chaining, system catalogs (`pg_shadow`, `pg_roles`, `pg_authid`, `information_schema`), and tables outside the 6-table allowlist. |
| **Query Bounding** | Row & Transaction Caps | Wraps approved queries with a hard `LIMIT <= 100` ceiling inside an explicit `BEGIN READ ONLY` transaction block. |
| **Connection Pool** | Dedicated Standby Alias | Routes exclusively through `cluster_telemetry_mcp` on `192.168.1.31:6433` (`pool_mode = transaction`), isolating AI workloads from the primary writer (`192.168.1.35`). |
| **Database Engine** | Least-Privilege Role | `mcp_readonly` role enforces `default_transaction_read_only = on` and `statement_timeout = 3000ms` at the PostgreSQL session level. |
| **Audit & SIEM** | Real-Time Loki Telemetry | Emits structured JSON audit records (`ALLOWED`, `BLOCKED`, `STARTUP`, `sql_sha256`, `row_count`, `duration_ms`) asynchronously to Loki (`192.168.1.36:3100`). |

## Governance Verification Proof

### 1. Positive Test — Approved Allowlist Query
* **Request (`tools/call` -> `query_telemetry`)**: `SELECT * FROM cluster_nodes LIMIT 10`
* **Result**: `ALLOWED` — returned `row_count: 3` (`sys2-controller`, `sys3-databasehost`, `sys7-databasehost`) from the standby replica in `123.6 ms`.

### 2. Negative Test — DDL Mutation Attempt (`DROP TABLE`)
* **Request**: `DROP TABLE cluster_nodes`
* **Result**: `GOVERNANCE_BLOCKED: Only SELECT queries are permitted` (`0.09 ms`, blocked prior to database connection).

### 3. Negative Test — Credential Catalog Enumeration (`pg_shadow`)
* **Request**: `SELECT usename, passwd FROM pg_shadow`
* **Result**: `GOVERNANCE_BLOCKED: Blocked keyword or catalog referenced: pg_shadow`

### 4. Negative Test — Unapproved Table Access (`secret_audit`)
* **Request**: `SELECT * FROM secret_audit LIMIT 5`
* **Result**: `GOVERNANCE_BLOCKED: Table 'secret_audit' is not in the governed allowlist`

### 5. Central Audit Verification in Loki (`{job="governed-pg-mcp"}`)
Verified via `GET /loki/api/v1/query_range?query={job="governed-pg-mcp"}` against `192.168.1.36:3100`:
* `STARTUP`: `{"status": "STARTUP", "db_host": "192.168.1.31", "db_port": 6433, "db_name": "cluster_telemetry_mcp"}`
* `ALLOWED`: `{"status": "ALLOWED", "sql_sha256": "736f1f757671060e", "applied_limit": 25, "row_count": 3, "duration_ms": 149.72}`
* `BLOCKED`: `{"status": "BLOCKED", "reason": "Only SELECT queries are permitted", "sql_sha256": "e4d28cf6dfe4b778", "duration_ms": 0.12}`

## Engineering & Troubleshooting Resolutions
1. **PgBouncer Startup Parameters & Transaction Mode**: Added `ignore_startup_parameters = extra_float_digits,options` and updated `pool_mode = transaction` in `/etc/pgbouncer/pgbouncer-standby.ini` so `psycopg2` startup options and `BEGIN READ ONLY` transaction blocks execute cleanly without `long transactions not allowed` disconnects.
2. **Cross-Subnet Pod-to-Loki Egress Routing**: Configured a persistent `firewalld` direct `POSTROUTING` `MASQUERADE` rule (`10.42.0.0/16 -> 192.168.1.0/24`) on worker node `sys3-databasehost` (`192.168.1.32`) to prevent asymmetric return-path drops when pods push audit streams to `sys6-monitoring` (`192.168.1.36:3100`).
