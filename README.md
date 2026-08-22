# contracts-spec — the root of truth for the Decision OS

> **Canonical ecosystem positioning:** [`POSITIONING.md`](POSITIONING.md) (this repo —
> version-controlled). Claim audit: [`CLAIM_AUDIT.md`](CLAIM_AUDIT.md). Repo map:
> [`ECOSYSTEM_MAP.md`](ECOSYSTEM_MAP.md).
>
> "Decision OS" here means the **authority + audit contract plane** for agent tool
> calls — not a universal moral operating system.

**Contracts are the system. Code is just implementations.**

This repository defines the *only* shared truth of the Decision OS: the schemas,
the single decision contract, the event formats, and the policy DSL. Every other
repository depends on this one; **this one depends on nothing.**

It contains **no logic** — no enforcement, no ML, no orchestration. Only the
INPUT to the kernel and the OUTPUT of the kernel, and nothing else.

## What is new — 2026-08-10

**`conformance/` — an executable conformance profile.** A specification document does
not make a standard; a standard is requirements precise enough that an *independent*
implementation can be run against them. Ten requirements (AE-1…AE-10) derived from the
No-Amplification axiom, an implementation-agnostic driver seam, and one real driver.

The load-bearing rule: a requirement whose capability an implementation does not claim
reports **N/A, never PASS**. A suite that scores unimplemented features as conformant
measures nothing.

`conformance/PROFILE.md` §2a attributes **every** requirement to its prior art —
Saltzer & Schroeder 1975, Miller's *Robust Composition* 2006, Anderson 1972 / Rushby
1981 / seL4, Macaroons NDSS 2014, RFC 7800 and DPoP, Haber & Stornetta 1991 — and states
plainly that the profile claims **no new security principle**. If such a profile already
exists, this one is redundant and should be retired in its favour.

**`COMPOSITION.md` §11–§13 — the record of a claim being falsified, fixed, and falsified
again.** §11 withdraws "an untrusted evaluator can at worst deny"; §12 documents the fix
and what it cost; §13 records that a second red team broke that fix, and why the lesson
matters more than the bug: *fail-closed for the variant you happened to write is not
fail-closed*.

**`OBLIGATIONS.md`** — the design for composing obligations, with an explicit novelty
verdict of **none**: an engineering integration of XACML obligations, Lupu & Sloman
conflict resolution, CRDT/OT commutativity, and the k-anonymity generalization lattice.

**`INDEX.md`** — a map of every repository in the stack, with honest status labels.

## Why this exists first

If contracts are not frozen before code, every downstream repo drifts and the
multi-repo system becomes worse than a monolith. So the build order is
non-negotiable:

1. **contracts-spec** (this repo) — truth
2. **CI enforcement** — the dependency + authority + schema-compliance gates
3. **decision-kernel-core** — the only authority, deterministic
4. everything else (control-plane, fdk-research, agent-runtime, audit-ledger)

## Layout

Installable package `decision_os_contracts` (distribution `decision-os-contracts`),
consumed by every other repo (see `INTEGRATION.md`).

```
contracts-spec/
  decision_os_contracts/          # the installable package
    __init__.py                   # validate(), load_schema(), __version__
    schemas/
      action.schema.json          # INPUT to the kernel
      decision.schema.json        # OUTPUT — the SINGLE decision contract (ALLOW/DENY/LIMIT/CONTAIN/DEFER)
      capability_token.schema.json# credential the kernel mints on a permitting decision
      audit_entry.schema.json     # one hash-chained audit record
      event.schema.json           # an event on the system event stream
    conformance/                  # shared rule A/B enforcers + validate()
  policies/dsl_spec.md            # the purpose-binding policy DSL (spec, not code)
  examples/                       # one valid instance per schema (CI validates these)
  tests/                          # schema well-formedness + example validation + conformance
  DEPENDENCY_RULES.md · CONTAINMENT.md · INTEGRATION.md
  VERSION                         # frozen contract version (semver)
```

## The single decision contract (the critical invariant)

Exactly **one** repo — `decision-kernel-core` — may emit a `decision`. Its
`verdict` is one of:

| verdict | meaning |
|---------|---------|
| `ALLOW` | permit the action as submitted |
| `DENY`  | refuse the action |
| `LIMIT` | permit, but only a constrained/minimized form (carries obligations, e.g. redacted fields) |
| `CONTAIN` | permit only inside a locked-down sandbox — the **defensive** response to a suspected-malicious actor (see `CONTAINMENT.md`) |
| `DEFER` | cannot decide now; escalate to a human / higher authority |

Nothing else — not control-plane, not research, not agents — may produce a
`decision`. Research emits `suggestion`/`risk_score`/`threat_assessment` events
only (advisory). `CONTAIN` is strictly **internal** containment; the Decision OS
never acts on, breaks into, or disables an external system
(`DEPENDENCY_RULES.md`, rule E).

> `LIMIT` is the canonical name for what the current AuthGate policy engine
> returns as `TRANSFORM` (an allowed-but-redacted call). The mapping is recorded
> in `schemas/decision.schema.json`.

## Versioning

`VERSION` holds the frozen contract version. Consumers pin a major version.
Breaking a schema requires a major bump and a migration note — never a silent
edit. v0.1.0 is the first frozen draft.

## License

PolyForm Noncommercial 1.0.0 (Required Notice: Ali Pourrahim) — consistent with
the rest of the Decision OS.
