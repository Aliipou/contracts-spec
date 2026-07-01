"""Rule C — schema-compliance helper.

Validate a message against a bundled contracts-spec schema by name. Consumer
repos call this at their boundaries and in tests so no ad-hoc message shape ever
crosses a repo edge.
"""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path

from jsonschema import Draft202012Validator

_SCHEMAS = Path(__file__).resolve().parent.parent / "schemas"


@cache
def _validator(name: str) -> Draft202012Validator:
    schema = json.loads((_SCHEMAS / f"{name}.schema.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def is_valid(message: dict, schema_name: str) -> bool:
    """True iff `message` conforms to the named schema (e.g. 'decision')."""
    return _validator(schema_name).is_valid(message)


def validate(message: dict, schema_name: str) -> None:
    """Raise jsonschema.ValidationError if `message` does not conform."""
    _validator(schema_name).validate(message)
