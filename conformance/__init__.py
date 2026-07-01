"""Decision OS conformance toolkit — reference enforcers for DEPENDENCY_RULES.md.

This is META-tooling (it enforces the contracts), not domain logic and not part of
the contract *data* under schemas/. Consumer repos vendor or invoke these checks
in their own CI. If contracts-spec is later kept strictly data-only, this package
moves to its own repo without changing the rules it enforces.
"""
