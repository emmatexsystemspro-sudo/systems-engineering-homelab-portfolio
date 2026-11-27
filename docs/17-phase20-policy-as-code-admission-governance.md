# Phase 20 — K3s Policy-as-Code & Admission Governance (Kyverno CEL)

## Objective
Enforce automated Kubernetes admission governance and shift-left manifest validation across the `lab-apps` namespace using **Kyverno v1.20.0** (`policies.kyverno.io/v1` `ValidatingPolicy` with Common Expression Language), ensuring resource hygiene, pod security boundaries, immutable image tagging, and ownership/data-classification metadata compliance.

## Architecture & Resource Sizing
- **Control Plane (`sys2-controller`, 1.7 GiB RAM):** Hosts the K3s API server and declarative `HelmChart` manifest (`/var/lib/rancher/k3s/server/manifests/kyverno.yaml`).
- **Worker Node (`sys3-databasehost`, 7.5 GiB RAM):** Hosts all four single-replica Kyverno controllers (`admissionController`, `backgroundController`, `cleanupController`, `reportsController`) pinned via `nodeSelector: kubernetes.io/hostname: sys3-databasehost` with bounded container memory limits (`128Mi`–`256Mi`).
- **Policy Engine (`policies.kyverno.io/v1` `ValidatingPolicy`):** Uses native Kubernetes CEL expressions (`validationActions: [Deny]`) scoped via `namespaceSelector` to `kubernetes.io/metadata.name: lab-apps`.

## Declarative Policy Controls (`policy-as-code/validating-policies.yaml`)

| Policy Name | Category | Enforcement Rule (CEL) |
| :--- | :--- | :--- |
| `require-resource-limits` | Resource Governance | Requires explicit `resources.limits.cpu` and `resources.limits.memory` on every container. |
| `disallow-privileged-containers` | Pod Security | Blocks `securityContext.privileged: true` across all containers. |
| `disallow-latest-tag` | Supply Chain Governance | Requires an explicit image tag (`:`) and prohibits `:latest`. |
| `require-governance-labels` | Compliance & Metadata | Enforces non-empty `owner` and `data-classification` labels on workload pods. |

## Verification Proof

### 1. Live API Admission Denial (Negative Test)
Deploying an unlabelled, privileged `nginx:latest` pod without resource limits (`kubectl run rogue-pod -n lab-apps --image=nginx:latest --privileged=true`) was rejected immediately by the `vpol.validate.kyverno.svc-fail` admission webhook with all four governance violation messages before any container could schedule.

### 2. Compliant Workload Rollout (Positive Test)
`ai-mcp-governance/k8s-manifest.yaml` was updated with `owner: platform-security` and `data-classification: internal-telemetry` labels, and `deployment/governed-pg-mcp` rolled out cleanly (`1/1 Running`, `0` restarts) in `lab-apps`.

### 3. Shift-Left CI Gate (`.github/workflows/policy-as-code-ci.yml`)
GitHub Actions runs `kyverno apply policy-as-code/validating-policies.yaml` on pull requests and pushes modifying `policy-as-code/**` or `ai-mcp-governance/k8s-manifest.yaml`, asserting both positive compliance for `governed-pg-mcp` and deterministic rejection of non-compliant pod fixtures prior to cluster deployment.
