# Authority Enforcement Conformance Profile v0.1

**Status: DRAFT. One implementation tested. Not a standard.**

A specification document does not make a standard — a standard is a set of
requirements precise enough that an *independent* implementation can be run against
them and shown to conform or not. This profile exists to be executable: every
requirement below has an identifier and a corresponding check in `suite.py`, and any
gate that provides a driver can be measured against it.

## 0. What this profile does and does not cover

It covers **authority enforcement**: whether a system can be made to act beyond the
authority explicitly granted to it. It says nothing about whether the *policy* is
wise, whether the *legitimacy* judgement is correct, or whether the system is safe in
any broader sense. A gate can conform to every requirement here and still be
configured to permit something catastrophic. Conformance is a floor, not a warrant.

It also does not cover functional safety, real-time behaviour, fault tolerance,
sensor/actuator integrity, or physical guarantees. A conformant gate is one layer of
a control system, not a control system.

## 1. The governing principle

From `freedom-decision-kernel/PRINCIPLE.md`:

> No entity — human, AI agent, robot, or quantum computer — can create or expand
> authority merely by possessing information or compute. Authority is granted only
> through explicit, auditable, attenuable rules.

Formally: authority is an element of a lattice `(A, ⊑)` where `a ⊑ b` means "a grants
no more than b". `grant()` is the **only** operation that raises authority; it is an
issuance — explicit, signed, auditable, revocable. Every runtime composition of a
base authority with constraint inputs `k₁…kₙ` (legitimacy, safety, privacy, budget,
risk, human approval, …) satisfies:

```
compose(a, k₁, …, kₙ) ⊑ a          (No Amplification)
```

Information and compute enter the system only as constraint inputs that **narrow**.
Every requirement below is an operational consequence of this one axiom.

## 2. Requirements

Keywords MUST / MUST NOT / SHOULD are used as in RFC 2119.

### AE-1 — Default deny
Absent an explicit grant, authority is bottom. A gate MUST refuse an action whose
actor holds no grant covering it. Unknown MUST NOT be treated as permitted.

### AE-2 — No amplification
For any base authority and any set of constraint inputs, the composed outcome MUST
NOT be more permissive than the base authority alone. Adding a constraint input MUST
NOT turn a refusal into a permission, MUST NOT widen the set of permitted tools, and
MUST NOT relax an obligation attached by the base authority.

### AE-3 — Constraint inputs are veto-only
A component that supplies a constraint (legitimacy, safety, privacy, cost, …) MUST
NOT be able to grant. Its permitting answer MUST have no effect beyond what the base
authority already permitted. Its refusing answer MUST be honoured.

Corollary, and the one most often violated in practice: a constraint input MUST NOT
be able to determine *what executes* — not the tool, not the payload, not the
sandbox in which it runs. A component that can rewrite the executed action is
exercising authority regardless of what its verdict says.

### AE-4 — Attenuation
Where delegation is supported, a delegated authority MUST grant no more than its
parent: `delegate(a) ⊑ a`. This MUST hold transitively along a delegation chain, so
that authority at depth *n* is bounded by authority at depth *n−1*.

### AE-5 — Temporal attenuation
Where expiry is supported, a delegated authority MUST NOT outlive its parent:
`expiry(child) ≤ expiry(parent)`. An expired authority MUST be refused.

### AE-6 — Revocation monotonicity
Where revocation is supported, once an authority is revoked no later action MUST be
permitted under it, including actions authorized before the revocation but not yet
executed. Revocation MUST NOT be defeatable by replaying prior evidence.

### AE-7 — Action binding
An authorization MUST be bound to the specific action it authorized — actor,
operation, and the security-relevant content of the payload. It MUST NOT be
re-attachable to a different action. Changing the payload after authorization MUST
invalidate it.

### AE-8 — Single use
Where one-time capabilities are supported, an authorization MUST NOT be spendable
twice, including across processes or instances.

### AE-9 — Non-bypass
No execution path MUST exist that reaches the effect without passing the enforcement
boundary. Every route into the tool — direct executor use, convenience wrappers,
adapters — MUST be mediated.

### AE-10 — Audit fidelity
Every decision and every effect MUST produce a record, and the record MUST match what
happened: no effect without a record, no record of an effect that did not occur, and
the recorded reason MUST be the reason the decision was made. A failure to write the
record MUST NOT leave an effect already performed.

## 2a. Prior art — none of these requirements is new

Stated explicitly so no reader mistakes this profile for a contribution to access
control. Every requirement is an established result; the profile's only job is to
make them **measurable for one specific setting** (autonomous-agent tool calls).

| Req | Established as |
|---|---|
| AE-1 default deny | Saltzer & Schroeder 1975, "fail-safe defaults" |
| AE-2 no amplification | **Miller, *Robust Composition*, 2006** — authority is not amplified by composition, only by explicit delegation (POLA). Also XACML 3.0 `deny-overrides` |
| AE-3 constraint inputs are veto-only | The same result, plus Anderson's reference monitor (1972) and the separation-kernel line (Rushby 1981; Klein et al., seL4, 2009) |
| AE-4 attenuation | **Macaroons** (Birgisson et al., NDSS 2014) — caveats can only attenuate; **Biscuit** for the offline/Datalog form |
| AE-5 temporal attenuation | Macaroons (expiry caveats); capability expiry generally |
| AE-6 revocation monotonicity | Standard in capability systems (KeyKOS, E); OAuth token revocation |
| AE-7 action binding | Sender-constrained / proof-of-possession tokens — RFC 7800, DPoP (RFC 9449) |
| AE-8 single use | Replay prevention via `jti`/nonce — OAuth, Kerberos |
| AE-9 non-bypass | Complete mediation, Saltzer & Schroeder 1975 |
| AE-10 audit fidelity | Baseline compliance/forensics requirement; tamper-evident logs (Haber & Stornetta 1991) |

**Therefore this profile claims no new security principle.** It claims that these
requirements have not been assembled into an executable conformance profile for
agent tool calls, and that a gate for that setting should be measured against all ten
rather than a subset. If someone has already published such a profile, this one is
redundant and should be retired in its favour.

Neighbouring work that already does part of this well, and should be adopted rather
than reinvented: **AWS Cedar** (formally verified authorization, Lean proofs),
**OPA/Rego** (policy-as-code, CNCF), **Zanzibar/OpenFGA/SpiceDB** (ReBAC at scale),
**SPIFFE/SPIRE** (workload identity). In particular, AE-4 and AE-5 should be
satisfied by adopting a macaroon/biscuit-style attenuation format — inventing a new
delegation format here would be the one place where "not invented here" would
directly cost credibility.

## 3. Reporting

Each requirement returns exactly one of:

- **PASS** — the check ran and the requirement held.
- **FAIL** — the check ran and the requirement was violated.
- **N/A** — the implementation does not claim the underlying capability (e.g. no
  delegation), so the requirement does not apply.

**N/A is never reported as PASS.** A suite that scores an unimplemented feature as
conformant measures nothing. An implementation's conformance claim must therefore
state both the requirements it passes *and* the ones it does not implement — "passes
6 of 10, 4 not applicable" is an honest claim; "100% conformant" from the same run is
not.

## 4. Honest status of this profile

- **One implementation** has been run against it. A profile validated against a single
  implementation mostly measures that implementation.
- The requirements are derived from one project's threat model. They are not the
  product of multi-party review, and no external party has agreed to them.
- Several requirements (AE-4, AE-5, AE-6) are untested against any implementation
  that actually supports delegation.
- Until a second, independently-written gate is measured, this is a **checklist with
  a test runner**, not a standard. That is a statement of where it is, not a
  disparagement of where it could go — the order is implementations first,
  codification second, and every standard worth the name was written that way.
