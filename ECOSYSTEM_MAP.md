# Ecosystem Map

**Canonical positioning:** [`POSITIONING.md`](POSITIONING.md)

Multi-repo workspace. Each row is an independent git repository unless noted.

---

## Specification & governance (source of record)

| Repository | Role |
|---|---|
| **`contracts-spec`** | Schemas, conformance (AE-1…AE-10), **canonical POSITIONING / CLAIM_AUDIT**, VerdictArtifact M0 |
| `decision-kernel-core` | Sole emitter of signed `decision` contract |
| `audit-ledger` | Tamper-evident audit chain |

---

## Authority order (Track A)

| Repository | Role |
|---|---|
| `decision-os-min` | Reference PEP + Decision Kernel (minimal) |
| `authgate-kernel` (`freedom-kernel-work`) | AuthGate Rust TCB, integrations |
| `authgate-gate` | Gate / executor components |
| `decision-os-integration` | Cross-repo composition harness |
| `plugin-*` | Veto-only advisors (ML, policy, identity, …) |
| `adapter-*` | Execution adapters (HTTP, K8s, ROS2, …) |

---

## Moral order (Track B)

| Repository | Role |
|---|---|
| `freedom-decision-kernel` | FDK kernel — frozen A1–A7, M1 VerdictArtifact |
| `freedom-theory-work` | Optional academic lineage (not product claim) |
| `fdk-research` | Research layer (compass, federation — outside TCB) |

---

## Experimental / not product claims

| Repository | Role |
|---|---|
| `decision-runtime` | Path B agent runtime — explicitly *not* “Decision OS” yet |
| `boundary-guard` | Architecture coupling discipline |
| `crypto-inventory`, `pq-ledger` | Crypto posture tooling |

---

## Dependency direction

```text
contracts-spec  ←  all implementation repos depend on schemas
       ↑
POSITIONING.md wins on ecosystem identity / claims conflicts
```

Local workspace root (`D:\جافکری\`) is a **checkout aggregate** — not a git repo.
Do not treat root-level stubs as canonical; use **`contracts-spec/POSITIONING.md`**.
