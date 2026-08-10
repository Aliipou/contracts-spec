# Index

One place to see what every repository in this stack is for, because thirty-odd
repositories without a map is indistinguishable from thirty-odd abandoned
repositories.

Status labels are deliberate and mean what they say:

- **core** — carries real weight; changes here affect everything downstream
- **experimental** — works, unproven in use, interfaces may change
- **reference** — exists to demonstrate an interface, not to be deployed
- **research** — a question being investigated; may end in a negative result

## The layers

```
   normative model        what SHOULD be permitted, and why
        |
   legitimacy             is this action permissible under that model?
        |
   authority              does this actor hold the capability?
        |
   enforcement (PEP)      execute only against a signed, bound authorization
        |
   effect                 the tool, the API, the machine
```

## Core

| Repo | Layer | What it is |
|---|---|---|
| `contracts-spec` | contracts | The shared wire contracts, the composition contract, ADRs, and the executable conformance profile (`conformance/`). Start here. |
| `decision-os-min` | authority + enforcement | The small public reference kernel: single authority, signed decisions bound to action content, one-time capability tokens, hash-chained audit, co-equal veto-only evaluators. |
| `freedom-decision-kernel` | legitimacy | The legitimacy layer and its formal core, including the Authority Principle (`PRINCIPLE.md`) and the ownership discriminant experiment (`experiments/`). |
| `authgate-gate` | authority | Purpose-binding authorization gate for agent tool calls. |
| `freedom-kernel-work` | authority | The verified kernel work (Rust TCB, proof artefacts). |

## Enforcement, runtime, ledgers

| Repo | Status | What it is |
|---|---|---|
| `decision-kernel-core` | core | Kernel of the multi-repo enterprise stack |
| `control-plane` | core | Control plane / PEP orchestration |
| `audit-ledger` | core | Tamper-evident audit storage |
| `decision-runtime` | experimental | Agent runtime platform: sessions, scheduling, supervision |
| `decision-os-integration` | experimental | Composition harness across the stack |
| `boundary-guard` | core | Architecture enforcement: one-way dependency rules across repos |

## Research

| Repo | Status | What it is |
|---|---|---|
| `fdk-research` | research | Advisory intelligence layer |
| `freedom-theory-work` | research | The normative theory itself |
| `freedom-specs-work` | research | Specifications and RFCs derived from it |
| `freedom-policy` | research | Policy seeds; deliberately not ready |
| `crypto-inventory`, `crypto-agility`, `pq-ledger`, `quantum-sandbox` | research | Cryptographic agility and post-quantum questions |

## Plugins and adapters

`plugin-*` are capability plugins (approval, attestation, identity, mcp, ml, policy,
pqcrypto, quantum, tpm-hsm). `adapter-*` are execution adapters (aws, browser,
finance, http, kubernetes, ros2). Both families are **reference or experimental** —
they exist to prove an interface shape. Real SDK calls are honest stubs unless a
repository says otherwise.

## Reading order

1. `contracts-spec/COMPOSITION.md` — how independent evaluators compose, and the
   record of the claims that were falsified getting there
2. `contracts-spec/conformance/PROFILE.md` — the ten requirements, each attributed
   to its prior art
3. `freedom-decision-kernel/PRINCIPLE.md` — the one axiom the stack rests on
4. `decision-os-min/` — the smallest thing that actually runs
