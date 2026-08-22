"""Windows-safe pytest bootstrap (see decision-os-min/conftest.py)."""
from __future__ import annotations

import os
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_ENV_TMP = _ROOT / ".pytest-tmp" / "env"
_BASETEMP = _ROOT / ".pytest-basetemp"

_ENV_TMP.mkdir(parents=True, exist_ok=True)
_BASETEMP.mkdir(parents=True, exist_ok=True)
os.environ["TMP"] = str(_ENV_TMP)
os.environ["TEMP"] = str(_ENV_TMP)


def pytest_configure(config) -> None:
    if config.option.basetemp is None:
        config.option.basetemp = str(_BASETEMP)
