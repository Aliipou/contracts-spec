# VerdictArtifact — specification (not implementation claim)

**Status:** Specification only (2026-08-22). Schema:
`decision_os_contracts/schemas/verdict_artifact.schema.json`.

Shipping this document **does not** mean provenance is solved. It defines what a
complete audit trail **must** contain when implemented — and what it **must not**
claim.

---

## Purpose

Turn verdicts from opaque strings (`DENY`) into **auditable constitutional
reactions**:

> Under this frozen constitution, this kernel version, and these **accepted**
> facts, DENY follows for these reasons.

---

## Epistemic levels (mandatory distinction)

```text
WORLD FACT          ← outside kernel; may never enter TCB
    ↓
ASSERTED FACT       ← caller/plugin supplied; untrusted
    ↓
ACCEPTED INPUT      ← what kernel assumed for this verdict
    ↓
CONSTITUTIONAL INFERENCE
    ↓
VERDICT
```

**Type-level rules (must not be collapsed in schema or code):**

| Expression | Means | Does NOT mean |
|---|---|---|
| `asserted_by` | Who supplied the fact | That they spoke truth |
| `provenance_ref` | Pointer to attestation / log | Verified world fact |
| `accepted_input` | Assumption for this verdict | Moral or empirical truth |
| `axiom_ids[]` | Which frozen axioms fired | That axioms are morally correct |
| `signature` | Integrity of artifact | Correctness of inputs |

The schema requires `epistemic_disclaimer` with fixed text so parsers cannot
strip the caveat silently.

---

## Field guide

```text
VerdictArtifact
├── artifact_version
├── decision_id
├── verdict
├── kernel_version
├── constitution_version      ← e.g. fdk-v1.0-a1-a7
├── accepted_inputs[]
│   ├── fact_key / fact_value
│   ├── asserted_by           ← WHO (not truth)
│   ├── input_class           ← CALLER_FLAG | TYPED_FACT | ATTESTED | ...
│   └── provenance_ref?       ← optional pointer (not truth)
├── constitutional_basis
│   └── axiom_ids[]           ← A1–A7, C*, R0
├── inference_trace
│   └── rule_ids[]            ← stable registry IDs
├── authority_context_ref?    ← Track A (AuthGate)
├── action_ref?
├── input_hash?
├── signature?
└── epistemic_disclaimer      ← required constant
```

---

## Implementation roadmap (honest)

| Milestone | Delivers |
|---|---|
| **M0 (this doc + schema)** | Shared vocabulary; no runtime change |
| **M1** | FDK emits partial artifact via `evaluate_legitimacy()` — `freedom-decision-kernel/tests/test_verdict_artifact_m1.py` |
| **M2** | decision-os-min attaches authority_context_ref + signature |
| **M3** | provenance_ref populated from attestation plugins |
| **M4** | Provenance completeness tests (conformance extension) |

Do not mark M4 complete until fact provenance is wired — not caller flags alone.

---

## Relationship to `decision.schema.json`

- `decision.schema.json` — **executable** kernel output (PEP consumes this today).
- `verdict_artifact.schema.json` — **audit / accountability** envelope (optional
  extension; may embed or reference `decision_id`).

Future: PEP verifies decision; auditors consume VerdictArtifact.

---

## Canonical wording (outreach)

**Say:**

> Conditional constitutional verdict with structured provenance of accepted inputs.

**Do not say:**

> We formalized morality or verified that the action was coercive.

See root `POSITIONING.md`.
