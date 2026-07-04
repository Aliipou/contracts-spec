"""decision_os_contracts — the installable root of truth for the Decision OS.

Every other repo depends on THIS package (pinned by version); this package
depends on nothing. It bundles the JSON schemas as package data and exposes:

  * `validate(msg, name)` / `is_valid(msg, name)` — schema compliance;
  * `schema_path(name)` / `load_schema(name)` — access the raw schema;
  * `conformance` — the shared AST enforcers (rules A/B) so consumers run the
    canonical checkers instead of reinventing them;
  * `__version__` — the frozen contract version (semver). Consumers pin a major.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .conformance.validate import is_valid, validate

__version__ = "0.3.0"

_SCHEMAS = Path(__file__).resolve().parent / "schemas"


def schema_path(name: str) -> Path:
    """Filesystem path to a bundled schema, e.g. schema_path('decision')."""
    return _SCHEMAS / f"{name}.schema.json"


def load_schema(name: str) -> dict[str, Any]:
    return json.loads(schema_path(name).read_text(encoding="utf-8"))


__all__ = ["validate", "is_valid", "schema_path", "load_schema", "__version__"]
