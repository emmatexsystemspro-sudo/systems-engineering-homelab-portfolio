# Case study 01 — Hybrid multi-node architecture

## Engineering question
How can a mixed hardware inventory be organized into a maintainable systems engineering lab with separated functions and meaningful failure domains?

## Design and evolution
I assigned logical responsibilities to a RHEL automation controller, a Hyper-V Linux compute guest, a bare-metal PostgreSQL service host, a centralized logging node, and a macOS Unix storage node. Later phases added a separate database-standby VM and dedicated observability components. My control workflows used SSH, Ansible, and a Tailscale overlay for lab access.

The original setup includes physical and virtual nodes rather than a homogeneous single-machine virtual cluster. That choice let me practice network bridging, cross-platform command differences, storage mounts, and failure isolation. I also tested cloned VM identity resets and network-interface configuration when provisioning the standby node.

## Decisions and trade-offs
- **Role separation:** The control plane automates workloads but does not replace service-specific verification.
- **Physical versus virtual fault domains:** Moving a standby VM to another physical host improves isolation relative to a same-host standby, but shared power, switching, storage, and controller dependencies may remain.
- **Mutable lab inventory:** Different reports contain different IP assignments and role labels, so I have withheld definitive IP-based public topology until reconciling the live inventory.
- **Different operating systems:** Linux automation modules do not always map cleanly to older macOS, so separate platform-specific tasks or native remote commands were needed.

## What I validated or documented
Documented Ansible-managed Linux nodes, Hyper-V network bridging and guest configuration, rootless PostgreSQL on bare metal, remote PostgreSQL connectivity, Unix/NFS storage configuration, and a separate standby environment for replication.


[Back to overview](../README.md)

## Final Phase 15 role assignment

In the closing November 2026 test, the writable PostgreSQL primary was hosted in a Linux Hyper-V VM while the standby was running on a physically separate HP EliteBook with RHEL installed directly on the hardware. Earlier role allocations in the project were historical lab states. See [Phase 15 validation](13-phase15-replication-monitoring.md).
