# Case study 04 — PostgreSQL 15 on rootless Podman

## Problem
A persistent PostgreSQL container failed to initialize on RHEL because its data directory could not be accessed by the user inside the container namespace.

## Investigation
I inspected container lifecycle state, mounted storage ownership, rootless user namespace mappings, and SELinux labels. The database image used a dedicated internal PostgreSQL user, while the host-mounted directory had a different ownership context. The failure surfaced as `chown: Operation not permitted` and related file errors.

## Remediation
I corrected host-directory ownership, used Podman's `unshare` mapping tools for the container's expected user, and used the private SELinux bind-mount labeling option (`:Z`) where appropriate. The deployed PostgreSQL engine persisted data under a host storage mount rather than only inside the container writable layer.

I then validated that the database process was running and authenticated to it from a separate controller node over a custom lab TCP port. An Ansible deployment report recorded a successful run with no unreachable or failed targets.

## Lessons
- Persistent application data needs deliberate filesystem ownership, SELinux contexts, and container user mapping.
- An open network path does not prove a database service is running; inspect container state and try authenticated SQL.
- Container isolation reduces attack surface but is not an absolute security boundary.
- A nondefault port can reduce accidental collisions; it is **not an authentication or confidentiality control**.


[Back to overview](../README.md)
