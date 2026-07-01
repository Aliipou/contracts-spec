"""Formal tests for the conformance enforcers (rules A, B, C).

The emphasis is adversarial: the import boundary and the single-authority
constraint must catch the OBVIOUS evasions (aliased/dotted/dynamic imports;
hand-built decision dicts), and must NOT fire on legitimate reads.
"""

from __future__ import annotations

from pathlib import Path

from conformance import check_authority, check_imports, validate


def _write(root: Path, rel: str, src: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(src, encoding="utf-8")


# ----------------------------- rule A ---------------------------------------- #
def _policy(core: Path) -> dict:
    return {"rules": [{"roots": [str(core)], "forbidden": ["research", "fdk_research"], "ban_dynamic_import": True}]}


def test_rule_a_catches_plain_and_aliased_and_dotted_imports(tmp_path: Path) -> None:
    core = tmp_path / "core"
    _write(core, "a.py", "import research\n")
    _write(core, "b.py", "import research as r\n")
    _write(core, "c.py", "import research.deep.mod\n")
    _write(core, "d.py", "from research.sub import thing\n")
    v = check_imports.check(_policy(core))
    assert len(v) == 4, v  # every form of the forbidden import is caught


def test_rule_a_bans_dynamic_import_escape_hatches(tmp_path: Path) -> None:
    core = tmp_path / "core"
    _write(core, "dyn.py", "import importlib\nimportlib.import_module('research')\n")
    _write(core, "dun.py", "__import__('research')\n")
    v = check_imports.check(_policy(core))
    assert len(v) == 2, v  # dynamic-import smuggling routes are refused


def test_rule_a_passes_clean_core(tmp_path: Path) -> None:
    core = tmp_path / "core"
    _write(core, "ok.py", "import json\nfrom contracts_spec import schemas  # allowed\n")
    assert check_imports.check(_policy(core)) == []


# ----------------------------- rule B ---------------------------------------- #
def test_rule_b_catches_decision_construction_and_dict(tmp_path: Path) -> None:
    src = tmp_path / "research"
    _write(src, "bad1.py", "def f():\n    return Decision(verdict='DENY', reason='x', action_ref='a', issued_by='me')\n")
    _write(src, "bad2.py", "d = {'verdict': 'CONTAIN', 'reason': 'x'}\n")
    v = check_authority.check([str(src)])
    assert len(v) == 2, v  # both emission forms flagged in a non-kernel tree


def test_rule_b_allows_reading_a_verdict(tmp_path: Path) -> None:
    src = tmp_path / "control_plane"
    _write(src, "ok.py", "def route(decision):\n    if decision.verdict == 'DENY':\n        return 'stop'\n    return 'go'\n")
    assert check_authority.check([str(src)]) == []  # reading is fine, only emitting is banned


# ----------------------------- rule C ---------------------------------------- #
def test_rule_c_accepts_valid_and_rejects_invalid_decision() -> None:
    good = {"verdict": "ALLOW", "reason": "ok", "action_ref": "n-1", "issued_by": "decision-kernel-core"}
    assert validate.is_valid(good, "decision")
    # CONTAIN without its required containment block must be rejected.
    bad = {"verdict": "CONTAIN", "reason": "x", "action_ref": "n-1", "issued_by": "decision-kernel-core"}
    assert not validate.is_valid(bad, "decision")
