# ADR-0001 — One composing kernel; the TCB is Authority; Legitimacy is an untrusted veto plugin

> **STATUS 2026-08-10 — one load-bearing claim of this ADR is FALSIFIED.** The
> "an untrusted evaluator can at worst deny (a DoS), never cause an unauthorized
> execution" argument is **withdrawn as a statement about the current code**: three
> runnable exploits (field injection, TOCTOU on the live action, obligation
> authorship) produce unauthorized execution from a malicious evaluator. See
> COMPOSITION.md §11. The *architectural* decision below (one kernel, authority in
> the TCB, plugins outside it, veto-only) is unchanged and still the target — but it
> is now a requirement to be earned, not a property the implementation has.

- **Status:** Accepted (decision axis) · **Target** (cross-repo convergence) · with named **Open Questions** (see below)
- **Living document (v0.1):** the *logical* architecture is mature, but the 3→1
  convergence and obligation composition (COMPOSITION.md §7) are real engineering
  that may surface new constraints. Do **not** treat the architecture as "final"
  until both are done; revise and bump this ADR's version if they do.
- **Date:** 2026-07-06
- **Supersedes framing of:** "AuthGate and FDK are two independent governance engines."
- **Related:** [`../../COMPOSITION.md`](../../COMPOSITION.md)

## Context

Governance is currently realized by **three separate engines**, each of which
independently implements compose + audit + dispatch + executor:

```
decision-os-min   └── full engine (now also has the deny-dominant `evaluators` composer)
authgate-gate     └── full engine (AuthGate + ControlledGate: capability→purpose→runtime + own audit + own executor)
fdk               └── full engine (its own legitimacy decide())
```

This is **duplication of the orchestration role**, not "one engine with evaluators
in separate repos." Two findings drove this ADR:

1. **The invariant.** *You cannot do a bad act even if authorized; you cannot do an
   authorized-good act if you lack authority.* Formally `Allow ⟺ Authority ∧
   Legitimacy`, generalizing to `Execute ⟺ compose(V₁…Vₙ) ∈ PERMITTING` under a
   deny-dominant lattice meet (see COMPOSITION.md).
2. **Evaluators are antitone.** Under deny-dominant `meet`, only the **Authority**
   evaluator's `ALLOW` grants anything and only the kernel mints the one-time token
   (after composition). Every other evaluator is **veto-only**: it can restrict but
   never authorize, and cannot override an authority `DENY`. So a buggy/malicious
   Legitimacy/Safety/Privacy plugin can at worst **deny (DoS)** — never cause an
   unauthorized execution.

## Decision

1. **One logical governance kernel** with a single deny-dominant composer. Not two
   or three engines.
2. **Authority is the only trusted evaluator** — the only `ALLOW`-capable,
   token-minting component — and lives **inside the TCB**: small, stable, formally
   verifiable (Rust-able).
3. **Legitimacy, Safety, Privacy, Cost, … are untrusted, veto-only, fail-closed
   plugins OUTSIDE the TCB**, behind one `Evaluator` interface.
4. **The real boundary is TCB-vs-plugins, not AuthGate-vs-FDK.** FDK/Legitimacy is
   a plugin on the untrusted side, not a co-equal engine.
5. **Invariants** (I1 both-required, I2 mandatory-veto, I3 token-mint-is-terminal,
   I4 fail-closed) are normative and live in COMPOSITION.md §5.
6. **No novelty is claimed** for the composition algebra (deny-overrides / lattice
   meet) or for the verified-core-with-untrusted-plugins architecture (reference
   monitor: Anderson 1972; separation kernel: Rushby 1981; seL4: Klein et al. 2009).

## Current vs Target

| | Current | Target |
|---|---|---|
| Engines | 3 (decision-os-min, authgate-gate, fdk) | 1 host composing kernel |
| Authority | authgate-gate = full engine | authority **evaluator** in the TCB |
| Legitimacy | fdk = full engine | legitimacy **plugin** (untrusted, veto-only) |
| Composer / audit / executor | duplicated in each | once, in the host kernel |
| Conforms to this ADR today | **only** decision-os-min | all |

**Migration is deliberately deferred** (ADR-first). The convergence path: adopt
`decision-os-min` as the host (it already has the composer + one-time token +
hash-chained audit + spent-store), refactor AuthGate's distinctive checks
(capability/purpose/runtime) into an authority evaluator, demote FDK to a
legitimacy plugin, and delete the duplicated orchestration. Not done in this ADR.

### Convergence bricks — progress (updated 2026-08-10)

Rather than migrate in one step, each stacked engine is first shown to be
*redundant* by a test proving the composed form matches it. See COMPOSITION.md §10.

| Brick | Retires | Evidence | Status |
|---|---|---|---|
| #1 legitimacy adapter | the sequential `LegitimacyAuthorityPipeline` stage | `tests/test_evaluators.py` — full truth table, identical verdict/executed/output | done |
| #2 authority adapter | a second *stacked* authority engine | `tests/test_authority_convergence.py` — equivalence, commutativity, capability-non-leak, fail-closed on dialect drift, real `authgate_gate` parity | done |
| #3 AuthGate's distinctive checks as evaluators (capability layer, runtime monitor, notary) | authgate-gate as a full engine | — | not started |
| #4 obligation composition | the blocker for deleting anything | — | design only (see COMPOSITION.md §7) |

Brick #2 produced one result worth promoting out of the test file: stacking two
engines does not merely duplicate code, it **violates the token-mint-is-terminal
invariant by construction** — engine A mints a one-time capability before engine B
can refuse. That makes convergence a correctness argument, not a tidiness one.

**Nothing has been deleted yet**, and no engine has been migrated. Redundancy proven
≠ migration done.

## Consequences

**Positive:** minimal architecture (Occam); TCB minimization; extensible to `n`
evaluators without touching the core; honest positioning (a verified reference
monitor over composed policies, not a novel decision system).

**Negative / risk:** convergence is real work, not a doc change (see Open Q); the
AuthGate verified core must be preserved, not rewritten; obligation composition is
still unsolved (COMPOSITION.md §7).

## Open Questions (NOT decided here)

- **Q1 — In-process vs runtime-isolated plugins.** Keep three axes distinct:
  **logical architecture** (one composing kernel; decided above), **code
  organization** (repos; Q3), and **deployment** (process/enclave topology; this
  Q). They are independent.

  "One engine" is a *logical* claim. The antitone guarantee holds only as strongly
  as the runtime enforces plugin isolation: a memory-safe/sandboxed plugin is safe
  in-process; an adversarial or native-code plugin, or a high-assurance or
  multi-tenant deployment, may justify a **runtime boundary for security**, not
  merely a codebase boundary. If adopted, that boundary is again **TCB-vs-plugins**
  (verified authority core isolated from plugins, verdicts over a channel) — one
  logical engine still.

  > **In-process vs cross-process is a threat-model-conditioned deployment choice,
  > not an architectural split.**

  Deployment guide (conditioned on plugin threat model):

  | Threat model                     | Deployment                                       |
  |----------------------------------|--------------------------------------------------|
  | Trusted, memory-safe evaluators  | Single runtime                                   |
  | Sandboxed evaluators             | Single runtime, or lightweight isolation         |
  | Native / third-party plugins     | Separate process                                 |
  | Multi-tenant environment         | Separate process                                 |
  | Certification / high-assurance   | Separate process / enclave / separation kernel   |

  seL4, MILS, SGX, and CHERI **illustrate why runtime isolation may be justified
  under certain threat models** — they are cited as prior art for the *pattern*,
  **not** a claim that this architecture is equivalent or peer to them.
  **Threat-model-conditioned; left open.**
- **Q2 — Obligation composition.** `LIMIT ∧ CONTAIN` currently collapses (loses the
  redaction). True obligation union / conflict resolution is unsolved.
- **Q3 — Separate FDK repo.** Retaining it is defensible on *lifecycle / ownership /
  licensing-attribution* grounds only — **not** security (it's outside the TCB). If
  those don't apply, merge it.
