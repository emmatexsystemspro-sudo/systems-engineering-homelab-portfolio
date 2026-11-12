# Case study 05 — PostgreSQL streaming replication and PgBouncer

## Problem
A single database host represented a complete database failure domain. The next phase explored a physically separate standby and application-friendly connection pooling.

## What I built
I configured a PostgreSQL 15 primary on a rootless Podman host and provisioned a separate Hyper-V standby VM. On the primary, I prepared a physical replication slot. On the standby, I initialized data with PostgreSQL base-backup tooling, corrected host and container ownership, and brought the replica container online. A phase 8 handover report states the standby was **ingesting the primary's live WAL stream**.

Next, I configured two PgBouncer service instances using systemd units: a primary transaction-pooling path and a separate standby-oriented connection path. Phase 9 reports document the host/port routing and status verification. These are laboratory results from the reports, not continuously monitored production uptime evidence.

## Validation approach
- `pg_is_in_recovery()` differentiates a standby from a writable primary.
- `pg_stat_replication` and `pg_stat_wal_receiver` help verify live replication.
- A test transaction followed by a read on the replica can verify data movement.
- Pooler tests must verify a correct backend, authentication, and expected transaction semantics.

## Risks and design caveats
A physical replica is generally read-only until promotion. Connection pooling **does not itself perform promotion**. PgBouncer statement-pooling mode also imposes query/transaction compatibility constraints. Real failover requires correct fencing and prevention of both nodes accepting writes concurrently. The lab reports contain multiple conflicting node-IP assignments; all exact addresses were intentionally removed from public examples.

[Back to overview](../README.md)

## November 2026 Phase 15 update

The final validated role assignment differed from the earlier Phase 8 design: the writable primary was a Linux Hyper-V guest and the streaming standby was a separate bare-metal Linux host. Both PgBouncer connection paths and WAL replay were verified. [Phase 15 validation](13-phase15-replication-monitoring.md).
