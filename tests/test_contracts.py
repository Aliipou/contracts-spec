"""Contract compliance tests.

contracts-spec ships NO logic — but it must guarantee its own artifacts are
valid and internally consistent, because every other repo pins to them:

  1. every schema in schemas/ is a well-formed JSON Schema (Draft 2020-12);
  2. every example in examples/ validates against its matching schema;
  3. the frozen VERSION is valid semver;
  4. the single-decision invariant: the Decision schema's verdicts are exactly
     {ALLOW, DENY, LIMIT, DEFER} — a guard against silent vocabulary drift.

Run: python -m pytest -q   (needs `jsonschema`).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

_ROOT = Path(__file__).resolve().parent.parent
_SCHEMAS = _ROOT / "schemas"
_EXAMPLES = _ROOT / "examples"

# example file  ->  schema file
_PAIRS = {
    "action.example.json": "action.schema.json",
    "decision.example.json": "decision.schema.json",
    "capability_token.example.json": "capability_token.schema.json",
    "audit_entry.example.json": "audit_entry.schema.json",
    "event.example.json": "event.schema.json",
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("schema_file", sorted(p.name for p in _SCHEMAS.glob("*.schema.json")))
def test_schema_is_well_formed(schema_file: str) -> None:
    Draft202012Validator.check_schema(_load(_SCHEMAS / schema_file))


@pytest.mark.parametrize("example_file,schema_file", sorted(_PAIRS.items()))
def test_example_validates(example_file: str, schema_file: str) -> None:
    schema = _load(_SCHEMAS / schema_file)
    instance = _load(_EXAMPLES / example_file)
    Draft202012Validator(schema).validate(instance)


def test_every_schema_has_an_example() -> None:
    schemas = {p.name for p in _SCHEMAS.glob("*.schema.json")}
    covered = set(_PAIRS.values())
    assert schemas == covered, f"schemas without an example: {schemas - covered}"


def test_version_is_semver() -> None:
    version = (_ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert re.fullmatch(r"\d+\.\d+\.\d+", version), f"VERSION not semver: {version!r}"


def test_single_decision_vocabulary_frozen() -> None:
    # Guards the most safety-critical invariant against silent drift.
    decision = _load(_SCHEMAS / "decision.schema.json")
    assert decision["properties"]["verdict"]["enum"] == ["ALLOW", "DENY", "LIMIT", "DEFER"]
