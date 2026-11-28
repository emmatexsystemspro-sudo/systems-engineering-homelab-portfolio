# Phase 22: Automated SIEM Alerting & Incident Webhook Response

## Executive Summary
Phase 22 transitions the platform governance architecture from passive dashboard visibility to automated incident detection, webhook dispatch, and lifecycle tracking (`FIRING` -> `RESOLVED`) using Grafana Unified Alerting and a zero-dependency incident webhook receiver on `sys6-monitoring`.

## Architecture & Automated Response Pipeline

### 1. Grafana Unified Alerting Rules (`ai-mcp-governance/grafana-governance-alerting.yaml`)
Provisioned declaratively into `/etc/grafana/provisioning/alerting/governance-siem-alerts.yaml` on `sys6-monitoring` (`192.168.1.36:3109`), evaluating Loki v3 (`ag1od8hot5728f`) every `30s`:
- **`KyvernoAdmissionDenialBurst` (`severity=high`, `governance=true`):** Fires immediately (`for: 0s`) when `sum(count_over_time({job="kyverno-admission-siem"}[5m])) > 2`, detecting repeated policy violations or brute-force admission probes in `lab-apps`.
- **`MCPBlockedSQLAttempt` (`severity=critical`, `governance=true`):** Fires immediately (`for: 0s`) when `sum(count_over_time({job="governed-pg-mcp"} |= "blocked" [5m])) > 0`, alerting on unauthorized DDL/DML SQL execution attempts.
- **Notification Policy & Contact Point (`governance-soar-webhook`):** Routes all `governance=true` alerts via HTTP `POST` to `127.0.0.1:9095/webhook`.

### 2. Governance Incident Webhook Receiver (`ai-mcp-governance/governance-webhook.py`)
- Runs as `governance-webhook.service` on `sys6-monitoring`, listening on `127.0.0.1:9095`.
- Appends structured JSON incident audit records (`received_at`, `status`, `alert_count`, `title`, `labels`, `annotations`) to `/var/log/governance-alerts.jsonl`.
- Mirrors every `FIRING` and `RESOLVED` incident record back into Loki v3 under `{job="governance-incident-alerts", source="grafana-unified-alerting"}` for unified forensic timeline correlation.

## Live Verification Evidence
- Triggered 3 consecutive non-compliant pod submissions (`alert-burst-test-1..3` with `nginx:latest` and missing governance labels/limits) in `lab-apps`.
- Kyverno rejected all 3 submissions at admission; `kyverno-siem-shipper` streamed the events to Loki; Grafana Unified Alerting evaluated the burst and fired `[FIRING:1] KyvernoAdmissionDenialBurst` (`21:46:09`) to `governance-webhook.service`, followed by `[RESOLVED] KyvernoAdmissionDenialBurst` (`21:52:09`) once the 5-minute window cleared.
