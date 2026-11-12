# Case study 06 — TCP ingress and failover automation prototype

## Layer 4 ingress experiments
I tested PostgreSQL forwarding through **HAProxy** and **NGINX stream** configurations on an RHEL compute guest. SELinux policy blocked the initial proxy bindings; I investigated denied connections and port labeling rather than disabling SELinux. I then described the proxy settings in an Ansible deployment playbook with a selectable proxy engine.

A later infrastructure blueprint discusses active/passive ingress and Keepalived virtual-IP routing. That diagram is **design documentation**, and I do not claim a fully validated redundant ingress service without a corresponding test log.

## Phase 10–11 orchestration
I built and debugged a Bash/systemd health-check script that probes the PostgreSQL primary and changes PgBouncer routing when the primary is considered unavailable. The source ledger reports resolution of a `203/EXEC` service failure, incorrect binary paths, text-replacement errors, and database-routing mismatches. I also wrote an Ansible task to stop the old primary's Podman container as a fencing exercise.

## Engineering review: why this remains a prototype
The phase 10–11 report calls the lab complete, but its embedded script needs additional review before public reuse:
- Different sections point at **different standby IP addresses**, including one address also used by the controller in earlier reports.
- One promotion example mixes an interactive container flag with remote noninteractive invocation, which may fail.
- A health-check failure does not establish that the primary is safely fenced; network partition can cause **split-brain**.
- The script does not demonstrate full, race-safe promotion, rejoin, rollback, quorum, and fencing behavior.
- The container-stop playbook is not a complete STONITH guarantee if the controller cannot reach the old primary.

**Portfolio claim:** I designed and troubleshot a **custom PostgreSQL failover and fencing lab prototype**. I do not yet claim production-grade automatic failover or guaranteed high availability.

## Future validation
- [ ] Reconcile actual standby address, management route, and current node inventory.
- [ ] Rehearse controlled primary outage and verify only one writable leader.
- [ ] Measure time to recover, transaction interruption, and expected data-loss window.
- [ ] Test network partitions, restart/rejoin behavior, and fencing failure.
- [ ] Replace plain-text credentials and root SSH with safer operational patterns.

[Back to overview](../README.md)

## Final Phase 15 decision

After investigating misrouting and destructive fencing loops, the project ended with the third systemd service running in **monitoring-only mode**. Unattended promotion was not enabled. See [Phase 15 closeout](13-phase15-replication-monitoring.md).
