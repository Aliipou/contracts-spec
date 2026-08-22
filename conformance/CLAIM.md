# Defensible conformance claim

**One sentence.** AuthGate’s reference PEP (`decision-os-min`) is an executable
Authority Enforcement profile for AI-agent tool calls: an authority verdict is
composed with untrusted constraint evaluators by a deny-dominant lattice meet
(veto-only), under a tested non-amplification discipline, measured as AE-1…AE-10.

**What we claim**

- A **conformance profile** (not a new security principle): AE-1…AE-10, each
  attributed to prior art (Saltzer & Schroeder, Miller 2006, Anderson/Rushby/seL4,
  Macaroons, RFC 7800/DPoP, Haber & Stornetta). See `contracts-spec/conformance/PROFILE.md`.
- A **reference PEP** that mediates tool execution: signed decision, action-content
  binding, one-time token, tamper-evident audit.
- **Composition under non-amplification:** `compose(a, k₁…kₙ) ⊑ a`. Untrusted
  evaluators may refuse; they must not grant, rewrite the tool, or author the
  executed payload.
- **Attenuation** via a macaroon-inspired caveat chain (AE-4/AE-5), not a novel
  token format.

**What we do not claim**

- A better general-purpose policy language than Cedar or OPA/Rego.
- A better ReBAC directory than Zanzibar / OpenFGA / SpiceDB.
- A full Macaroon or Biscuit implementation (we adopt the attenuation *property*).
- Multi-party standardization (one implementation measured → checklist, not a standard).
- That Ed25519 in the runtime is formally verified (ASSUMPTIONS.md axiom).
- That the Theory of Freedom is a security result (see `contracts-spec/POSITIONING.md`).

## Comparison snapshot (honest)

| System | Strength | Relative to this claim |
|---|---|---|
| **Cedar** | Formally analyzed authorization policy | Wins on policy; does not ship our PEP+one-time action binding as one unit |
| **OPA/Rego** | Policy-as-code ecosystem | PDP only — you still build mediation + audit |
| **Zanzibar/OpenFGA/SpiceDB** | Relationship-based authz at scale | Wins on ReBAC; not agent tool-call PEP |
| **Macaroons/Biscuit** | Offline attenuable tokens | We reuse the attenuation idea; they win on maturity/format |
| **This profile + PEP** | Measurable AE-1…AE-10 for agent tool calls with veto-only composition | Narrow wedge; evidence is the conformance suite + red-team corpus |

## How to verify the claim

```text
cd contracts-spec
python -m conformance.suite
# Expected (2026-08-20): 10 pass · 0 fail · 0 not applicable
```

Red-team regressions (exploits kept as permanent tests):

```text
cd decision-os-min
python -m pytest tests/test_redteam_composition.py tests/test_redteam_round2.py -q
```

Cite `ASSUMPTIONS.md` for anything stronger than “tested against this suite.”
