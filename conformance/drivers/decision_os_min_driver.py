"""Conformance driver for `decision-os-min`.

The driver is deliberately thin: it translates the profile's vocabulary into the
implementation's API and reports honestly what the implementation does NOT support.
`capabilities` is the load-bearing part — every capability omitted here turns the
dependent requirements into N/A rather than PASS, which is the only thing that keeps
a conformance score from being self-congratulatory.

As of 2026-08-20 the reference gate claims macaroon-inspired attenuation (AE-4)
and temporal attenuation (AE-5), in addition to one-time tokens, action binding,
hash-chained audit, co-equal constraint evaluators, and revocation.
"""

from __future__ import annotations

import sys
import tempfile
import uuid
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

# decision-os-min lives beside contracts-spec in the same workspace.
_SIBLING = Path(__file__).resolve().parents[3] / "decision-os-min"
if str(_SIBLING) not in sys.path:
    sys.path.insert(0, str(_SIBLING))

from decision_os_min import DecisionOS  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from conformance.suite import Outcome  # noqa: E402


class DecisionOSMinDriver:
    name = "decision-os-min (macaroon-attenuation)"
    capabilities = frozenset(
        {
            "constraint_inputs",
            "one_time",
            "action_binding",
            "audit",
            "revocation",
            "delegation",
            "expiry",
        }
    )

    def __init__(self) -> None:
        self._dir = Path(tempfile.mkdtemp(prefix="conformance-"))
        self._gate: DecisionOS | None = None
        self.reset()

    # --- lifecycle -------------------------------------------------------
    def reset(self) -> None:
        self._audit = self._dir / f"audit-{uuid.uuid4().hex[:8]}.jsonl"
        # Persistent gate: macaroons live on the kernel; recreating would drop them.
        self._gate = DecisionOS({"grants": {}, "default": "allow"}, audit_path=str(self._audit))

    def _records(self) -> list[dict[str, Any]]:
        import json

        if not self._audit.exists():
            return []
        lines = self._audit.read_text(encoding="utf-8").splitlines()
        return [json.loads(x) for x in lines if x.strip()]

    # --- profile operations ----------------------------------------------
    def grant(self, actor: str, tool: str) -> None:
        assert self._gate is not None
        self._gate.grant(actor, f"tool:{tool}")

    def revoke(self, actor: str, tool: str) -> None:
        assert self._gate is not None
        self._gate.revoke(actor, f"tool:{tool}")

    def delegate(self, parent: str, child: str, tools: Sequence[str]) -> None:
        assert self._gate is not None
        # Default child ceiling: 1 hour (parent root grants have no expiry, so
        # this is free). AE-5 tests pass an explicit expiry via delegate_until.
        self._gate.delegate(parent, child, list(tools), expires_at=datetime.now(UTC) + timedelta(hours=1))

    def delegate_until(
        self, parent: str, child: str, tools: Sequence[str], expires_at: datetime
    ) -> None:
        """Used by AE-5; not part of the minimal Driver protocol but available."""
        assert self._gate is not None
        self._gate.delegate(parent, child, list(tools), expires_at=expires_at)

    def _tools(self, sink: list) -> dict[str, Callable[[dict[str, Any]], Any]]:
        def make(name: str) -> Callable[[dict[str, Any]], Any]:
            def run(payload: dict[str, Any]) -> str:
                sink.append((name, dict(payload)))
                return f"{name}-done"

            return run

        return {t: make(t) for t in ("send_email", "wire_money")}

    def act(
        self,
        actor: str,
        tool: str,
        payload: dict[str, Any] | None = None,
        *,
        constraints: Sequence[Callable[[dict[str, Any]], Any]] = (),
    ) -> Outcome:
        assert self._gate is not None
        sink: list = []
        before = len(self._records())
        action = {
            "actor": actor,
            "tool": tool,
            "capability": f"tool:{tool}",
            "action_purpose": "conformance",
            "payload": dict(payload or {}),
            "nonce": f"n-{uuid.uuid4().hex[:10]}",
        }
        out = self._gate.handle(action, self._tools(sink), evaluators=list(constraints) or None)
        return Outcome(
            permitted=out.verdict in ("ALLOW", "LIMIT", "CONTAIN"),
            executed=out.executed,
            effect_tool=sink[0][0] if sink else None,
            effect_payload=sink[0][1] if sink else None,
            reason=out.refused_reason or "",
            records=self._records()[before:],
        )

    def tamper_after_authorization(self, actor: str, tool: str) -> Outcome:
        """Authorize one action, then hand the executor a MUTATED action."""
        assert self._gate is not None
        sink: list = []
        gate = self._gate
        action = {
            "actor": actor,
            "tool": tool,
            "capability": f"tool:{tool}",
            "action_purpose": "conformance",
            "payload": {"amount": 1},
            "nonce": "n-tamper",
        }
        result = gate.kernel.decide(dict(action))
        tampered = {**action, "payload": {"amount": 1_000_000}}
        try:
            output = gate.executor.execute(tampered, result, self._tools(sink))
            return Outcome(
                permitted=True,
                executed=True,
                effect_tool=sink[0][0] if sink else None,
                effect_payload=sink[0][1] if sink else None,
                reason=str(output),
            )
        except Exception as exc:
            return Outcome(permitted=True, executed=False, reason=str(exc))

    def replay(self, actor: str, tool: str) -> tuple[Outcome, Outcome]:
        """Spend ONE authorization twice."""
        assert self._gate is not None
        sink: list = []
        gate = self._gate
        action = {
            "actor": actor,
            "tool": tool,
            "capability": f"tool:{tool}",
            "action_purpose": "conformance",
            "payload": {"to": "a@b.test"},
            "nonce": "n-replay",
        }
        result = gate.kernel.decide(dict(action))
        outs = []
        for _ in range(2):
            try:
                gate.executor.execute(dict(action), result, self._tools(sink))
                outs.append(Outcome(permitted=True, executed=True))
            except Exception as exc:
                outs.append(Outcome(permitted=True, executed=False, reason=str(exc)))
        return outs[0], outs[1]

    def bypass_paths(self) -> Sequence[Callable[[], Outcome]]:
        """Alternate routes to the effect that this implementation exposes."""

        def raw_executor_without_a_decision() -> Outcome:
            assert self._gate is not None
            sink: list = []
            gate = self._gate
            action = {
                "actor": "agent:x",
                "tool": "wire_money",
                "capability": "tool:wire_money",
                "action_purpose": "conformance",
                "payload": {"amount": 1},
                "nonce": "n-bypass",
            }
            forged = {
                "decision": {
                    "verdict": "ALLOW",
                    "reason": "forged",
                    "action_ref": "n-bypass",
                    "issued_by": "decision-os-min-kernel",
                    "token_id": "tok-forged",
                    "capability": "tool:wire_money",
                    "token_expires_at": "2099-01-01T00:00:00+00:00",
                },
                "signature": "00" * 64,
            }
            try:
                gate.executor.execute(action, forged, self._tools(sink))
                return Outcome(
                    permitted=False,
                    executed=True,
                    effect_tool=sink[0][0] if sink else None,
                )
            except Exception as exc:
                return Outcome(permitted=False, executed=False, reason=str(exc))

        return [raw_executor_without_a_decision]
