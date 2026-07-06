# Decision Composition

> Status: **normative contract, deliberately un-ambitious.** This document fixes
> how multiple independent governance evaluators (Authority, Legitimacy, and — in
> future — Safety/Privacy/Cost/…) combine into ONE verdict, and the invariants
> that composition must preserve. Reference implementation:
> [`decision-os-min/decision_os_min/compose.py`](../decision-os-min/decision_os_min/compose.py)
> and its use in `kernel.decide(..., evaluators=[...])`.
>
> Architecture decision & current-vs-target state:
> [`docs/adr/0001-one-engine-authority-tcb.md`](docs/adr/0001-one-engine-authority-tcb.md).
> Whether plugins share the kernel's runtime or sit behind a runtime isolation
> boundary (process/enclave/separation-kernel) is **open** and threat-model-
> conditioned — see ADR-0001 Q1; §9 here describes the *logical* architecture only.

## 0. Non-claims (read first)

The repository **intentionally does not claim novelty for policy composition or
lattice theory.** The repository's contribution, if any, lies in the overall
governance architecture and its concrete enforcement model.

Composing independent policy verdicts by deny-overrides / lattice meet is a mature,
well-studied area. This document *reuses* it and cites it; it does not reinvent it.
See §6 (Prior art) before writing any paper or README that uses the word "novel."

## 1. The invariant this exists to serve

> You cannot do a bad act even if you are authorized; you cannot do an
> authorized-good act if you lack authority.

Formally, for the two current evaluators:

```
Allow  ⟺  Authority = ALLOW  ∧  Legitimacy = ALLOW
```

Neither is sufficient alone; each holds a **veto**; neither may override the
other's DENY. Generalized to `n` mandatory evaluators `V₁ … Vₙ`:

```
Execute  ⟺  compose(V₁, …, Vₙ) ∈ PERMITTING
```

## 2. Verdict types

Five verdicts (a bounded lattice, not a boolean):

| Verdict   | Meaning                                  | Permitting? |
|-----------|------------------------------------------|-------------|
| `ALLOW`   | run as-is                                | yes         |
| `LIMIT`   | run against a minimized/redacted payload | yes         |
| `CONTAIN` | run sandboxed (restricted tools/net/TTL) | yes         |
| `DEFER`   | escalate to a human; do not run now      | no          |
| `DENY`    | refuse                                   | no          |

`PERMITTING = {ALLOW, LIMIT, CONTAIN}`. Only a permitting **composed** verdict
mints a capability token.

## 3. The meet operator (composition)

Order verdicts by restrictiveness, least → most:

```
ALLOW  ≺  LIMIT  ≺  CONTAIN  ≺  DEFER  ≺  DENY
```

`meet(a, b)` = the more restrictive of the two. Then:

- **`DENY` is the absorbing bottom** — any DENY makes the result DENY (deny-overrides).
- **`ALLOW` is the identity** — `compose([]) = ALLOW`; an action with no evaluators
  is unconstrained *by composition* (authority still applies).
- **Unknown/malformed verdict → ranks as `DENY` (fail-closed).** A broken evaluator
  can only make the outcome *more* restrictive, never less.
- **`compose(V₁ … Vₙ) = fold(meet)`** — n-ary for free, because `meet` is
  associative and commutative.

### Commutativity / associativity ⇒ order has no meaning

Because `meet` is commutative and associative, evaluator **order does not affect
the verdict**. Sequencing (Authority-first vs Legitimacy-first vs parallel) is a
pure *performance* choice — latency, caching, short-circuit — with **no semantic
content**. This is why the old "which comes first" debate was a non-question.

## 4. Mandatory vs discretionary evaluators (veto vs advice)

Not every input is a veto. Two roles:

- **Evaluator (mandatory):** returns a full verdict; its DENY is **authoritative**
  and enters the meet. Authority and Legitimacy are evaluators.
- **Advisor (discretionary):** returns only a *signal* (e.g. a threat class) that a
  mandatory evaluator may map to `CONTAIN`. An advisor **can never** produce `DENY`
  on its own and holds **no authority**.

> **Correctness note (the bug this fixed).** Treating Legitimacy as an *advisor*
> violates §1: an advisor cannot veto, so Authority could execute over a
> Legitimacy objection = "a bad act while authorized." Legitimacy MUST be a
> mandatory **evaluator**. Fixed in `kernel.decide(evaluators=[...])`; see
> `decision-os-min/tests/test_compose.py`.

## 5. Invariants (must hold in every implementation)

```
Invariant 1  (both required)
    No action executes unless  Authority = ALLOW  ∧  Legitimacy = ALLOW
    (generally: unless the composed verdict is PERMITTING).

Invariant 2  (mandatory veto)
    A DENY from ANY mandatory evaluator must prevent execution, and no other
    evaluator's ALLOW may override it.

Invariant 3  (commit is terminal)
    No capability token may be minted before the composed verdict exists.
    The token — the one irreversible grant — is minted only on a PERMITTING
    COMPOSED verdict, so a later evaluator's DENY can never strand a live token.

Invariant 4  (fail-closed composition)
    An evaluator that errors, times out, or returns an unknown verdict is
    composed as DENY.
```

Invariant 3 is enforced structurally: in `kernel.decide`, composition runs
*before* the mint step, and the mint step is gated on the composed
`decision["verdict"] ∈ PERMITTING`.

## 6. Prior art (cite, do not reinvent)

The verdict-composition algebra above is **not new**. At minimum:

- **XACML** combining algorithms — `deny-overrides`, `permit-overrides`,
  `first-applicable`, `deny-unless-permit`, … over `{Permit, Deny, NotApplicable,
  Indeterminate}` (a 4-valued set; see §8).
- **Bonatti, di Vimercati & Samarati**, *An Algebra for Composing Access Control
  Policies*, ACM TISSEC 5(1), 2002.
- **Wijesekera & Jajodia**, *A Propositional Policy Algebra for Access Control*,
  ACM TISSEC 6(2), 2003.
- **Rao, Lin, Li & Lobo**, *An Algebra for Fine-Grained Integration of XACML
  Policies*, SACMAT 2009.
- **Bruns & Huth**, *Access Control via Belnap Logic*, ACM TISSEC 14(1), 2011 —
  four-valued **bilattice** composition (the mature generalization of §8).
- **Crampton & Morisset**, *PTaCL*, POST 2012 — three-valued ABAC composition, and
  the non-monotonicity hazard (§7).
- **Tschantz & Krishnamurthi**, *Reasonability properties for access-control policy
  languages*, SACMAT 2006 — the meta-theory (determinism, monotonicity, safety).

If any part of this repository is genuinely novel, it is **not** this algebra. The
candidates for contribution are the **enforcement coupling** (§9) and the specific
content of the Legitimacy evaluator — both to be established by literature review,
not asserted.

### 6a. The "verified core + untrusted plugins" architecture is ALSO prior art

The §9 design — a small verified Authority core (the TCB) mediating untrusted,
veto-only evaluator plugins in one engine — is **not** a novel property, and this
document claims none for it. It is the classical mixed-assurance / reference-monitor
pattern:

- **Anderson**, *Computer Security Technology Planning Study*, 1972 — the
  **reference monitor** (small, tamper-proof, always-invoked, verifiable).
- **Rushby**, *Design and Verification of Secure Systems*, 1981 — separation kernels.
- **Saltzer & Schroeder**, 1975 — economy of mechanism, least privilege (why the
  TCB is minimized).
- **Klein et al.**, *seL4: Formal Verification of an OS Kernel*, SOSP 2009 — the
  canonical verified core running **unverified** components whose guarantees hold
  regardless. A single system routinely carries **non-uniform assurance**; the claim
  "a unified engine cannot give two assurance levels" is FALSE and is not made here.

The antitone/veto-only argument in §9 is simply the reference-monitor argument
applied to policy composition: the always-invoked, DENY-dominant mediator preserves
the core's guarantee no matter what an untrusted plugin returns.

## 7. Known limitation — obligations do not yet compose

`meet` composes *verdicts* cleanly. It does **not** yet compose **obligations**.
`LIMIT` (redact field X) ∧ `CONTAIN` (sandbox) currently collapses to `CONTAIN`,
losing the redaction. True obligation *union* — and resolving contradictory
obligations (one evaluator needs field X, another redacts it) — is future work and
is where any real research friction lives, not in the verdict meet. Naive n-ary
composition is also vulnerable to **non-monotonicity** (hiding an attribute flips
DENY→ALLOW; Crampton-Morisset, Tschantz-Krishnamurthi); any richer composer must be
checked for it.

## 8. Why two values will not survive `n` evaluators

`{ALLOW, DENY}` is enough for 2 always-applicable evaluators. It breaks once
evaluators can **abstain or fail**: with 10 evaluators, some return "not
applicable", some error, some time out. You then need `NotApplicable` /
`Indeterminate` (XACML) or, better, a **Belnap bilattice** with a separate
*information* ordering (Bruns-Huth). The arity of `compose` is trivial (fold);
**the verdict lattice is the part that must grow.** This is a documented direction,
not a claim.

## 9. Architecture: one kernel; the TCB is authority, not "AuthGate + FDK"

This composition model does **not** require two engines, two services, or two
repos. The blank-page falsification the project adopted:

- **Conceptual split** (Authority vs Legitimacy as distinct predicates): **kept** —
  they vary independently in the real world (a doctor may have access authority yet
  no legitimacy to read a neighbour's record; an act may be hospital-legitimate yet
  outside this doctor's authority). They also consume disjoint inputs (authority:
  actor/grants/capability/purpose; legitimacy: ownership graph/consent/semantics).
- **Module split** (distinct evaluators behind one `Evaluator` interface, composed
  in one place): **this is the design** — one kernel, several evaluator modules.

### The key result: evaluators are antitone ⇒ only authority is trusted

Under deny-dominant `meet`, composition starts from the **authority** verdict and
folds each evaluator in, and `meet` can only move the result toward *more*
restrictive. So every non-authority evaluator is **antitone / veto-only**:

- it can `DENY`/`DEFER`/`CONTAIN`/`LIMIT` (restrict) but its `ALLOW` grants nothing;
- it cannot override an authority `DENY` (`meet(DENY, ALLOW) = DENY`);
- it cannot mint a token or sign — only the kernel does, *after* composition.

Therefore a malicious or buggy Legitimacy/Safety/Privacy/Cost evaluator can at
worst **deny (a DoS)** — it can **never** cause an unauthorized execution. This
places the trust boundary precisely:

```
TCB  (small, verifiable, one unit — Rust-able)
  ├── compose (meet, deny-dominant)
  ├── Authority evaluator     ← the ONLY ALLOW-capable / token-minting part
  └── commit (mint iff composed PERMITTING) + PEP + audit-before-effect
        │  Evaluator interface
        ▼  (UNTRUSTED, veto-only, fail-closed — OUTSIDE the TCB)
  ├── Legitimacy (FDK)
  ├── Safety
  └── Privacy / Cost / …
```

**Consequences (a correction to earlier framing):**

- The real boundary is **TCB (kernel + authority) vs untrusted veto-only plugins**,
  which cuts *across* the old "AuthGate vs FDK" line. FDK/Legitimacy is **not** a
  co-equal engine beside a verified authority kernel; it is a plugin on the
  untrusted side. Differential assurance is real, but it justifies *this* cut — not
  two peer engines.
- Fault isolation, independent scaling, and deploy cadence do **not** justify
  separation — Invariant 4 (fail-closed) and horizontal scaling cover them.
- A **separate FDK repo** remains defensible only for reasons unrelated to security:
  independent research lifecycle, independent ownership, and licensing/attribution.
  If those do not apply, merge it.

> **The boundary that is real is *TCB vs plugins*, not *runtime engine A vs engine
> B*.** Prefer one composing kernel whose only trusted evaluator is authority;
> everything else is an untrusted, fail-closed, veto-only plugin.
