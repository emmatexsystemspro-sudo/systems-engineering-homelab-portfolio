# Phase 15 — Non-destructive failover-policy simulation

**Status:** 11/11 synthetic test cases passed in the November 2026 laboratory session.

## Purpose

Before considering any real automatic promotion, I tested the policy decisions a controller should make when evidence is incomplete or contradictory. The test executable uses **synthetic input variables only** and does not communicate with PostgreSQL, host-management hardware, Windows Hyper-V, or any network endpoint.

## Cases covered

1. Healthy primary → `NO_ACTION`.
2. Unknown primary state → `BLOCK`.
3. No independent failure confirmation → `BLOCK`.
4. Unverified fencing → `BLOCK`.
5. Possible old-primary reboot → `BLOCK`.
6. Missing witness/quorum → `BLOCK`.
7. Missing exclusive coordination lock → `BLOCK`.
8. Standby unreachable → `BLOCK`.
9. Standby not confirmed in recovery → `BLOCK`.
10. Unacceptable WAL freshness/RPO → `BLOCK`.
11. All **synthetic** safety gates satisfied → `REVIEW_ONLY`, **not** a promotion authorization.

## Reproduce safely

Requires Python 3 with no third-party packages:

```bash
python3 -m py_compile examples/failover_policy_simulator.py
python3 -B examples/failover_policy_simulator.py
```

Expected final output:

```text
RESULT: 11/11 simulated scenarios passed
```

## Meaning and limits

The simulator tests deterministic branching under predefined inputs. It **does not** verify that the inputs reflect real host state; does not implement an external witness, lease, DCS, or fencing agent; and cannot guarantee single-writer safety. The deliberately conservative `REVIEW_ONLY` outcome helps prevent accidental interpretation of this code as a production failover tool.

Source: [failover_policy_simulator.py](../examples/failover_policy_simulator.py).

[Back to portfolio](../README.md)
