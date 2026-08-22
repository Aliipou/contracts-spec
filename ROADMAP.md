# Provenance & Governance Roadmap

**Repository:** `contracts-spec` (version-controlled source of record)

| Milestone | Scope | Status | Evidence |
|---|---|---|---|
| **M0** | Schema + epistemic disclaimer | **DONE** | `decision_os_contracts/schemas/verdict_artifact.schema.json`, `docs/VERDICT_ARTIFACT.md` |
| **M1** | Axiom + rule trace | **DONE** | `freedom-decision-kernel` → `evaluate_legitimacy()`, `spec/INFERENCE_RULES.md`, `tests/test_verdict_artifact_m1.py` |
| **M2** | Accepted-input references | **DONE** | `fdk_kernel/accepted_inputs.py`, `tests/test_verdict_artifact_m2.py` |
| **M3** | `action_ref` binding | **DONE** | `VerdictArtifact.action_ref` = candidate action id |
| **M4** | Structural conformance | **DONE** | `conformance/verdict_artifact_profile.py`, `tests/test_verdict_artifact_m4.py` |
| **M5** | Authority linkage (AuthGate decision signature) | **NOT STARTED** | decision-os-min integration |
| **M6** | `provenance_ref` from attestation plugins | **NOT STARTED** | plugin-attestation |
| **M7** | Full provenance conformance in CI | **NOT STARTED** | extend AE profile or VA-* suite |

## Governance

| Item | Status |
|---|---|
| Canonical `POSITIONING.md` in this repo | **DONE** |
| `CLAIM_AUDIT.md` | **DONE** |
| `ECOSYSTEM_MAP.md` | **DONE** |
| `conformance/probes.py` committed | **DONE** |
| Workspace root pointer-only README | **DONE** (local aggregate, not a git repo) |

## Claim discipline rule

Each milestone claims **only** what its artifact can show. Do not say "provenance solved"
until M7 passes with fact attestation — not caller flags alone.

See [`POSITIONING.md`](POSITIONING.md) for ecosystem claims.
