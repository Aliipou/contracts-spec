"""Rule A — import-boundary enforcement (AST-based, policy-driven).

`decision-kernel-core` MUST NOT import research/agent/control layers. This scans
a package's source with the `ast` module (not regex — regex is trivially fooled)
and fails the build on any forbidden import.

Made hard to bypass:
  * catches `import x`, `import x.y`, and `from x.y import z` (top-level and dotted);
  * in a boundary-restricted layer, ALSO bans the dynamic-import escape hatches
    (`__import__(...)`, `importlib.import_module(...)`) — because they can smuggle
    a forbidden module past any static check, so their mere presence in the kernel
    is itself a violation.

Honest limit (stated, not hidden): static analysis cannot catch a determined
runtime evasion (e.g. `getattr`/`eval` building a module object). That is why the
authority rule is ALSO enforced at RUNTIME by the kernel (issued_by validation +
signed capability tokens). Static + runtime = defense in depth; neither alone is
claimed to be total.

CLI:  python -m conformance.check_imports --policy <policy.json>
Exit code 1 on any violation.
"""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

_DYNAMIC_IMPORT_NAMES = {"__import__", "import_module"}


def _call_name(func: ast.expr) -> str | None:
    """The simple name of a call target: `f()` -> 'f', `m.f()' -> 'f'."""
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _static_imports(tree: ast.AST) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.extend((alias.name, node.lineno) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            out.append((node.module, node.lineno))
    return out


def _dynamic_import_sites(tree: ast.AST) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            name = _call_name(f)
            if name in _DYNAMIC_IMPORT_NAMES:
                out.append((name, node.lineno))
    return out


def _forbidden(module: str, forbidden: list[str]) -> str | None:
    top = module.split(".")[0]
    for pref in forbidden:
        if module == pref or module.startswith(pref + ".") or top == pref:
            return pref
    return None


def check_file(path: Path, forbidden: list[str], ban_dynamic: bool) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations: list[str] = []
    for module, lineno in _static_imports(tree):
        hit = _forbidden(module, forbidden)
        if hit:
            violations.append(f"{path}:{lineno}: forbidden import '{module}' (rule bans '{hit}')")
    if ban_dynamic:
        for name, lineno in _dynamic_import_sites(tree):
            violations.append(
                f"{path}:{lineno}: dynamic import '{name}(...)' banned in this layer "
                f"(it can smuggle a forbidden import past static checks)"
            )
    return violations


def check(policy: dict) -> list[str]:
    violations: list[str] = []
    for rule in policy.get("rules", []):
        forbidden = rule.get("forbidden", [])
        ban_dynamic = rule.get("ban_dynamic_import", True)
        for root in rule.get("roots", []):
            for py in sorted(Path(root).rglob("*.py")):
                violations.extend(check_file(py, forbidden, ban_dynamic))
    return violations


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Decision OS import-boundary checker (rule A).")
    ap.add_argument(
        "--policy",
        required=True,
        help="JSON policy: {rules:[{roots,forbidden,ban_dynamic_import}]}",
    )
    args = ap.parse_args(argv)
    policy = json.loads(Path(args.policy).read_text(encoding="utf-8"))
    violations = check(policy)
    for v in violations:
        print(v)
    if violations:
        print(f"\nRULE A FAILED: {len(violations)} import-boundary violation(s).")
        return 1
    print("rule A OK — no forbidden cross-layer imports.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
