"""Portable probes for the three candidate failure families in TAXONOMY_MAP.md.

The exploit corpus that found these families is welded to the internals of the two
codebases it was written against, so it cannot be run anywhere else — which is exactly
why the families are still labelled *candidate*. These probes are the same attacks
expressed against the `Driver` seam instead, so they can be pointed at an
implementation nobody here wrote.

A probe reports:

  BROKEN       the attack succeeded — a defect in the target
  HELD         the attack ran and the target refused it
  UNSUPPORTED  the target has no surface for this attack; nothing was measured

`UNSUPPORTED` is never reported as `HELD`, for the same reason `N/A` is never reported
as `PASS`: a probe that cannot reach a feature has learned nothing about it.

Findings against third-party software are disclosed privately to the maintainer before
they are published anywhere. Running these against software you do not operate, without
permission, is your problem and not a use this file endorses.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any


class Verdict(Enum):
    BROKEN = "BROKEN"
    HELD = "HELD"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass
class ProbeResult:
    id: str
    family: str
    title: str
    verdict: Verdict
    detail: str


def _supports(driver: Any, *caps: str) -> bool:
    have = getattr(driver, "capabilities", frozenset())
    return all(c in have for c in caps)


# ---------------------------------------------------------------------------
# Family A — verdict type confusion in the decision path
# ---------------------------------------------------------------------------


class _LyingVerdict(str):
    """Value says DENY; hash/eq impersonate ALLOW.

    The attack that broke a fixed implementation on the second attempt: this governs a
    deny-dominant fold *as a refusal* because its value ranks most-restrictive, and then
    satisfies a `verdict in PERMITTING` membership test because membership is a hash
    lookup. Serialisation writes "DENY" into the audit and the signature, so the forgery
    is self-consistent and nothing downstream can catch it.
    """

    def __new__(cls) -> _LyingVerdict:
        return super().__new__(cls, "DENY")

    def __hash__(self) -> int:  # type: ignore[override]
        return hash("ALLOW")

    def __eq__(self, other: object) -> bool:  # type: ignore[override]
        return other == "ALLOW"


def probe_a1_lying_verdict(driver: Any) -> ProbeResult:
    if not _supports(driver, "constraint_inputs"):
        return ProbeResult(
            "A1", "A", "Verdict whose value and identity disagree",
            Verdict.UNSUPPORTED, "target accepts no external constraint verdicts",
        )
    driver.reset()
    driver.grant("agent:probe", "send_email")
    out = driver.act(
        "agent:probe", "send_email", {"to": "a@b.test"},
        constraints=[lambda a: {"verdict": _LyingVerdict(), "reason": "veto"}],
    )
    if out.executed:
        return ProbeResult(
            "A1", "A", "Verdict whose value and identity disagree", Verdict.BROKEN,
            "a verdict valued DENY was honoured as permission and the effect ran",
        )
    return ProbeResult(
        "A1", "A", "Verdict whose value and identity disagree", Verdict.HELD,
        f"refused ({out.reason[:60]})",
    )


def probe_a2_dialect_drift(driver: Any) -> ProbeResult:
    """A neighbouring engine's lowercase dialect. No malice required — this is what a
    hand-rolled bridge between two policy engines produces by accident."""
    if not _supports(driver, "constraint_inputs"):
        return ProbeResult(
            "A2", "A", "Off-lattice verdict from a foreign dialect",
            Verdict.UNSUPPORTED, "target accepts no external constraint verdicts",
        )
    driver.reset()
    driver.grant("agent:probe", "send_email")
    out = driver.act(
        "agent:probe", "send_email", {"to": "a@b.test"},
        constraints=[lambda a: {"verdict": "deny", "reason": "lowercase dialect"}],
    )
    if out.executed:
        return ProbeResult(
            "A2", "A", "Off-lattice verdict from a foreign dialect", Verdict.BROKEN,
            "an unrecognised verdict string was not treated as a refusal",
        )
    return ProbeResult(
        "A2", "A", "Off-lattice verdict from a foreign dialect", Verdict.HELD,
        "unrecognised verdict refused (fail-closed)",
    )


# ---------------------------------------------------------------------------
# Family B — ceilings keyed on an attacker-authored identifier
# ---------------------------------------------------------------------------


def _call(driver: Any, actor: str, tool: str, session: str) -> bool:
    """One call, tagged with a session the caller chose. Drivers that cannot carry a
    session id raise TypeError, which the probe reports as UNSUPPORTED."""
    return driver.act(actor, tool, {"n": 1, "session_id": session}, session=session).executed


def probe_b1_rotating_session_defeats_ceilings(driver: Any, budget_calls: int = 12) -> ProbeResult:
    """The generalisation worth testing everywhere: ANY cumulative control keyed on a
    field the constrained party supplies is not a control.

    Method: establish that a fixed session eventually gets refused (so a ceiling exists
    at all), then repeat the identical calls rotating the session id. If the second run
    is never refused, the ceiling is defeated by a field the agent writes.
    """
    title = "Cumulative ceiling keyed on an agent-supplied session id"
    driver.reset()
    driver.grant("agent:probe", "send_email")

    fixed = f"s-{uuid.uuid4().hex[:8]}"
    try:
        fixed_results = [_call(driver, "agent:probe", "send_email", fixed) for _ in range(budget_calls)]
    except TypeError:
        return ProbeResult("B1", "B", title, Verdict.UNSUPPORTED,
                           "driver cannot attach a session id to a call")
    if all(fixed_results):
        return ProbeResult("B1", "B", title, Verdict.UNSUPPORTED,
                           f"no ceiling fired in {budget_calls} identical calls — "
                           "nothing to defeat, so nothing is measured")

    rotated = [
        _call(driver, "agent:probe", "send_email", f"s-{uuid.uuid4().hex[:8]}")
        for _ in range(budget_calls)
    ]
    if all(rotated):
        allowed_fixed = sum(fixed_results)
        return ProbeResult(
            "B1", "B", title, Verdict.BROKEN,
            f"fixed session refused after {allowed_fixed}/{budget_calls}; "
            f"rotating the session id allowed {len(rotated)}/{budget_calls}",
        )
    return ProbeResult("B1", "B", title, Verdict.HELD,
                       "the ceiling survived session rotation")


# ---------------------------------------------------------------------------
# Family C — audit integrity under partial failure
# ---------------------------------------------------------------------------


def probe_c1_effect_without_record(driver: Any) -> ProbeResult:
    """Did an effect happen with no audit record? The weakest observable form of the
    family, and the only one reachable without control of the target's dependencies."""
    title = "Effect performed with no audit record"
    if not _supports(driver, "audit"):
        return ProbeResult("C1", "C", title, Verdict.UNSUPPORTED,
                           "target exposes no audit records to the driver")
    driver.reset()
    driver.grant("agent:probe", "send_email")
    out = driver.act("agent:probe", "send_email", {"to": "a@b.test"})
    if out.executed and not out.records:
        return ProbeResult("C1", "C", title, Verdict.BROKEN,
                           "the tool ran and no record was produced")
    return ProbeResult("C1", "C", title, Verdict.HELD,
                       "records accompany the effect" if out.executed else "no effect to audit")


def probe_c2_refusal_records_its_reason(driver: Any) -> ProbeResult:
    """A refusal whose record does not say why is an unaccountable enforcement layer —
    and `reason` is often the only channel a veto-only component still owns."""
    title = "Refusal recorded without the reason it was refused"
    if not _supports(driver, "audit", "constraint_inputs"):
        return ProbeResult("C2", "C", title, Verdict.UNSUPPORTED,
                           "target exposes no audit records and/or no constraint inputs")
    driver.reset()
    driver.grant("agent:probe", "send_email")
    marker = f"PROBE-REASON-{uuid.uuid4().hex[:6]}"
    out = driver.act(
        "agent:probe", "send_email", {"to": "a@b.test"},
        constraints=[lambda a: {"verdict": "DENY", "reason": marker}],
    )
    if out.executed:
        return ProbeResult("C2", "C", title, Verdict.UNSUPPORTED,
                           "the refusal was not honoured, so its record cannot be judged")
    logged = " ".join(str(r.get("reason", "")) for r in out.records)
    if marker not in logged:
        return ProbeResult("C2", "C", title, Verdict.BROKEN,
                           "the vetoing reason is absent from the record")
    return ProbeResult("C2", "C", title, Verdict.HELD, "the refusal records its reason")


PROBES: list[Callable[[Any], ProbeResult]] = [
    probe_a1_lying_verdict,
    probe_a2_dialect_drift,
    probe_b1_rotating_session_defeats_ceilings,
    probe_c1_effect_without_record,
    probe_c2_refusal_records_its_reason,
]


def run_probes(driver: Any) -> list[ProbeResult]:
    results = []
    for probe in PROBES:
        try:
            results.append(probe(driver))
        except Exception as exc:  # a probe that crashes has measured nothing
            results.append(
                ProbeResult(getattr(probe, "__name__", "?"), "?", probe.__doc__ or "",
                            Verdict.UNSUPPORTED, f"probe error: {type(exc).__name__}: {exc}")
            )
    return results
