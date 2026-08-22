"""M4 — VerdictArtifact conformance profile tests."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conformance.verdict_artifact_profile import validate_verdict_artifact_dict

FIXTURE_ALLOW = {
    "artifact_version": "1.1.0",
    "decision_id": "abc123",
    "verdict": "ALLOW",
    "kernel_version": "0.4.0",
    "constitution_version": "fdk-v1.0-a1-a7",
    "accepted_inputs": [
        {
            "fact_key": "actor.kind",
            "fact_value": "MACHINE",
            "asserted_by": "proposer",
            "input_class": "TYPED_FACT",
        }
    ],
    "constitutional_basis": {"axiom_ids": []},
    "inference_trace": {"rule_ids": []},
    "epistemic_disclaimer": (
        "This artifact records constitutional behavior conditional on accepted_inputs. "
        "It does not certify that accepted inputs match world truth."
    ),
}

FIXTURE_DENY = {
    **FIXTURE_ALLOW,
    "decision_id": "deny001",
    "verdict": "DENY",
    "constitutional_basis": {"axiom_ids": ["A7"]},
    "inference_trace": {"rule_ids": ["R-A7-01"]},
}


def test_allow_fixture_passes_m4():
    assert validate_verdict_artifact_dict(FIXTURE_ALLOW) == []


def test_deny_fixture_passes_m4():
    assert validate_verdict_artifact_dict(FIXTURE_DENY) == []


def test_bad_disclaimer_fails():
    bad = {**FIXTURE_ALLOW, "epistemic_disclaimer": "we verified morality"}
    errs = validate_verdict_artifact_dict(bad)
    assert any("epistemic_disclaimer" in e for e in errs)


def test_fdk_integration_if_available():
    fdk_src = Path(__file__).resolve().parent.parent.parent / "freedom-decision-kernel" / "src"
    if not fdk_src.is_dir():
        return
    sys.path.insert(0, str(fdk_src))
    from fdk_kernel import AgentType, CandidateAction, Entity, OwnershipGraph, evaluate_legitimacy

    bot = Entity("bot", AgentType.MACHINE)
    company = Entity("co", AgentType.HUMAN)
    product = type("R", (), {"name": "product"})  # noqa — skip if model import fails
    from fdk_kernel.model import Resource

    product = Resource("product")
    graph = OwnershipGraph(
        human_owns={company: {product}},
        machine_owner={bot: company},
        delegated={bot: {product}},
    )
    art = evaluate_legitimacy(CandidateAction("x", bot, resources_used=(product,)), graph)
    doc = art.to_contract_schema()
    errs = validate_verdict_artifact_dict(doc)
    assert errs == [], f"FDK artifact failed M4: {errs}"
