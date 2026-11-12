# Selected screenshot evidence — multi-node systems engineering lab

These are **cropped excerpts** of screenshots recorded during October 2026 laboratory work. The source files remain private. Browser addresses, device chrome, terminal prompts, or internal host labels have been excluded or masked where necessary. Image content has **not been recreated**, and visible results have not been changed. All evidence refers to **self-directed laboratory tasks**, not production infrastructure or customer workloads.

## Six-node Ansible telemetry deployment

![Ansible play recap for six Linux nodes](../screenshots/ansible-telemetry-recap-redacted.png)

The screenshot shows six completed host rows in an Ansible `PLAY RECAP`, with `unreachable=0` and `failed=0`. Original inventory labels were masked. This supports successful execution of the recorded tasks, not independent proof that every metric endpoint was continuously healthy.

## Firewall configuration playbook

![Ansible firewall play recap for six Linux nodes](../screenshots/ansible-firewall-recap-redacted.png)

Six host rows completed the reported firewall-configuration run with zero task failures. Original inventory labels were masked. A play recap does not independently prove every runtime firewall rule or all network isolation requirements.

## Grafana CPU and memory metrics

![Grafana CPU and memory time series](../screenshots/grafana-cpu-memory-cropped.png)

Two Grafana panels display non-empty CPU and memory time series across the captured observation window. The screenshot supports successful collection and visualization for the selected dashboard target; it does not establish full-fleet health or continuous monitoring availability.

## Grafana filesystem and storage visibility

![Grafana filesystem available-space graph](../screenshots/grafana-filesystem-cropped.png)

The filesystem panel displays available-space measurements for several paths, including a lab storage mount labeled `/mnt/mac_vault` with approximately 314 GiB available in the displayed summary. The chart alone does not prove a successful backup, recovery, NFS transport, or data-integrity test.

## Evidence limitations

- These are **selected October 2026 screenshots**, not a complete Phase 15 evidence collection.
- The November 2026 PostgreSQL replication, PgBouncer routing, systemd monitoring, and 11/11 simulated failover checks are documented separately in [Phase 15 validation](13-phase15-replication-monitoring.md) and [simulation methodology](14-phase15-failover-simulation.md), but **are not depicted** in these four captures.
- Cropping and redaction intentionally remove identifying context without manufacturing output or implying missing tests were performed.
- Review each cropped image personally before setting repository visibility to Public; review earlier Git history separately for exposed secrets or unredacted captures.

[Back to case studies](01-architecture.md)
