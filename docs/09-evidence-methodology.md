# Evidence and validation methodology

The public portfolio summarizes documented lab work and provides instructional source examples. Raw PDFs, original environment logs, screenshots, and source-to-claim ledgers remain private because they may contain credentials, host addresses, and identifiers.

**Evidence classes used in this repository:**

- **Observed:** specific commands or outputs captured in lab reports or reviewed terminal screenshots.
- **Simulated:** test data or predefined conditions, not production traffic or physical failure injection.
- **Historical:** a test performed in an earlier phase with a different database-role assignment.
- **Unverified:** an architectural goal without a corresponding successful acceptance test.

Measured results are tied to their individual lab sessions; they are not production SLOs or guarantees. This distinction especially applies to PostgreSQL asynchronous replication and high-availability failover.

The original sources are retained outside the public repository for later private verification.
