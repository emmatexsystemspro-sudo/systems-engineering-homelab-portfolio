# Case study 02 — Ansible automation, time synchronization, and security

## Problem
Manual host configuration made it difficult to maintain consistent packages, time sources, service permissions, and firewall rules across RHEL and macOS nodes.

## Implementation
I created Ansible inventory groups and playbooks for RHEL packages, PostgreSQL container deployment, Chrony configuration, TCP proxy services, and system firewall posture. I practiced moving from imperative shell commands to declarative tasks using Ansible modules and handlers. On the macOS node, I used OS-specific time configuration rather than attempting Linux package operations.

## Diagnostic example: certificate failures caused by time drift
A DNF transaction failed with an expired OCSP-response error. I investigated system time and package manager state, corrected severe clock drift, repaired the package metadata/DB state in the isolated lab, and used Chrony to maintain sync. The Linux/macOS automation run reported successful results across four targets. An earlier container deployment play recap recorded `unreachable=0` and `failed=0`.

## Security design considerations
- Used a dedicated automation identity rather than routinely executing the entire workflow as root.
- Practiced SSH key-based management and controlled privilege escalation.
- Managed SELinux policy instead of disabling it to make services start.
- Configured `firewalld` for service-specific restrictions and experimented with a default-drop posture.
- Used Tailscale for remote lab access rather than opening administration ports directly to the public Internet.

**Important qualification:** Some source playbooks include permissive trusted-subnet rules, passwordless sudo, and broad SELinux boolean changes. Those require further threat-model review before reuse. The sample in [`ansible/playbooks/chrony_client.yml`](../ansible/playbooks/chrony_client.yml) is a sanitized teaching example, not a verified drop-in reproduction of the complete lab.

## What I learned
A task returning success does not guarantee the service is healthy. Configuration management needs follow-up checks: active daemon state, socket availability, authentication, and application-level behavior.

[Back to overview](../README.md)
