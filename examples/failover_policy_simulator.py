#!/usr/bin/env python3
"""Non-destructive Phase 15 HA decision simulator.

Synthetic inputs only. No SSH, database, network, fencing, promotion,
service restarts, or configuration changes.
"""
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Evidence:
    primary_health: str = "DOWN"
    independent_failure_confirmed: bool = True
    fencing_verified: bool = True
    fencing_persistent: bool = True
    witness_agrees: bool = True
    exclusive_lock_held: bool = True
    standby_accessible: bool = True
    standby_in_recovery: bool = True
    wal_rpo_acceptable: bool = True


def assess(e: Evidence):
    if e.primary_health == "UP":
        return "NO_ACTION", "Original primary is responding"
    if e.primary_health != "DOWN":
        return "BLOCK", "Primary state unknown"
    checks = (
        (e.independent_failure_confirmed, "No independent failure confirmation"),
        (e.fencing_verified, "No independently verified fencing"),
        (e.fencing_persistent, "Old primary could restart as writable"),
        (e.witness_agrees, "Witness/quorum evidence missing"),
        (e.exclusive_lock_held, "No exclusive coordination lock"),
        (e.standby_accessible, "Standby unavailable"),
        (e.standby_in_recovery, "Candidate is not confirmed standby"),
        (e.wal_rpo_acceptable, "WAL freshness/RPO not acceptable"),
    )
    for ok, reason in checks:
        if not ok:
            return "BLOCK", reason
    return "REVIEW_ONLY", "Synthetic checks passed; no promotion authorized"


def main():
    base = Evidence()
    cases = (
        ("Healthy primary", replace(base, primary_health="UP"), "NO_ACTION"),
        ("Unknown primary state", replace(base, primary_health="UNKNOWN"), "BLOCK"),
        ("Only one failure signal",
         replace(base, independent_failure_confirmed=False), "BLOCK"),
        ("Fencing unverified", replace(base, fencing_verified=False), "BLOCK"),
        ("Reboot protection absent", replace(base, fencing_persistent=False), "BLOCK"),
        ("Witness missing", replace(base, witness_agrees=False), "BLOCK"),
        ("Lock unavailable", replace(base, exclusive_lock_held=False), "BLOCK"),
        ("Standby unreachable", replace(base, standby_accessible=False), "BLOCK"),
        ("Standby role unexpected", replace(base, standby_in_recovery=False), "BLOCK"),
        ("WAL uncertainty", replace(base, wal_rpo_acceptable=False), "BLOCK"),
        ("All synthetic gates met", base, "REVIEW_ONLY"),
    )
    print("[SAFETY] SIMULATION ONLY")
    print("No network, database, service or fencing operations")
    for name, case, expected in cases:
        result, reason = assess(case)
        assert result == expected, f"{name}: expected {expected}, got {result}"
        print(f"PASS  {name}: {result} - {reason}")
    print(f"RESULT: {len(cases)}/{len(cases)} simulated scenarios passed")


if __name__ == "__main__":
    main()
