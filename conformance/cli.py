"""Command line entry point — point the profile at any implementation.

    python -m conformance --driver conformance.drivers.http:HttpDriver \\
                          --endpoint http://localhost:8080/authorize
    python -m conformance --list
    python -m conformance --driver ... --json report.json

The whole point of a conformance profile is that it measures software its author did
not write. Until this had a CLI and a loadable driver it could only measure one
implementation, which is a demo, not a profile.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from typing import Any

from .probes import Verdict as PVerdict
from .probes import run_probes
from .suite import CHECKS, Result, run


def load_driver(spec: str, **kwargs: Any) -> Any:
    """Load `package.module:ClassName` and instantiate it with the given options."""
    if ":" not in spec:
        raise SystemExit(f"--driver must be 'module:ClassName', got {spec!r}")
    module_name, class_name = spec.split(":", 1)
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise SystemExit(f"cannot import driver module {module_name!r}: {exc}") from exc
    try:
        cls = getattr(module, class_name)
    except AttributeError as exc:
        raise SystemExit(f"{module_name!r} has no {class_name!r}") from exc
    try:
        return cls(**{k: v for k, v in kwargs.items() if v is not None})
    except TypeError as exc:
        raise SystemExit(f"cannot construct {spec}: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="conformance",
        description="Measure an authorization implementation against the Authority "
        "Enforcement Profile v0.1. See PROFILE.md.",
    )
    p.add_argument("--driver", help="module:ClassName implementing the Driver protocol")
    p.add_argument("--endpoint", help="passed to the driver (HTTP drivers use this)")
    p.add_argument("--token", help="passed to the driver as an auth token, if it takes one")
    p.add_argument("--json", dest="json_out", help="write a machine-readable report here")
    p.add_argument("--list", action="store_true", help="list the requirements and exit")
    p.add_argument("--probes", action="store_true",
                   help="also run the attack probes for the candidate failure families")
    args = p.parse_args(argv)

    if args.list:
        print("Authority Enforcement Profile v0.1\n")
        for rid, title, _ in CHECKS:
            print(f"  {rid:6} {title}")
        print("\nFull normative text: PROFILE.md")
        return 0

    if not args.driver:
        p.error("--driver is required (or use --list)")

    driver = load_driver(args.driver, endpoint=args.endpoint, token=args.token)
    failures = run(driver)

    if args.probes:
        print("\n" + "-" * 100)
        print("ATTACK PROBES — candidate failure families (see TAXONOMY_MAP.md)")
        print("  BROKEN = the attack succeeded.  UNSUPPORTED = no surface; nothing measured.\n")
        broken = 0
        for r in run_probes(driver):
            print(f"  {r.verdict.value:12} {r.id:4} [{r.family}] {r.title:52} {r.detail}")
            broken += r.verdict is PVerdict.BROKEN
        print(f"\n  {broken} broken")
        failures += broken

    if args.json_out:
        rows = []
        for rid, title, check in CHECKS:
            try:
                result, detail = check(driver)
            except Exception as exc:  # a check that crashes is not a pass
                result, detail = Result.FAIL, f"{type(exc).__name__}: {exc}"
            rows.append(
                {"id": rid, "title": title, "result": result.value, "detail": detail}
            )
        report = {
            "profile": "Authority Enforcement Profile v0.1",
            "implementation": getattr(driver, "name", args.driver),
            "results": rows,
            "summary": {
                "pass": sum(1 for r in rows if r["result"] == "PASS"),
                "fail": sum(1 for r in rows if r["result"] == "FAIL"),
                "not_applicable": sum(1 for r in rows if r["result"] == "N/A"),
            },
            "note": "N/A is not conformance. It means the implementation does not claim "
            "the capability, so the requirement was not measured.",
        }
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"\nreport written to {args.json_out}")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
