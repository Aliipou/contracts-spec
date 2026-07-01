"""Rule B — single-authority constraint (AST-based, formal).

Only `decision-kernel-core` may EMIT a Decision. This scans a NON-kernel package's
source and fails if it constructs one. Emission is detected as:

  * a call ``Decision(...)`` (constructing the decision object), or
  * a dict literal carrying ``"verdict": "<ALLOW|DENY|LIMIT|CONTAIN|DEFER>"``
    (constructing a decision message by hand).

It deliberately does NOT flag *reading* a verdict (``decision.verdict``,
``x == "DENY"``): consumers are allowed to inspect a decision, only not to
produce one. This keeps false positives near zero while catching real emission.

Honest limit: like all static checks this can be evaded at runtime; the
non-bypassable complement is the kernel refusing any Decision whose ``issued_by``
is not itself, and executors requiring a kernel-signed capability token. Static
here, runtime there.

CLI:  python -m conformance.check_authority --roots <dir> [<dir> ...]
Exit code 1 if a non-kernel tree emits a Decision.
"""

from __future__ import annotations

import argparse
import ast
from pathlib import Path

_VERDICTS = {"ALLOW", "DENY", "LIMIT", "CONTAIN", "DEFER"}


def _emission_sites(tree: ast.AST) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            name = f.id if isinstance(f, ast.Name) else getattr(f, "attr", None)
            if name == "Decision":
                out.append((node.lineno, "constructs Decision(...)"))
        if isinstance(node, ast.Dict):
            for key, val in zip(node.keys, node.values, strict=False):
                if (
                    isinstance(key, ast.Constant)
                    and key.value == "verdict"
                    and isinstance(val, ast.Constant)
                    and val.value in _VERDICTS
                ):
                    out.append((node.lineno, f"emits a decision dict (verdict='{val.value}')"))
    return out


def check(roots: list[str]) -> list[str]:
    violations: list[str] = []
    for root in roots:
        for py in sorted(Path(root).rglob("*.py")):
            tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
            for lineno, what in _emission_sites(tree):
                violations.append(
                    f"{py}:{lineno}: non-kernel code {what} — only the kernel may emit a Decision"
                )
    return violations


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Decision OS single-authority checker (rule B).")
    ap.add_argument("--roots", nargs="+", required=True, help="source dirs of a NON-kernel repo")
    args = ap.parse_args(argv)
    violations = check(args.roots)
    for v in violations:
        print(v)
    if violations:
        print(f"\nRULE B FAILED: {len(violations)} authority violation(s).")
        return 1
    print("rule B OK — no non-kernel Decision emission.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
