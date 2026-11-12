# Case study 03 — LVM, XFS, and disaster recovery experiments

## Problem
The database host needed persistent storage that could be managed independently of container lifecycle, with enough flexibility for rebuilds and recovery experiments.

## Implementation
I partitioned disk space and created a Logical Volume Manager (LVM) volume group, mounted an XFS logical volume through `/etc/fstab`, and tested safe mount verification. The lab evolved from a larger test volume to a smaller planned footprint, leaving capacity unallocated for later use.

I also ran local snapshot/rollback experiments. They exposed three operational pitfalls:

1. A snapshot taken **after corruption** preserves the corrupted state; rollback cannot recover an earlier healthy version that was never captured.
2. Manually freezing filesystem I/O while LVM is performing snapshot operations can cause device-mapper contention in the tested workflow.
3. Active processes holding mounted filesystems open can delay merges and unmounts, so service sequencing matters.

## Engineering outcome
I gained a working view of block devices, logical volumes, filesystem mount persistence, copy-on-write snapshots, and why snapshots are not a substitute for tested off-host backups. These were **lab recovery simulations**, not a proven end-to-end business continuity process.


[Back to overview](../README.md)
