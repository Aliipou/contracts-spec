#!/usr/bin/env python3
"""Rigorous deployment testimony — run all gates and optional live HTTP probe.

Usage:
  python scripts/rigorous_testimony.py
  python scripts/rigorous_testimony.py --live-service

Exits 0 only if every gate passes.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = Path(os.environ.get("TESTIMONY_WORKSPACE", ROOT.parent))


@dataclass
class Gate:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class Report:
    gates: list[Gate] = field(default_factory=list)

    def add(self, name: str, passed: bool, detail: str = "") -> None:
        self.gates.append(Gate(name, passed, detail))

    @property
    def ok(self) -> bool:
        return all(g.passed for g in self.gates)

    def to_dict(self) -> dict:
        return {
            "verdict": "DEPLOYABLE" if self.ok else "NOT_DEPLOYABLE",
            "passed": sum(g.passed for g in self.gates),
            "total": len(self.gates),
            "gates": [
                {"name": g.name, "passed": g.passed, "detail": g.detail}
                for g in self.gates
            ],
        }

    def print_summary(self) -> None:
        print("\n" + "=" * 60)
        print("RIGOROUS DEPLOYMENT TESTIMONY")
        print("=" * 60)
        for g in self.gates:
            mark = "PASS" if g.passed else "FAIL"
            line = f"  [{mark}] {g.name}"
            if g.detail:
                line += f" - {g.detail}"
            print(line)
        print("-" * 60)
        print(f"  TOTAL: {sum(g.passed for g in self.gates)}/{len(self.gates)} gates")
        print("  VERDICT:", "DEPLOYABLE (evidence pass)" if self.ok else "NOT DEPLOYABLE")
        print("=" * 60)


def _run(cmd: list[str], cwd: Path, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )


def gate_pytest(report: Report, name: str, cwd: Path, paths: list[str]) -> None:
    r = _run([sys.executable, "-m", "pytest", *paths, "-q", "--tb=line"], cwd)
    tail = (r.stdout + r.stderr).strip().splitlines()[-1] if r.stdout or r.stderr else ""
    report.add(name, r.returncode == 0, tail or f"exit {r.returncode}")


def gate_conformance_suite(report: Report) -> None:
    r = _run([sys.executable, "-m", "conformance.suite"], ROOT)
    out = r.stdout + r.stderr
    passed = r.returncode == 0 and "0 fail" in out
    detail = "10/10 AE" if passed else out.strip().splitlines()[-3:]
    report.add("AE-1..AE-10 conformance suite", passed, str(detail)[:120])


def gate_m4(report: Report) -> None:
    r = _run([sys.executable, "-m", "pytest", "tests/test_verdict_artifact_m4.py", "-q"], ROOT)
    report.add("M4 verdict artifact profile", r.returncode == 0, (r.stdout or "").strip()[-40:])


def gate_fdk_m4_integration(report: Report) -> None:
    fdk_src = WORKSPACE / "freedom-decision-kernel" / "src"
    if not fdk_src.is_dir():
        report.add("FDK -> M4 integration", False, "freedom-decision-kernel not found")
        return
    sys.path.insert(0, str(fdk_src))
    try:
        from conformance.verdict_artifact_profile import validate_verdict_artifact_dict
        from fdk_kernel import AgentType, CandidateAction, Entity, OwnershipGraph, evaluate_legitimacy
        from fdk_kernel.model import Resource

        bot = Entity("bot", AgentType.MACHINE)
        co = Entity("co", AgentType.HUMAN)
        product = Resource("product")
        graph = OwnershipGraph(
            human_owns={co: {product}},
            machine_owner={bot: co},
            delegated={bot: {product}},
        )
        art = evaluate_legitimacy(CandidateAction("t", bot, resources_used=(product,)), graph)
        errs = validate_verdict_artifact_dict(art.to_contract_schema())
        report.add("FDK -> M4 integration", errs == [], "no errors" if not errs else "; ".join(errs))
    except Exception as exc:
        report.add("FDK -> M4 integration", False, str(exc))


def gate_live_service(report: Report, port: int = 18080) -> None:
    dos_root = WORKSPACE / "decision-os-min"
    if not dos_root.is_dir():
        report.add("Live HTTP service", False, "decision-os-min not found")
        return

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        policy = dos_root / "deploy" / "policy.json"
        env = os.environ.copy()
        env.update({
            "PORT": str(port),
            "DECISION_OS_POLICY": str(policy),
            "DECISION_OS_AUDIT": str(tmp_path / "audit.jsonl"),
            "DECISION_OS_KEY_FILE": str(tmp_path / "key.pem"),
            "DECISION_OS_EVALUATOR_TIMEOUT_S": "1.0",
            "PYTHONPATH": str(dos_root),
        })

        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "decision_os_min.service:app", "--host", "127.0.0.1", "--port", str(port)],
            cwd=dos_root,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )

        def _wait_ready() -> bool:
            url = f"http://127.0.0.1:{port}/readyz"
            for _ in range(40):
                try:
                    with urllib.request.urlopen(url, timeout=1) as resp:
                        if resp.status == 200:
                            return True
                except (urllib.error.URLError, TimeoutError):
                    time.sleep(0.25)
            return False

        try:
            if not _wait_ready():
                err = proc.stderr.read() if proc.stderr else ""
                report.add("Live HTTP /readyz", False, err[:200] or "timeout")
                return
            report.add("Live HTTP /readyz", True, f"port {port}")

            # ALLOW path
            body = json.dumps({
                "actor": "agent:bot",
                "tool": "send_email",
                "capability": "tool:send_email",
                "action_purpose": "support_reply",
                "data_labels": ["customer_support"],
                "payload": {"to": "a@b.test"},
                "nonce": "testimony-allow-1",
            }).encode()
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/v1/decide",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
            ok = data.get("decision", {}).get("verdict") == "ALLOW" and bool(data.get("signature"))
            report.add("Live HTTP /v1/decide ALLOW", ok, data.get("decision", {}).get("verdict", "?"))

            # DENY path — wrong purpose
            body_deny = json.dumps({
                "actor": "agent:bot",
                "tool": "send_email",
                "capability": "tool:send_email",
                "action_purpose": "marketing",
                "data_labels": ["customer_support"],
                "payload": {"to": "a@b.test"},
                "nonce": "testimony-deny-1",
            }).encode()
            req2 = urllib.request.Request(
                f"http://127.0.0.1:{port}/v1/decide",
                data=body_deny,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req2, timeout=5) as resp:
                data2 = json.loads(resp.read())
            deny_ok = data2.get("decision", {}).get("verdict") == "DENY"
            report.add("Live HTTP /v1/decide DENY", deny_ok, data2.get("decision", {}).get("verdict", "?"))

            audit_path = tmp_path / "audit.jsonl"
            audit_ok = audit_path.exists() and audit_path.stat().st_size > 0
            report.add("Audit chain written", audit_ok, f"{audit_path.stat().st_size} bytes" if audit_ok else "empty")

        except Exception as exc:
            report.add("Live HTTP probes", False, str(exc))
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live-service", action="store_true", help="start uvicorn and probe HTTP")
    parser.add_argument("--skip-slow", action="store_true", help="skip lean/tla refinement tests")
    parser.add_argument("--json", dest="json_out", metavar="PATH", help="write machine-readable report")
    args = parser.parse_args()

    report = Report()

    # contracts-spec
    gate_m4(report)
    gate_conformance_suite(report)
    gate_fdk_m4_integration(report)

    # FDK
    fdk = WORKSPACE / "freedom-decision-kernel"
    if fdk.is_dir():
        tests = [
            "tests/test_verdict_artifact_m1.py",
            "tests/test_verdict_artifact_m2.py",
            "tests/test_kernel.py",
            "tests/test_primitive_freeze.py",
        ]
        if not args.skip_slow:
            tests += ["tests/test_lean_refinement.py", "tests/test_tla_refinement.py"]
        gate_pytest(report, "FDK kernel + M1/M2", fdk, tests)
    else:
        report.add("FDK kernel + M1/M2", False, "repo missing")

    # decision-os-min
    dos = WORKSPACE / "decision-os-min"
    if dos.is_dir():
        gate_pytest(report, "decision-os-min core", dos, [
            "tests/test_core.py",
            "tests/test_full_loop.py",
            "tests/test_redteam_composition.py",
            "tests/test_redteam_round2.py",
            "tests/test_service.py",
        ])
    else:
        report.add("decision-os-min core", False, "repo missing")

    if args.live_service:
        try:
            import uvicorn  # noqa: F401
            gate_live_service(report)
        except ImportError:
            report.add("Live HTTP service", False, "pip install decision-os-min[service] or uvicorn")

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")

    report.print_summary()
    return 0 if report.ok else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.path.insert(0, str(ROOT))
    raise SystemExit(main())
