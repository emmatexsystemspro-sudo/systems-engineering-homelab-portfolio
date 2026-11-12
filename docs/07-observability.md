# Case study 07 — Logging, metrics, and observability

## Aim
Create centralized visibility across a mixed Linux/Unix home lab and use monitoring data to investigate operational failures.

## Work documented
The architecture assigns a headless RHEL system to centralized `rsyslog` collection and later describes a monitoring node with Prometheus-compatible scraping, Grafana, and Loki/Promtail components. I also tested `node_exporter` deployment on RHEL hosts and remote access through a Tailscale overlay.

## Troubleshooting recorded in Phase 6
- A downloaded archive turned out to be HTML because a mobile terminal wrapped a long release URL. I verified the source path and corrected the download.
- Podman registry image selection failed; I specified a fully-qualified image reference.
- An Ansible playbook failed because of YAML indentation and missing collection context.
- Remote automation fact gathering stalled during SSH/network resolution problems; I adjusted the lab workflow to isolate the failure.

## What the evidence establishes
The Phase 6 log documents **design, troubleshooting, and a proposed bootstrap playbook**, but its last page contains a **post-blackout verification checklist**, not a complete successful end-to-end monitoring rollout. A later topology report describes an operational monitoring/logging stack; the raw Grafana/Prometheus screenshots and target health checks would strengthen that claim.


[Back to overview](../README.md)
