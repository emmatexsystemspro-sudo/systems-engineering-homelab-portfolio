# Case study 08 — Engineering incident and diagnostic journal

My lab generated genuine failure conditions that helped me practice a repeatable troubleshooting approach: **capture the error, determine the failing layer, test a hypothesis, correct the smallest responsible configuration, and verify the service end to end.**

| Symptom | Diagnostic finding | Remediation and test |
|---|---|---|
| DNF repo operations returned 404 | An orphaned repository configuration remained on disk under an unexpected filename | Removed the stale repo definition, cleared metadata, and retried package operations |
| TLS/OCSP certificate status appeared expired | Severe system clock drift changed certificate validation behavior | Corrected time, configured Chrony, and verified time synchronization |
| PostgreSQL `chown: Operation not permitted` | Bind-mounted data ownership did not match rootless container user mappings | Reconciled directory ownership, subordinate UID/GID mapping, and SELinux mount context |
| Remote PostgreSQL connection refused | Container was stopped even though host networking was reachable | Checked `podman ps -a`, restarted the container, then retried SQL authentication |
| `systemd` exit `203/EXEC` | Script permission or SELinux executable labeling prevented launch | Corrected permissions or executable context, then restarted and inspected service status |
| Ansible YAML parser failure | A malformed task indentation block broke playbook structure | Corrected YAML structure and reran syntax validation |
| Missing `containers.podman` module | Collection existed in the wrong user's module path | Reconciled collection installation/search path; developed a bootstrap alternative |
| VM transfer throughput collapsed | Insufficient guest memory led to swap pressure and I/O wait | Increased lab VM memory and observed improved transfer behavior |
| PgBouncer login/database routing error | Backend catalog name or pooler configuration mismatched the actual database | Corrected routing and verified the database target |

## How I evaluate success
I separate successful command execution from service health. Better proof combines a running process, the expected listening socket, firewall reachability, successful authentication, and an application-level transaction or query. The underlying PDFs include some tests and some plans; my next step is to publish reproducible, redacted verification artifacts for each significant claim.

[Back to overview](../README.md)
