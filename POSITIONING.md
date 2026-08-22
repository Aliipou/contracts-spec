# Ecosystem Positioning — Canonical Claims

**Repository:** `contracts-spec` (version-controlled source of record)  
**Decision date:** 2026-08-22 (revised: system-level moral order framing)  
**Status:** Locked until evidence changes (new conformance results, provenance
milestones, or external review). When sub-project READMEs, papers, or pitches
conflict with this file on *identity or claims*, **this file wins**.

**Purpose:** Stabilize what the ecosystem claims — and what it deliberately does
not claim — after kill-tests, falsification runs, and architectural review.
The goal is not a grander pitch. It is a **harder-to-refute** one.

**Audit trail:** [`CLAIM_AUDIT.md`](CLAIM_AUDIT.md) · **Repo map:** [`ECOSYSTEM_MAP.md`](ECOSYSTEM_MAP.md)

---

## What the whole system is

**One sentence:**

> The ecosystem engineers a **moral order for machine agency** — an external,
> explicit, enforceable structure within which intelligence may propose but cannot,
> by being capable or clever, become the source of permission to act.

**The defining sentence (outreach):**

> **Morality is not inside the model. The model exists inside the moral order.**

This is **not** “we discovered correct morality.” It **is**:

> We instantiate a **specific** moral order from frozen axioms, convert it into
> machine-enforceable constraints, and prevent intelligence or capability from
> bypassing that order.

---

## Four orders — not one blur

Most stacks collapse these. This ecosystem separates them:

```text
Morality  ≠  Authority  ≠  Capability  ≠  Execution
```

| Order | Question | Primary component |
|---|---|---|
| **Moral order** | Under foundational axioms, what is impermissible, permissible, or unresolved? | FDK (+ frozen A1–A7) |
| **Authority order** | Who may grant, delegate, or exercise permission to act? | AuthGate / decision-os-min |
| **Capability** | What can the agent technically do? | Agent / runtime (untrusted) |
| **Execution** | What actually happens in the world? | PEP, adapters, IO |

Policy engines answer rules. Authorization systems answer “do you have permission?”
This ecosystem additionally answers:

> **Can the agent do this *even if it could* — and may it do this *even if authorized*?**

Capability answers the first operationally; the moral order answers the first
normatively; authority answers the second; enforcement makes all three binding.

---

## System pipeline (ordering matters)

```text
Intelligence / Agent
        │
        │ proposes, reasons, plans (untrusted)
        ▼
┌─────────────────────────────────────────┐
│     ENGINEERED MORAL ORDER (system)     │
│                                         │
│  Moral constraints    ← FDK (A1–A7)     │
│  Authority constraints ← AuthGate       │
│  Legitimate path      ← Decision Kernel │
│  Accountability       ← Audit           │
└─────────────────────────────────────────┘
        │
        ▼
    Enforcement → Execution
```

**Four-line mantra:**

> **Intelligence proposes.**
> **The moral order constrains.**
> **Authority authorizes.**
> **The system enforces.**

**Ordering invariant** (matches `decision-os-min/paradigm.py` — legitimacy ⊥ authority):

1. **Moral / legitimacy gate first** — “should this happen at all?” (FDK, plugins)
2. **Authority gate second** — “does this actor hold the capability?” (AuthGate)
3. A legitimacy DENY **cannot** be overridden by authority
4. Constraint inputs are **veto-only** — they never grant authority (`compose ⊑ a`)

At runtime, authority grants and moral ceilings compose by lattice meet; both must
pass before execution.

---

## Canonical thesis

1. **Intelligence does not create authority.**
2. **Capability does not establish permissibility or legitimacy.**
3. **Execution requires verifiable authority inside an enforced moral order.**
4. **Morality is engineered as external constraint — not trained as inner virtue.**

Sub-claims (Track B):

> FDK instantiates the **moral** slice of that order from frozen axioms over
> accepted inputs — it does not discover moral truth.

Sub-claims (Track A):

> AuthGate instantiates the **authority** slice — preventing intelligence,
> information, or computation from becoming authority merely by being capable.

---

## What makes this an “order” — not policies with philosophy words

A collection of policies is ad hoc. An **order** requires global properties:

| Property | Meaning | Status |
|---|---|---|
| **Global invariants** | Same rules at every gate; no local exceptions smuggled in | AE-1…AE-10, No Amplification |
| **Non-bypassable enforcement** | No path from proposal to IO without mediation | PEP, INV-1…6, mandatory tokens |
| **Explicit chain** | axiom → constraint → authority → execution traceable | **PARTIAL** — provenance gap |
| **Veto-only moral layer** | Moral constraints narrow; never grant | FDK + evaluator algebra |
| **Single authority root** | One signer for executable verdicts | Decision Kernel |
| **Frozen moral constitution** | A1–A7 immutable in FDK v1 | `FREEZE.md`, primitive freeze CI |
| **External moral source** | Order’s legitimacy not proven inside kernel | Explicit non-claim |
| **Accountability** | Audit records what was decided and why | Partial — M1 artifact shipped |

If any of these fail in deployment, call it what it is: **policies**, not an order.
Do not use “engineered moral order” in outreach until the chain is auditable end-to-end.

---

## Two tracks — one ecosystem, two claims

Do not merge Track A and Track B in one elevator pitch. They are **layers of one
order**, not one product claim.

### Track B — FDK (moral order layer)

**Question:** Under frozen foundational axioms, what is impermissible, permissible,
or unresolved — given **accepted inputs**?

**One sentence:**

> FDK is a formally constrained **moral order for machine action**: frozen axioms
> (A1–A7) determine the boundaries within which an agent's capabilities and
> delegated authority may be exercised — not a universal engine for discovering
> moral truth.

**Canonical sub-documents:** `freedom-decision-kernel` → `spec/AXIOM_REGISTRY.md`,
`spec/FREEZE.md`, `spec/INFERENCE_RULES.md`.

---

### Track A — AuthGate / decision-os-min (authority order layer)

**Question:** What may create, expand, delegate, or enforce authority?

**One sentence:**

> AuthGate is the **authority architecture** that prevents capability or
> intelligence from bypassing the moral order — or from becoming authority merely
> by being capable of acting.

**Canonical sub-documents:** [`conformance/CLAIM.md`](conformance/CLAIM.md),
`decision-os-min` → `docs/AUTHORITY_MODEL.md`, `authgate-kernel` → `WHY_NOT_OPA.md`.

---

## Constitutional source — external to the kernel

**Canonical statement:**

> The constitutional source is external to the kernel. The kernel enforces the
> constitution; it does not establish its legitimacy.

---

## Truth levels — conditional moral order

**Honest claim:**

> The order guarantees moral-constitutional behavior **conditional on accepted
> inputs** — not that inputs match world truth.

Do not say “we formalized morality.” Say:

> **We formalized enforceable moral constraint conditional on declared inputs.**

---

## Provenance roadmap

| **M0** | Schema + epistemic disclaimer | **DONE** |
| **M1** | Axiom + rule trace (`evaluate_legitimacy`) | **DONE** |
| **M2** | Accepted-input references | **DONE** |
| **M3** | `action_ref` binding | **DONE** |
| **M4** | Structural conformance (`verdict_artifact_profile`) | **DONE** |
| **M5** | Authority linkage (signed decision ref) | not started |
| **M6** | Attestation `provenance_ref` | not started |
| **M7** | Full provenance CI | not started |

---

## Forbidden outreach

- “We discovered correct morality”
- FDK as universal ethics engine
- AuthGate as “Theory of Freedom executable” (main hook)
- “Engineered moral order” without provenance chain
- Hiding conditional-on-inputs caveat

---

## Document map

| Topic | Location |
|---|---|
| **This file** | `contracts-spec/POSITIONING.md` |
| **Claim audit** | [`CLAIM_AUDIT.md`](CLAIM_AUDIT.md) |
| **Repo roles** | [`ECOSYSTEM_MAP.md`](ECOSYSTEM_MAP.md) |
| AE-1…AE-10 | [`conformance/CLAIM.md`](conformance/CLAIM.md) |
| **Roadmap** | [`ROADMAP.md`](ROADMAP.md) |
| FDK rules | `freedom-decision-kernel/spec/INFERENCE_RULES.md` |

Sub-project docs defer here for **ecosystem-level** identity and claims.

---

## Revisit triggers

- Provenance-complete verdict artifacts ship (**M7**)
- End-to-end axiom → constraint → authority → execution audit demonstrated
- Authenticated rule-adoption authority model specified

Until then: **stabilize claims, do not enlarge them.**
