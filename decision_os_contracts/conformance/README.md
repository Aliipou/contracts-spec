# conformance — reference enforcers for the Decision OS rules

Meta-tooling that makes `DEPENDENCY_RULES.md` executable. Each consumer repo runs
the relevant checks in its own CI; a violation fails the build.

| Rule | Checker | What it enforces |
|------|---------|------------------|
| A — dependency | `check_imports.py` | the layer imports nothing forbidden (AST; catches plain/aliased/dotted imports and bans dynamic-import escape hatches) |
| B — single authority | `check_authority.py` | a NON-kernel repo never emits a `Decision` (no `Decision(...)`, no hand-built verdict dict) |
| C — schema compliance | `validate.py` | every boundary message validates against a bundled schema |

## Wiring it into a consumer repo's CI

```yaml
- name: Rule A — import boundary
  run: python -m conformance.check_imports --policy ci/import_policy.json
- name: Rule B — single authority (non-kernel repos only)
  run: python -m conformance.check_authority --roots <your-source-dir>
# Rule C is exercised in tests:  from conformance import validate
```

`import_policy.json` shape (see `policy.example.json`):

```json
{ "rules": [ { "roots": ["src"], "forbidden": ["fdk_research", "research"], "ban_dynamic_import": true } ] }
```

## Honest scope (do not overclaim)

These are **static** checks. A determined insider can evade any static analysis at
runtime (`getattr`/`eval`, dynamically assembled module objects). That is why the
authority rule is **also** enforced at runtime by the kernel — it rejects any
`Decision` whose `issued_by` is not itself, and executors require a kernel-signed
capability token. Static (here) + runtime (kernel) is the defense in depth;
neither alone is claimed total. The checkers make the *static* bypasses loud, and
ban the escape hatches (dynamic import) that would otherwise make static analysis
meaningless.
