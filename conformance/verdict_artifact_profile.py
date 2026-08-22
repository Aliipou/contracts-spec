"""M4 — VerdictArtifact structural conformance (no runtime dependency on FDK)."""
from __future__ import annotations

from typing import Any

EPISTEMIC_DISCLAIMER = (
    "This artifact records constitutional behavior conditional on accepted_inputs. "
    "It does not certify that accepted inputs match world truth."
)

REQUIRED_TOP = frozenset({
    "artifact_version",
    "decision_id",
    "verdict",
    "kernel_version",
    "constitution_version",
    "accepted_inputs",
    "constitutional_basis",
    "inference_trace",
    "epistemic_disclaimer",
})


def validate_verdict_artifact_dict(doc: dict[str, Any]) -> list[str]:
    """Return list of violations (empty = pass). Schema-level M4 checks."""
    errors: list[str] = []

    missing = REQUIRED_TOP - set(doc)
    if missing:
        errors.append(f"missing required fields: {sorted(missing)}")

    if doc.get("epistemic_disclaimer") != EPISTEMIC_DISCLAIMER:
        errors.append("epistemic_disclaimer must be the canonical fixed text")

    for i, inp in enumerate(doc.get("accepted_inputs", [])):
        if not inp.get("asserted_by"):
            errors.append(f"accepted_inputs[{i}].asserted_by required")
        if inp.get("provenance_ref") and inp.get("input_class") == "CALLER_FLAG":
            errors.append(
                f"accepted_inputs[{i}]: provenance_ref on CALLER_FLAG implies M3+ — not M2"
            )

    basis = doc.get("constitutional_basis", {})
    trace = doc.get("inference_trace", {})
    rule_ids = trace.get("rule_ids", [])
    axiom_ids = basis.get("axiom_ids", [])
    if doc.get("verdict") != "ALLOW" and not rule_ids:
        errors.append("non-ALLOW verdict requires inference_trace.rule_ids")

    if doc.get("verdict") == "ALLOW" and (rule_ids or axiom_ids):
        errors.append("ALLOW verdict should have empty constitutional basis")

    return errors
