# Defensive containment model (the CONTAIN verdict)

How the Decision OS handles a suspected-malicious agent or action. This is a
**defensive** model: the system nullifies a threat's effect **within its own
execution domain** and never acts on anything outside it.

## The one hard line

> **No external enforcement.** The Decision OS never accesses, exploits, breaks,
> disables, or "hacks back" any external system — not even an attacker's. Doing
> so is offensive cyber capability, illegal outside state/law-enforcement
> frameworks, and it is *not* how real systems stay secure. Security comes from
> **total control of your own domain against the adversary**, not from striking
> the adversary.

## Detection is advisory; the decision is authoritative

```
Incoming agent / action
        │
        ▼
AuthGate (identity & integrity)         ── is this actor who it claims, unmodified?
        │
        ▼
FDK  (behavioral threat classifier)     ── ADVISORY: benign | suspicious | malicious | unknown
        │  emits a `threat_assessment` event (never a decision)
        ▼
decision-kernel-core (SOLE authority)   ── ALLOW | LIMIT | DENY | CONTAIN | DEFER
        │
        ▼
if CONTAIN ─► sandboxed execution ─► no external impact beyond the boundary ─► audit
```

- **FDK does not neutralize anything.** It scores behavior/intent and emits a
  `threat_assessment` (see `schemas/event.schema.json`). It is HIGH-risk,
  experimental, and advisory-only — exactly like every other `fdk-research`
  output.
- **Only the kernel decides.** A `CONTAIN` verdict is a `Decision` (see
  `schemas/decision.schema.json`), and only `decision-kernel-core` may emit it.

## What CONTAIN means (and does not)

CONTAIN **is**: run the action only inside an isolated sandbox with the
constraints in `Decision.containment` —

- `sandbox: true`, `network: none|restricted`, `allowed_tools: []` (minimal),
- `persistence: false`, `privilege_escalation: false`, `time_limit_seconds: N`.

CONTAIN **is not**: hacking the agent, destroying an external system, running an
exploit, taking control of another host, or any outward action. The contained
actor simply cannot *affect* anything beyond the sandbox.

## CONTAIN is deterministic + policy-driven — never ML-driven

The verdict `CONTAIN` is decided by the deterministic kernel from policy, using
FDK's `threat_assessment` only as **advisory input**. It is NOT chosen by an ML
model in the loop. This is a hard design rule, because an ML-driven CONTAIN
invites three failure modes: model bias, agents perpetually falling back to
containment, and false-positive explosion. Same reason `LIMIT` is policy-driven:
a given (policy, action, advisory-signal) triple must always yield the same
verdict.

## Why this is the only correct model

You do not control the outside world — only your own execution domain. So the
security goal is not "defeat the attacker" but "reduce the attacker's effect on
you to zero." Escalation, false positives harming real users, and uncontrolled
propagation are exactly the failure modes an offensive design invites; a
containment design has none of them.

## One-line mental model

**The system does not destroy the adversary; it denies the adversary any effect
inside the system.**
