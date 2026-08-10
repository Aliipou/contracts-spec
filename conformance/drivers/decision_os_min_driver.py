"""Conformance driver for `decision-os-min`.

The driver is deliberately thin: it translates the profile's vocabulary into the
implementation's API and reports honestly what the implementation does NOT support.
`capabilities` is the load-bearing part — every capability omitted here turns the
dependent requirements into N/A rather than PASS, which is the only thing that keeps
a conformance score from being self-congratulatory.

`decision-os-min` has no delegation graph and no expiry hierarchy, so AE-4 and AE-5
are genuinely out of its scope. It DOES have one-time tokens, action binding, a
hash-chained audit, and co-equal constraint evaluators.
"""

from __future__ import annotations

import sys
import tempfile
import uuid
from collections.abc import Callable, Sequence
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
    name = "decision-os-min (feat/co-equal-evaluator-composition)"
    capabilities = frozenset(
        {"constraint_inputs", "one_time", "action_binding", "audit", "revocation"}
    )

    def __init__(self) -> None:
        self._grants: dict[str, list[str]] = {}
        self._dir = Path(tempfile.mkdtemp(prefix="conformance-"))
        self.reset()

    # --- lifecycle -------------------------------------------------------
    def reset(self) -> None:
        self._grants = {}
        self._audit = self._dir / f"audit-{uuid.uuid4().hex[:8]}.jsonl"

    def _gate(self) -> DecisionOS:
        return DecisionOS({"grants": dict(self._grants), "default": "allow"},
                          audit_path=str(self._audit))

    def _records(self) -> list[dict[str, Any]]:
        import json

        if not self._audit.exists():
            return []
        return [json.loads(x) for x in self._audit.read_text(encoding="utf-8").splitlines() if x.strip()]

    # --- profile operations ----------------------------------------------
    def grant(self, actor: str, tool: str) -> None:
        self._grants.setdefault(actor, []).append(f"tool:{tool}")

    def revoke(self, actor: str, tool: str) -> None:
        self._grants[actor] = [c for c in self._grants.get(actor, []) if c != f"tool:{tool}"]

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
        out = self._gate().handle(action, self._tools(sink), evaluators=list(constraints) or None)
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
        sink: list = []
        gate = self._gate()
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
            return Outcome(permitted=True, executed=True, effect_tool=sink[0][0] if sink else None,
                           effect_payload=sink[0][1] if sink else None, reason=str(output))
        except Exception as exc:
            return Outcome(permitted=True, executed=False, reason=str(exc))

    def replay(self, actor: str, tool: str) -> tuple[Outcome, Outcome]:
        """Spend ONE authorization twice."""
        sink: list = []
        gate = self._gate()
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
            sink: list = []
            gate = self._gate()
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
                return Outcome(permitted=False, executed=True,
                               effect_tool=sink[0][0] if sink else None)
            except Exception as exc:
                return Outcome(permitted=False, executed=False, reason=str(exc))

        return [raw_executor_without_a_decision]
