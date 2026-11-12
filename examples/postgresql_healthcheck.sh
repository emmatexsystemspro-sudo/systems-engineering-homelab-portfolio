#!/usr/bin/env bash
# Read-only PostgreSQL readiness check; safe example, not an HA/fencing system.
set -euo pipefail
: "${PGHOST:?Set PGHOST to a validated database hostname}"
: "${PGPORT:=5432}"
: "${PGUSER:?Set PGUSER to a read-only or health-check user}"
: "${PGDATABASE:=postgres}"

if pg_isready -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -t 3; then
  printf 'Database readiness probe succeeded.\n'
else
  printf 'Database readiness probe failed. Investigate before taking failover action.\n' >&2
  exit 1
fi
