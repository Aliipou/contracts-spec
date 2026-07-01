# Cross-repo integration — the standard consumption pattern (Phase 3.5)

How every other Decision OS repo consumes the shared truth. Decision: **Python
package, pinned by version** (not submodule/subtree) — clear semver, clean
rollback, natural CI.

## The package

`contracts-spec` publishes the importable package **`decision_os_contracts`**
(distribution name `decision-os-contracts`), version = the frozen contract
version (`__version__`, currently `0.2.0`). It bundles the schemas (as data), the
`validate()`/`load_schema()` helpers, and the shared `conformance` enforcers.

`decision-kernel-core` publishes **`decision-kernel-core`** the same way; it
depends on `decision-os-contracts`.

## How a consumer depends on it

Pin an exact version in the consumer's `pyproject.toml`:

```toml
dependencies = [
  "decision-os-contracts @ git+https://github.com/Aliipou/contracts-spec.git@v0.2.0",
]
```

and in the consumer's CI:

```yaml
- run: python -m pip install -e ".[dev]"
- run: python -m decision_os_contracts.conformance.check_imports --policy ci/import_policy.json
- run: python -m decision_os_contracts.conformance.check_authority --roots src   # non-kernel repos
```

Consumers now use the **shared** rule A/B checkers and the **shared** schemas
instead of vendoring their own — one source of truth.

### Private-repo note (one-time infra)

These repos are private, so a consumer's CI needs read access to install the
dependency from git. Provide it once via either a **deploy key** on the consumer
repo, or a **PAT stored as an Actions secret** used in the install URL. This is
the only manual credential step; after it, `pip install` from a pinned tag is
fully automatic. (Until it's set, `decision-kernel-core` keeps a vendored, pinned
copy of the schemas under `contracts/` so its CI stays green stand-alone.)

## Version compatibility policy

- Contracts version is **semver**. Consumers pin a **major**; a breaking schema
  change (e.g. a new required field, or removing a verdict) is a **major** bump
  with a migration note. Additive, back-compatible changes are minor.
- A consumer declares the contract range it supports; CI fails if the installed
  `decision_os_contracts.__version__` is outside it.

## Roadmap — the four maintainability gaps (Ali's list)

1. **Version compatibility** across repos — the pin + supported-range check above.
2. **Release pipeline** — tag → build → (sign) → changelog; a `CHANGELOG.md` and a
   `git tag vX.Y.Z` per repo; migration policy on majors.
3. **System-wide threat model** — one document covering the *composed* system
   (agent → control-plane → kernel → execution → audit), not each repo alone.
4. **Cross-repo integration tests** — a harness that installs the pinned repos
   together and exercises a full decision→token→execute→audit flow. Candidate
   home: a future `decision-os-sdk` (client libs + verification/token helpers +
   examples) so consumers never touch kernel internals directly.
