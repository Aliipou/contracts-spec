# Dependency & authority rules (the golden rules)

These are the invariants every repo's CI in the Decision OS **must** enforce.
They are the whole reason the system is multi-repo: separation is not for tidy
code, it is for **enforcing trust boundaries** that a monolith cannot.

## The dependency graph

```
agent-runtime ─┐
control-plane ─┼──→ decision-kernel-core ──→ execution
fdk-research ──┘

ALL repos ───────→ contracts-spec        (read-only; contracts-spec depends on NOTHING)
audit-ledger  ←── ALL                    (append-only writes)
```

## Rule A — dependency rule

`decision-kernel-core` **MUST NOT** import `fdk-research`, `agent-runtime`, or
`control-plane`. The kernel depends only on `contracts-spec`. Research leaking
into the kernel makes it non-deterministic and the whole system unverifiable.

*Enforced by:* AST-based import scanning in each repo's CI (an import of a
forbidden package fails the build). AuthGate's existing `boundary-guard` already
performs exactly this class of check.

## Rule B — authority rule (single decision contract)

Only `decision-kernel-core` may emit a `decision` (verdict `ALLOW`/`DENY`/
`LIMIT`/`DEFER`). `control-plane`, `fdk-research`, and `agent-runtime` MUST NOT
construct or return a `decision`; research emits `suggestion`/`risk_score`
events only.

*Enforced by:* (1) a grep/AST check that the decision verdict literals and the
`Decision` type are constructed only inside the kernel repo; (2) at runtime, a
`decision` whose `issued_by` is not the kernel identity is rejected.

## Rule C — schema compliance

Every message crossing a repo boundary MUST validate against the corresponding
`contracts-spec` schema, pinned to a major version. No ad-hoc shapes.

*Enforced by:* schema-validation tests in each repo against the pinned
`contracts-spec` version.

## Rule E — no external enforcement (defensive-only)

The Decision OS acts **only within its own execution domain**. No component may
access, exploit, break, disable, or "hack back" any external system — including a
detected attacker's. A malicious agent is handled by the `CONTAIN` verdict
(internal sandboxing/isolation), never by outward action. FDK *classifies* threat
behavior (advisory `threat_assessment`); it never *neutralizes* anything and the
kernel alone decides. See `CONTAINMENT.md`.

*Enforced by:* the decision vocabulary itself (there is no "attack"/"disable"
verdict — only ALLOW/DENY/LIMIT/CONTAIN/DEFER, all internal), plus review that no
component performs outbound offensive actions.

## Rule D — audit is write-only

`audit-ledger` accepts appends only. No API edits or deletes an entry. Integrity
is by hash chain; tamper-EVIDENCE is by an out-of-process anchor (notary).

## Trust levels (for reference)

| Layer | Authority | Risk | May emit |
|-------|-----------|------|----------|
| decision-kernel-core | YES (sole) | LOW (deterministic) | `Decision`, `CapabilityToken` |
| control-plane | NO | MEDIUM | routing events |
| fdk-research | NO | HIGH (experimental) | `suggestion`, `risk_score` (advisory) |
| agent-runtime | NO | HIGH | `action_proposed` (proposals) |
| audit-ledger | NO | LOW | append-only writes |

## One-line mental model

**Contracts define truth. The kernel enforces truth. Everything else is optional
intelligence.**
