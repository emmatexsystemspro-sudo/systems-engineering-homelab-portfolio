# Phase 21: Kyverno Admission SIEM Telemetry & Zero-Trust Network Micro-Segmentation

## Executive Summary
Phase 21 closes the runtime governance loop by connecting Kubernetes admission control (`Kyverno v1.20.0`) directly to centralized security telemetry (`Grafana Loki v3` on `sys6-monitoring`) and enforcing L3/L4 zero-trust micro-segmentation (`NetworkPolicy` via K3s embedded `kube-router`) across the `lab-apps` namespace.

## Architecture & Controls

### 1. Zero-Trust `NetworkPolicy` Micro-Segmentation (`policy-as-code/network-policies.yaml`)
All pods in `lab-apps` operate under a strict default-deny posture (`default-deny-all` covering both `Ingress` and `Egress`), with explicit least-privilege allow rules:
- **`default-deny-all`:** Denies all unsolicited ingress and egress traffic across `lab-apps` (`podSelector: {}`).
- **`allow-dns-egress`:** Permits `UDP/53` and `TCP/53` to `kube-system` CoreDNS pods (`k8s-app=kube-dns`) and the `10.43.0.10/32` cluster DNS service VIP.
- **`governed-pg-mcp-netpol`:**
  - *Ingress:* Allows `TCP/8080` exclusively from homelab LAN (`192.168.1.0/24`) and cluster pod CIDR (`10.42.0.0/16`).
  - *Egress:* Permits `TCP/6433` to `192.168.1.31/32` (PgBouncer/HAProxy pooler), `TCP/5543` to `192.168.1.35/32` (`Sys7-databasehost`), and `TCP/3100` to `192.168.1.36/32` (`sys6-monitoring` Loki ingestion).
- **`ha-telemetry-dashboard-netpol`:**
  - *Ingress:* Allows `TCP/3000` (backing `NodePort 30080`) from `192.168.1.0/24` and `10.42.0.0/16`.
  - *Egress:* Permits `TCP/5432` and `TCP/6433` to `192.168.1.31/32`.

### 2. Kyverno Admission & Policy Violation SIEM Forwarder (`policy-as-code/kyverno-loki-shipper.yaml`)
- Deployed as a lightweight (`15m` CPU / `32Mi` RAM request) RBAC-scoped pod (`kyverno-siem-shipper`) pinned to `sys3-databasehost` using the hardened local `localhost/governed-pg-mcp:v2` image.
- Watches Kubernetes `Event` resources (`PolicyViolation`, `FailedCreate`, admission rejections) and Kyverno admission controller logs, shipping structured JSON events to Grafana Loki v3 (`192.168.1.36:3100`) under `{job="kyverno-admission-siem"}`.
- Restored Loki v3 TSDB `schema_config` (`v13`, `filesystem` object store) on `sys6-monitoring` and extended `ai-mcp-governance/grafana-mcp-governance-dashboard.json` with Panel 8 (`Kyverno Admission Denials & Policy Events (5m Rate)`) and Panel 9 (`Live Kyverno Admission & Policy Violation Audit Stream`).

## Verification Evidence
- **Positive Connectivity:** `governed-pg-mcp` (`10.43.36.140:8080`) verified reachable (`MCP_INGRESS_8080_ALLOWED`) and CoreDNS resolution verified (`10.43.0.1`).
- **Negative Isolation Probe:** Ephemeral compliant `busybox:1.36` pod in `lab-apps` blocked from unauthorized egress to `192.168.1.35:5543` (`EGRESS_5543_BLOCKED_AS_EXPECTED`).
- **Admission SIEM Telemetry:** Synthetic non-compliant workload (`nginx:latest` without governance labels or resource limits) rejected by `vpol.validate.kyverno.svc-fail` across 3 `ValidatingPolicy` rules and ingested into Loki (`Shipped 47 admission/policy events to Loki`, `Loki_Kyverno_Streams: 1`).
- **Shift-Left CI Gate:** `.github/workflows/policy-as-code-ci.yml` extended with `network-policy-and-siem-validation` enforcing metadata governance labels and SIEM dashboard integrity on every push/PR.
