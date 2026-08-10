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

## 10. Convergence bricks (evidence, not intention)

ADR-0001 says the target is ONE host kernel composing an authority evaluator and
untrusted veto-only plugins, while three engines exist today. Migration is deferred,
so the risk is that the target stays a slogan. Each "brick" is therefore a *test*
that retires one stacked engine by proving the composed form is equivalent to it —
and, where possible, strictly safer.

**Brick #1 — legitimacy (done).** `decision_os_min/evaluators.py::legitimacy` adapts a
boolean legitimacy policy into a veto-only, fail-closed evaluator.
`tests/test_evaluators.py` proves the sequential `LegitimacyAuthorityPipeline` and
`handle(..., evaluators=[legitimacy(policy)])` agree on the whole
legitimacy × authority truth table (verdict, executed, output). The sequential stage
is therefore redundant and deletable.

**Brick #2 — a second authority engine (done).** `evaluators.py::authority` adapts an
external authority engine (e.g. an AuthGate deployment) into a co-equal evaluator.
`tests/test_authority_convergence.py` proves, over the full truth table:

1. **Equivalence** — composed verdict == the stacked pair's verdict, every cell.
2. **Commutativity** — evaluator order is semantically empty (§3 restated as a test).
3. **Non-leak** — this is the part that is not merely tidier. *Stacked*, engine A
   rules and MINTS a one-time capability before engine B is consulted, so B's refusal
   arrives after the mint and a live token exists for a refused action. *Composed*,
   the veto lands before the mint and no token is created. Stacking engines therefore
   violates the token-mint-is-terminal-commit invariant (I3) by construction;
   composition satisfies it by construction.
4. **Fail-closed twice** — a raising engine denies, and a verdict outside the lattice
   denies rather than being read as permission. The second case is not hypothetical:
   AuthGate's own dialect is lowercase `allow`/`deny`/`transform`, so vocabulary drift
   between two engines is exactly the shape of an accidental grant. Dialect mapping is
   the adapter's job and is deliberately kept out of this package.
5. **Veto-only** — an external `ALLOW` cannot resurrect the host's `DENY`, and the
   host's reason survives composition.
6. **Real parity** — the same, against the actual `authgate_gate.PolicyEngine`, so the
   claim is about the neighbouring engine and not only about a stand-in. The test skips
   where that sibling repo is not importable; this package still depends on nothing but
   stdlib + `cryptography`.

**Honest status.** These bricks show the stacked paths are *redundant*. They are not
themselves the migration: no engine has been deleted, and AuthGate's distinctive
checks (capability layer, runtime monitor, notary) are not yet expressed as evaluators
— only its policy verdict is. The remaining blocker before any deletion is
§7 (obligations do not yet compose): an engine whose verdict carries a redaction
cannot be folded in without losing it.

## 11. FALSIFIED — "an untrusted evaluator can at worst deny" (2026-08-10)

§9 and ADR-0001 claim that because evaluators are antitone, a malicious or buggy
evaluator can at worst **deny (a DoS)** and can **never** cause an unauthorized
execution. **That claim is false as implemented, and is withdrawn until the code
earns it.** A red-team pass produced runnable exploits (`decision-os-min/tests/
test_redteam_composition.py`, 31 tests), independently reproduced. The three that
matter, all verified by hand:

1. **Field injection.** `more_restrictive` adopts the *entire* dict an evaluator
   returns. An evaluator that returns an **off-lattice** verdict (`"deny"` —
   lowercase, i.e. a plausible neighbouring dialect) carrying a forged `token_id`
   and `capability` gets those fields **signed by the kernel**, and the PEP gates on
   a blacklist (`verdict in (DENY, DEFER) or not token_id`) rather than on
   `verdict in PERMITTING`. Result: composed verdict non-permitting, no token
   minted by the kernel — **and the tool still runs**, with `verify()` accepting the
   forged decision.
2. **TOCTOU on the live action.** Evaluators receive the mutable action dict, and
   `capability` + `action_fingerprint` are computed *after* the evaluator loop. An
   evaluator that rewrites `action["capability"]`/`["tool"]` and returns `ALLOW`
   causes a tool the actor was never granted to execute — with a perfectly valid
   signature and binding, because the fingerprint commits to the *mutated* action.
3. **Obligation authorship.** `LIMIT` outranks `ALLOW`, so an evaluator "restricting"
   an action becomes the governing decision and its `transformed_payload` is what
   executes. A veto-only plugin thereby **chooses the payload** ($1 → $1,000,000)
   while the signed `action_binding` still commits to the original.

**The diagnosis is precise, and it is not the lattice.** The verdict algebra
survives falsification: property tests (~85k generated examples) confirm antitone,
DENY-absorbing, token-iff-permitting, and that no verdict input ever moved the
kernel below its own authority ruling. What fails is the **plumbing around the
lattice** — the meet is antitone, the *decision dict* is not. An evaluator
contributes fields (token, capability, payload, containment, `action_ref`) that
never enter the meet at all.

**The one invariant that does hold:** no evaluator can override an authority `DENY`
(rank ties keep the authority decision, and authority seeds the fold).

**Root causes** — R1 `more_restrictive` adopts the plugin's whole dict; R2 unknown
verdicts *rank* as DENY but are *returned verbatim*, and the PEP blacklists instead
of whitelisting; R3 evaluators get the live action, and identity fields are derived
after the loop.

Consequences for §10: the convergence bricks stand as *equivalence* results — they
say a stacked engine is redundant, and that stacking violates token-mint-terminal.
They say nothing about plugin containment, and must not be read as evidence for it.
Brick #2's equivalence test compares the **verdict field only**, which is why it did
not catch an external `LIMIT` executing with an empty payload.

## 12. The fix (2026-08-10) — what §11 costs, and what it buys

§11 stands as the record of what was broken; this section records the repair. Four
changes in `decision-os-min`, each aimed at one root cause:

**R1 — an evaluator may contribute a verdict and a reason, and nothing else.**
`compose.sanitize()` filters an evaluator's decision to `EVALUATOR_CONTRIBUTABLE`
= {`verdict`, `reason`, `action_ref`}, and `action_ref` is then overwritten with the
kernel's own value. `token_id`, `capability`, `token_expires_at`, `containment`,
`transformed_payload`, `issued_by`, `action_binding` can no longer be injected. This
is what makes the antitone argument true of the *decision* and not merely of the
*meet*.

**R2 — the lattice is closed, and the PEP whitelists.** `compose.normalize()` maps
anything outside `VERDICTS` to `DENY` *inside* `meet`, so (a) `meet` is commutative
for arbitrary strings rather than only up to rank, (b) a composed verdict is always
a lattice member, and (c) a consumer testing `verdict == DENY` can no longer be
fooled by a neighbouring engine's lowercase dialect. The PEP gate changed from the
blacklist `verdict in (DENY, DEFER) or not token_id` to the whitelist
`verdict not in PERMITTING or not token_id`.

**R3 — evaluators cannot touch the action.** Each receives `copy.deepcopy(action)`.
This closes the TOCTOU escalation (rewriting `capability` so an ungranted tool runs
under a valid signature) and also stops one evaluator hiding an attribute from the
next. Cost: one deep copy per evaluator per decision — accepted, because the
alternative is an argument about which fields are safe to share, and that argument
is exactly what failed.

**I4 at the kernel boundary.** A raising evaluator becomes `DENY` instead of
propagating an unstable exception out of `decide()`; a non-mapping return
(`None`, `42`, `["ALLOW"]`) and an unhashable verdict fail closed. `BaseException`
is deliberately NOT caught — `KeyboardInterrupt`/`SystemExit` are process shutdown,
not a verdict.

**A consequence worth stating plainly, because it is a real loss.** An evaluator can
no longer carry an obligation. A plugin `LIMIT` therefore has no redaction to apply,
and a `LIMIT` the PEP cannot discharge is now **refused** rather than degraded — the
old fallback called the tool with an empty payload, which is a *different* effect,
not a more restrictive one. So a plugin's "restrict" collapses to a clean veto. That
is correct for a veto-only plugin and it is fail-closed, but it means obligations
from plugins are unavailable until OBLIGATIONS.md is implemented. Refusing to carry
an obligation is better than silently honouring an unverified one; it is still a gap,
not a feature.

**Status of the claim §11 withdrew.** The three root causes are closed against the
exploits that demonstrated them — verified by hand, independently of the test suite:
field injection, TOCTOU escalation, and payload authorship all now refuse, while a
genuine `ALLOW` still executes. That is *evidence the specific attacks are dead*, not
proof the general claim is now true. ADR-0001's "an untrusted evaluator can at worst
deny" should be restored only after the exploit suite has been re-pointed at the
fixed behaviour AND a fresh adversarial pass has failed to find a new escape. Until
then the banner on ADR-0001 stays.

## 13. Round 2 — the fix in §12 was not enough (2026-08-10)

A second adversarial pass, given no knowledge of the §12 fix, broke it. The result
matters more than the bug, so it is recorded rather than quietly patched.

**The break.** `normalize` returned the CALLER'S OBJECT when `verdict in _RANK`
succeeded — and `in` is a hash/eq lookup. A `str` subclass could therefore make its
VALUE and its IDENTITY disagree: value `"DENY"`, so `more_restrictive` ranked it
most-restrictive and let it govern the fold; `__hash__`/`__eq__` impersonating
`"ALLOW"`, so the kernel's mint gate and the PEP's `verdict in PERMITTING` test both
said yes. A semantic **veto minted a one-time token and executed the tool**, and
`verify()` accepted the decision — `json.dumps` serializes a subclass by value, so
the forgery is self-consistent and no signature check can catch it. Placed before an
honest evaluator, it also tied at the top rank and had that evaluator's real veto
discarded.

**Why this is the interesting part.** The *previous* pass found this exact defect and
filed it as a harmless scope limit, because the liar it happened to construct ranked
as DENY and was fail-closed. One construction sharper, the same defect was an
execution. **"Fail-closed for the variant I happened to write" is not fail-closed** —
and a fix aimed at the demonstrated variant rather than the mechanism will keep
producing this outcome.

**The fix.** The lookup key comes from `str.__str__` (the base implementation, which
a `__str__` override cannot lie about) and the return value is the interned lattice
member, never the caller's object — so an attacker-controlled `__hash__`/`__eq__`
cannot reach any downstream membership test. `more_restrictive` no longer calls
`str()` first, which was itself spoofable.

**Second break, same root shape.** `reason` is the one field an evaluator still owns,
and it flows into both the signed decision and the audit log — which serialized with
DIFFERENT tolerances (`_canonical` passed `default=str`, the audit path did not). A
`reason` that signs but will not log made the mandatory audit write raise AFTER the
tool ran, as a bare `TypeError` that `handle` does not catch: **effect executed, log
empty**, defeating HB-3's one-entry-per-execute guarantee. Fixed at both ends —
`sanitize` coerces `reason` to a plain `str`, and the audit path serializes with
`default=str`.

**What round 2 could NOT break** (each a passing assertion, so the surface is
demonstrably covered): field injection through `sanitize`; off-lattice plain strings;
plugin `LIMIT`/`CONTAIN` without an obligation; capability escalation by mutating the
deep-copied action; injecting `action_ref`/`action_binding`; token replay. And the
invariant that has survived every round: **an evaluator cannot override the
AUTHORITY's DENY** — authority seeds the fold at the top rank and ties keep it.

**Still open, and NOT a code defect.** An in-process evaluator can walk the stack
(`sys._getframe`) to reach the kernel's signing key and forge anything. Python is not
a sandbox. This is the runtime-isolation question ADR-0001 leaves open, and it means
the claim in §9 must be stated **conditionally**: veto-only holds against an evaluator
confined to the `Evaluator` interface, not against arbitrary in-process code. The ADR
banner stays until that condition is written into the contract normatively.
