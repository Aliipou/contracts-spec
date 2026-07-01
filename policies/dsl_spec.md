# Purpose-binding policy DSL — specification (v0.1)

This is the **spec** of the declarative policy the kernel evaluates. It is not
code and carries no logic of its own; `decision-kernel-core` implements an
evaluator for it. It formalizes the policy the current AuthGate
`policies/purpose_policy.json` already speaks.

## Document shape

```json
{
  "version": 1,
  "default": "deny",
  "purpose_bindings": {
    "<data_purpose>": ["<action_purpose>", "..."]
  },
  "redactions": [
    {
      "action_purpose": "<action_purpose>",
      "redact_fields": ["<field-name>", "..."],
      "redact_patterns": ["<regex>", "..."]
    }
  ]
}
```

## Semantics (deterministic)

1. **Purpose binding.** For each `data_label` on an action, the action's
   `action_purpose` must appear in that label's permitted list. One mismatch →
   `DENY`. An unknown data purpose under `default: "deny"` → `DENY`.
2. **Data minimization → LIMIT.** If permitted, a matching redaction rule strips
   fields not needed for the purpose:
   - `redact_fields`: field names redacted at **any depth** (nested/aliased).
   - `redact_patterns`: values matching a sensitive **content** pattern (e.g. an
     SSN/PAN) are scrubbed wherever they appear, regardless of the (possibly
     lying) self-attached label. This is a known-format floor, not a proof.
   A redaction that fires yields verdict `LIMIT` with the minimized
   `transformed_payload` and `obligations` naming what was stripped.
3. **Otherwise → ALLOW.**

## Non-goals

- No probabilistic scoring, no ML, no "helpfulness". A given (policy, action)
  pair always yields the same verdict.
- Ranking, necessity scoring, and anomaly detection are **advisory** and live in
  `fdk-research`; they never produce a verdict.
