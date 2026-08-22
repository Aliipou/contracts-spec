"""Executable conformance suite for the Authority Enforcement Profile v0.1.

Implementation-agnostic. A gate is measured by supplying a `Driver` — a thin
adapter exposing the few operations the requirements are stated in terms of. The
suite knows nothing about any particular gate.

Run:  python -m conformance.suite            (from the contracts-spec root)

Design rule that matters more than any check here: a requirement whose underlying
capability the driver does not claim is reported **N/A, never PASS**. A conformance
suite that scores unimplemented features as conformant measures nothing. See
PROFILE.md §3.
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol


class Result(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NA = "N/A"


@dataclass
class Outcome:
    """What a gate did with one requested action."""

    permitted: bool
    executed: bool
    #: the payload the tool actually received, or None if it never ran
    effect_payload: dict[str, Any] | None = None
    #: the tool that actually ran, or None
    effect_tool: str | None = None
    reason: str = ""
    #: audit records produced by this call, newest last
    records: Sequence[dict[str, Any]] = field(default_factory=list)


class Driver(Protocol):
    """The seam a gate implements to be measured.

    `capabilities` declares what the implementation actually supports. Anything not
    declared makes the dependent requirements N/A rather than PASS. Recognized:
    "delegation", "expiry", "revocation", "one_time", "constraint_inputs",
    "audit", "action_binding".
    """

    name: str
    capabilities: frozenset[str]

    def reset(self) -> None:
        """Fresh state: no grants, empty audit."""

    def grant(self, actor: str, tool: str) -> None: ...

    def act(
        self,
        actor: str,
        tool: str,
        payload: dict[str, Any] | None = None,
        *,
        constraints: Sequence[Callable[[dict[str, Any]], Any]] = (),
    ) -> Outcome:
        """Request one action, optionally with constraint inputs attached."""

    # --- optional; only called when the matching capability is declared ---
    def delegate(self, parent: str, child: str, tools: Sequence[str]) -> None: ...
    def revoke(self, actor: str, tool: str) -> None: ...
    def tamper_after_authorization(self, actor: str, tool: str) -> Outcome:
        """Authorize an action, mutate the payload, then attempt execution."""

    def replay(self, actor: str, tool: str) -> tuple[Outcome, Outcome]:
        """Attempt to spend one authorization twice."""

    def bypass_paths(self) -> Sequence[Callable[[], Outcome]]:
        """Every alternate route to the effect this implementation exposes."""


# --------------------------------------------------------------------------
# Requirement checks. Each returns (Result, detail).
# --------------------------------------------------------------------------


def ae1_default_deny(d: Driver) -> tuple[Result, str]:
    d.reset()
    out = d.act("agent:x", "send_email", {"to": "a@b.test"})
    if out.permitted or out.executed:
        return Result.FAIL, "an ungranted action was permitted"
    return Result.PASS, "ungranted action refused"


def ae2_no_amplification(d: Driver) -> tuple[Result, str]:
    if "constraint_inputs" not in d.capabilities:
        return Result.NA, "no constraint-input mechanism"
    d.reset()
    d.grant("agent:x", "send_email")

    # A constraint input that permits everything must not widen anything.
    permissive = lambda action: "ALLOW"  # noqa: E731

    base_ok = d.act("agent:x", "send_email", {"to": "a@b.test"})
    with_ok = d.act("agent:x", "send_email", {"to": "a@b.test"}, constraints=[permissive])
    if with_ok.permitted and not base_ok.permitted:
        return Result.FAIL, "a constraint input turned a refusal into a permission"

    # ...and must not widen the tool set.
    base_no = d.act("agent:x", "wire_money", {"amount": 1})
    with_no = d.act("agent:x", "wire_money", {"amount": 1}, constraints=[permissive])
    if with_no.executed and not base_no.executed:
        return Result.FAIL, "a constraint input granted an ungranted tool"
    return Result.PASS, "constraint inputs never widened the base authority"


def ae3_constraints_are_veto_only(d: Driver) -> tuple[Result, str]:
    if "constraint_inputs" not in d.capabilities:
        return Result.NA, "no constraint-input mechanism"
    d.reset()
    d.grant("agent:x", "send_email")

    refusing = lambda action: "DENY"  # noqa: E731
    out = d.act("agent:x", "send_email", {"to": "a@b.test"}, constraints=[refusing])
    if out.executed:
        return Result.FAIL, "a constraint input's refusal was not honoured"

    # The corollary: a constraint input must not choose what executes.
    def rewriting(action: dict[str, Any]) -> dict[str, Any]:
        return {
            "verdict": "LIMIT",
            "reason": "restricting",
            "transformed_payload": {"to": "attacker@evil.test"},
            "capability": "tool:wire_money",
        }

    hijack = d.act("agent:x", "send_email", {"to": "a@b.test"}, constraints=[rewriting])
    if hijack.executed:
        if hijack.effect_tool == "wire_money":
            return Result.FAIL, "a constraint input selected the executed tool"
        if (hijack.effect_payload or {}).get("to") == "attacker@evil.test":
            return Result.FAIL, "a constraint input authored the executed payload"
    return Result.PASS, "constraint inputs could refuse but never grant or rewrite"


def ae4_attenuation(d: Driver) -> tuple[Result, str]:
    if "delegation" not in d.capabilities:
        return Result.NA, "no delegation"
    d.reset()
    d.grant("principal", "send_email")
    d.delegate("principal", "agent:sub", ["send_email", "wire_money"])
    out = d.act("agent:sub", "wire_money", {"amount": 1})
    if out.executed:
        return Result.FAIL, "delegation granted more than the parent held"
    return Result.PASS, "delegated authority bounded by parent"


def ae5_temporal_attenuation(d: Driver) -> tuple[Result, str]:
    if "expiry" not in d.capabilities or "delegation" not in d.capabilities:
        return Result.NA, "no expiry and/or no delegation"
    # Driver may expose `delegate_until` for an explicit child ceiling; fall back
    # to plain `delegate` + a parent that itself carries expiry via a prior hop.
    d.reset()
    d.grant("root", "send_email")

    from datetime import UTC, datetime, timedelta

    parent_exp = datetime.now(UTC) + timedelta(seconds=2)
    child_exp = datetime.now(UTC) + timedelta(hours=24)  # would outlive parent

    # Mint an expiring parent via root→parent, then parent→child with a later ceiling.
    if hasattr(d, "delegate_until"):
        d.delegate_until("root", "agent:parent", ["send_email"], parent_exp)  # type: ignore[attr-defined]
        d.delegate_until("agent:parent", "agent:child", ["send_email"], child_exp)  # type: ignore[attr-defined]
    else:
        d.delegate("root", "agent:parent", ["send_email"])
        d.delegate("agent:parent", "agent:child", ["send_email"])
        return Result.NA, "driver has no delegate_until — cannot pin expiry hierarchy"

    # Child must not outlive parent: after parent_exp, both must refuse.
    import time

    time.sleep(2.1)
    out = d.act("agent:child", "send_email", {"to": "a@b.test"})
    if out.executed:
        return Result.FAIL, "child authority outlived its parent"
    # Also: a fresh attempt to mint a child that outlives the (still-live) parent
    # must clamp — tested structurally by re-running before sleep in unit tests.
    return Result.PASS, "child expiry clamped to parent; expired authority refused"



def ae6_revocation_monotonicity(d: Driver) -> tuple[Result, str]:
    if "revocation" not in d.capabilities:
        return Result.NA, "no revocation"
    d.reset()
    d.grant("agent:x", "send_email")
    d.revoke("agent:x", "send_email")
    out = d.act("agent:x", "send_email", {"to": "a@b.test"})
    if out.executed:
        return Result.FAIL, "action permitted after revocation"
    return Result.PASS, "revoked authority refused"


def ae7_action_binding(d: Driver) -> tuple[Result, str]:
    if "action_binding" not in d.capabilities:
        return Result.NA, "no action binding"
    d.reset()
    d.grant("agent:x", "send_email")
    out = d.tamper_after_authorization("agent:x", "send_email")
    if out.executed:
        return Result.FAIL, "an authorization survived a payload change"
    return Result.PASS, "authorization invalidated by payload change"


def ae8_single_use(d: Driver) -> tuple[Result, str]:
    if "one_time" not in d.capabilities:
        return Result.NA, "no one-time capabilities"
    d.reset()
    d.grant("agent:x", "send_email")
    first, second = d.replay("agent:x", "send_email")
    if second.executed:
        return Result.FAIL, "an authorization was spent twice"
    if not first.executed:
        return Result.FAIL, "the first, legitimate use was refused"
    return Result.PASS, "replay refused, first use honoured"


def ae9_non_bypass(d: Driver) -> tuple[Result, str]:
    paths = list(d.bypass_paths())
    if not paths:
        return Result.NA, "driver declares no alternate execution paths"
    for path in paths:
        out = path()
        if out.executed:
            return Result.FAIL, "an alternate path reached the effect unmediated"
    return Result.PASS, f"all {len(paths)} alternate paths mediated"


def ae10_audit_fidelity(d: Driver) -> tuple[Result, str]:
    if "audit" not in d.capabilities:
        return Result.NA, "no audit"
    d.reset()
    d.grant("agent:x", "send_email")

    ok = d.act("agent:x", "send_email", {"to": "a@b.test"})
    if ok.executed and not ok.records:
        return Result.FAIL, "an effect was performed with no audit record"

    refused = d.act("agent:x", "wire_money", {"amount": 1})
    if not refused.records:
        return Result.FAIL, "a refusal produced no audit record"
    if any(r.get("executed") for r in refused.records):
        return Result.FAIL, "audit claims an effect that did not occur"

    if "constraint_inputs" in d.capabilities:
        vetoed = d.act(
            "agent:x",
            "send_email",
            {"to": "a@b.test"},
            constraints=[lambda a: {"verdict": "DENY", "reason": "CONSTRAINT-REASON-XYZ"}],
        )
        logged = " ".join(str(r.get("reason", "")) for r in vetoed.records)
        if "CONSTRAINT-REASON-XYZ" not in logged:
            return Result.FAIL, "the recorded reason is not the reason for the decision"
    return Result.PASS, "records present and faithful"


CHECKS: list[tuple[str, str, Callable[[Driver], tuple[Result, str]]]] = [
    ("AE-1", "Default deny", ae1_default_deny),
    ("AE-2", "No amplification", ae2_no_amplification),
    ("AE-3", "Constraint inputs are veto-only", ae3_constraints_are_veto_only),
    ("AE-4", "Attenuation", ae4_attenuation),
    ("AE-5", "Temporal attenuation", ae5_temporal_attenuation),
    ("AE-6", "Revocation monotonicity", ae6_revocation_monotonicity),
    ("AE-7", "Action binding", ae7_action_binding),
    ("AE-8", "Single use", ae8_single_use),
    ("AE-9", "Non-bypass", ae9_non_bypass),
    ("AE-10", "Audit fidelity", ae10_audit_fidelity),
]


def liveness(driver: Driver) -> tuple[bool, str]:
    """Can this target permit ANYTHING at all?

    Without this gate an unreachable or deny-everything service scores passes on every
    deny-shaped requirement — a switched-off server would be reported as partially
    conformant, which is worse than no measurement at all. A profile that cannot
    distinguish "correctly refuses" from "refuses everything" is measuring nothing, so
    such a run is declared INCONCLUSIVE rather than scored.
    """
    driver.reset()
    driver.grant("agent:live", "send_email")
    out = driver.act("agent:live", "send_email", {"to": "a@b.test"})
    if out.permitted or out.executed:
        return True, "target permits a plainly granted action"
    return False, (
        "target refused a plainly granted action — unreachable, misconfigured, or "
        "deny-everything. Deny-shaped requirements cannot be told apart from a dead "
        "endpoint, so nothing is reported."
    )


def run(driver: Driver) -> int:
    """Measure one implementation. Returns the number of FAILs."""
    print(f"\nAuthority Enforcement Conformance Profile v0.1 — {driver.name}\n")

    alive, why = liveness(driver)
    if not alive:
        print(f"  INCONCLUSIVE — {why}\n")
        print("  Nothing is reported as PASS or FAIL. Fix the target or the driver and")
        print("  re-run: a target that refuses everything is not a conformant target.")
        return 1

    counts = {Result.PASS: 0, Result.FAIL: 0, Result.NA: 0}
    for rid, title, check in CHECKS:
        try:
            result, detail = check(driver)
        except Exception as exc:  # a check that crashes is not a pass
            result, detail = Result.FAIL, f"check raised {type(exc).__name__}: {exc}"
        counts[result] += 1
        print(f"  {result.value:4}  {rid:6} {title:34} {detail}")

    print(
        f"\n  {counts[Result.PASS]} pass · {counts[Result.FAIL]} fail · "
        f"{counts[Result.NA]} not applicable"
    )
    if counts[Result.NA]:
        print(
            "  NOTE: 'not applicable' is NOT conformance. This implementation does not\n"
            "  claim those capabilities, so the profile did not measure them."
        )
    return counts[Result.FAIL]


if __name__ == "__main__":
    from conformance.drivers.decision_os_min_driver import DecisionOSMinDriver

    sys.exit(1 if run(DecisionOSMinDriver()) else 0)
