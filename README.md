# contracts-spec — the root of truth for the Decision OS

**Contracts are the system. Code is just implementations.**

This repository defines the *only* shared truth of the Decision OS: the schemas,
the single decision contract, the event formats, and the policy DSL. Every other
repository depends on this one; **this one depends on nothing.**

It contains **no logic** — no enforcement, no ML, no orchestration. Only the
INPUT to the kernel and the OUTPUT of the kernel, and nothing else.

## Why this exists first

If contracts are not frozen before code, every downstream repo drifts and the
multi-repo system becomes worse than a monolith. So the build order is
non-negotiable:

1. **contracts-spec** (this repo) — truth
2. **CI enforcement** — the dependency + authority + schema-compliance gates
3. **decision-kernel-core** — the only authority, deterministic
4. everything else (control-plane, fdk-research, agent-runtime, audit-ledger)

## Layout

```
contracts-spec/
  schemas/
    action.schema.json            # INPUT to the kernel
    decision.schema.json          # OUTPUT of the kernel — the SINGLE decision contract
    capability_token.schema.json  # the credential the kernel mints on a permitting decision
    audit_entry.schema.json       # one hash-chained audit record
    event.schema.json             # an event on the system event stream
  policies/
    dsl_spec.md                   # the purpose-binding policy DSL (spec, not code)
  examples/                       # one valid instance per schema (CI validates these)
  tests/                          # schema well-formedness + example validation
  DEPENDENCY_RULES.md             # the golden rules every repo's CI must enforce
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
| `DEFER` | cannot decide now; escalate to a human / higher authority |

Nothing else — not control-plane, not research, not agents — may produce a
`decision`. Research emits `suggestion`/`risk_score` events only.

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
