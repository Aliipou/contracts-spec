"""A driver for any authorization service reachable over HTTP.

This is the driver that makes the profile a product rather than a demo: it can be
pointed at software its author did not write — an MCP gateway, a policy sidecar, an
OPA/Cedar decision endpoint behind a thin shim — provided that service can answer a
single question:

    POST {endpoint}
    {"actor", "capability", "resource", "payload", "purpose", "labels", "nonce"}
    -> {"allow": bool, ...}   (or {"decision": "ALLOW"|"DENY"} / {"result": "permit"})

Anything richer is optional. Where the target cannot express a capability at all, the
driver declines to claim it, and the dependent requirements report **N/A rather than
PASS** — which is the rule the whole profile rests on.

Honest scope: a decision endpoint tells you what a system *says*. It cannot tell you
whether the effect was actually mediated, whether an audit record was written, or
whether a token was spent twice. Those requirements are therefore N/A here unless the
target exposes the corresponding endpoints. A conformance run over HTTP is a floor,
not a full audit — and reporting it as anything more would be the exact dishonesty
this profile exists to prevent.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
import uuid
from collections.abc import Callable, Sequence
from typing import Any

from ..suite import Outcome

# Response shapes seen in the wild. Checked in order; first match wins.
_ALLOW_KEYS = ("allow", "allowed", "permit", "permitted")
_VERDICT_KEYS = ("decision", "verdict", "result", "effect")
_PERMIT_WORDS = {"allow", "allowed", "permit", "permitted", "true", "yes", "ok"}


class HttpDriver:
    """Measure a remote authorization service.

    `capabilities` is intentionally minimal. A remote decision endpoint demonstrably
    supports default-deny and constraint composition only if it accepts constraint
    inputs; it says nothing about one-time tokens, action binding, or audit, so those
    are not claimed and their requirements come back N/A. Override `capabilities` when
    you know the target really does support more, and be prepared to justify it.
    """

    def __init__(
        self,
        endpoint: str | None = None,
        token: str | None = None,
        timeout: float = 10.0,
        capabilities: Sequence[str] = ("constraint_inputs",),
    ) -> None:
        if not endpoint:
            raise SystemExit("HttpDriver needs --endpoint")
        self.endpoint = endpoint
        self.name = f"http:{endpoint}"
        self._token = token
        self._timeout = timeout
        self.capabilities = frozenset(capabilities)
        self._grants: dict[str, list[str]] = {}

    # --- lifecycle -------------------------------------------------------
    def reset(self) -> None:
        self._grants = {}

    def grant(self, actor: str, tool: str) -> None:
        """Recorded locally and sent with each request. A remote service that manages
        its own grants will ignore this; one that accepts them in context will use it.
        Either way the profile's default-deny check remains meaningful, because the
        ungranted case sends no grant at all."""
        self._grants.setdefault(actor, []).append(f"tool:{tool}")

    def revoke(self, actor: str, tool: str) -> None:
        self._grants[actor] = [c for c in self._grants.get(actor, []) if c != f"tool:{tool}"]

    # --- the one call ----------------------------------------------------
    def _post(self, body: dict[str, Any]) -> tuple[bool, str]:
        data = json.dumps(body).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        req = urllib.request.Request(self.endpoint, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as r:
                payload = json.loads(r.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as e:
            # 403/401 is a refusal, which is a legitimate answer, not a driver failure.
            if e.code in (401, 403):
                return False, f"HTTP {e.code}"
            return False, f"HTTP {e.code} (treated as refusal, fail-closed)"
        except Exception as exc:
            # An unreachable authorizer must never read as ALLOW.
            return False, f"{type(exc).__name__}: {exc} (fail-closed)"
        return self._interpret(payload)

    @staticmethod
    def _interpret(payload: Any) -> tuple[bool, str]:
        """Map a response onto allow/deny without ever guessing 'allow'."""
        if isinstance(payload, bool):
            return payload, str(payload)
        if not isinstance(payload, dict):
            return False, f"unrecognized response type {type(payload).__name__} (fail-closed)"
        for k in _ALLOW_KEYS:
            if isinstance(payload.get(k), bool):
                return payload[k], f"{k}={payload[k]}"
        for k in _VERDICT_KEYS:
            v = payload.get(k)
            if isinstance(v, str):
                return v.strip().lower() in _PERMIT_WORDS, f"{k}={v}"
        return False, f"no verdict field found in {sorted(payload)[:6]} (fail-closed)"

    def act(
        self,
        actor: str,
        tool: str,
        payload: dict[str, Any] | None = None,
        *,
        constraints: Sequence[Callable[[dict[str, Any]], Any]] = (),
    ) -> Outcome:
        action = {
            "actor": actor,
            "tool": tool,
            "capability": f"tool:{tool}",
            "resource": tool,
            "purpose": "conformance",
            "payload": dict(payload or {}),
            "labels": [],
            "nonce": f"n-{uuid.uuid4().hex[:10]}",
            "grants": {a: list(c) for a, c in self._grants.items()},
        }
        # Constraint inputs are evaluated locally and sent as advisory verdicts. A
        # target that ignores them will fail AE-3, which is the correct outcome: an
        # implementation that cannot be vetoed does not satisfy veto composition.
        verdicts = []
        for c in constraints:
            try:
                out = c(dict(action))
            except Exception as exc:
                out = {"verdict": "DENY", "reason": f"constraint error: {exc}"}
            verdicts.append(out if isinstance(out, dict) else {"verdict": str(out)})
        if verdicts:
            action["constraints"] = verdicts

        allowed, detail = self._post(action)

        # Deny-dominance is a property of the SYSTEM. If the target ignores a refusing
        # constraint, we report what the target did — we do not silently apply the
        # veto ourselves and award a pass the implementation did not earn.
        return Outcome(
            permitted=allowed,
            executed=allowed,
            effect_tool=tool if allowed else None,
            effect_payload=dict(payload or {}) if allowed else None,
            reason=detail,
            records=[],
        )

    # --- capabilities this driver cannot honestly claim ------------------
    def bypass_paths(self) -> Sequence[Callable[[], Outcome]]:
        """None observable over a decision endpoint. AE-9 asks whether an effect can be
        reached without passing the enforcement boundary; that is a question about the
        target's architecture, not about its API, so it reports N/A rather than a pass
        this driver has no evidence for."""
        return []
