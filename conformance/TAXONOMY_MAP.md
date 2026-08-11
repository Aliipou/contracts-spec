# Mapping the exploit corpus onto existing taxonomies

**Purpose.** Before proposing anything to anyone, find out whether this corpus is a
duplicate. Every exploit is mapped onto an existing category if one fits. Where nothing
fits, that gap — not a new standard — is the contribution proposal.

**Taxonomies used:** [OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)
(ASI01–ASI10, published Dec 2025, 100+ contributors) and its companion MCP Top 10 for
the tool-connection layer.

**Corpus:** 73 runnable tests across three adversarial rounds against two
authorization layers. Tests are variants; what is mapped below are the ~20 distinct
*failure classes* they demonstrate.

---

## Part 1 — classes that already have a home

These are **not** a contribution. They are evidence that the corpus exercises risks the
community has already named, which is what makes it useful as a *reference
implementation* rather than as a new taxonomy.

| Failure class | Maps to | Evidence |
|---|---|---|
| `capability` and `tool` never compared — one grant executes any tool | **ASI03 Identity & Privilege Abuse** | `test_ESCAPE_A1*` |
| Evaluator injects forged `token_id`/`capability`, kernel signs it | **ASI03** | `test_fixed1*` |
| Evaluator mutates the live action to escalate capability (TOCTOU) | **ASI03** | `test_fixed4*` |
| A TRANSFORM re-selects the tool past the capability check | **ASI03 / ASI02** | `test_ESCAPE_A8b` |
| A "restricting" evaluator authors the executed payload | **ASI02 Tool Misuse & Exploitation** | `test_fixed2` |
| Redaction bypassed so a secret reaches the tool | **ASI02** | `test_ESCAPE_A2*`, `test_fixed3*` |
| In-process evaluator frame-walks to the signing key | **ASI05 Unexpected Code Execution** | `test_break_inprocess_evaluator_steals_signing_key` |

## Part 2 — classes with no clean home

Three families, each demonstrated by runnable exploits, each absent from the agentic
taxonomies because those describe **agent behaviour** while these describe defects in
the **enforcement layer itself**.

### Family A — Verdict type confusion in the decision path

A verdict whose *value* and *identity* disagree. A `str` subclass valued `"DENY"` whose
`__hash__`/`__eq__` impersonate `"ALLOW"` governs the composition as a veto **and**
passes the permission gate: a refusal that executes, carrying a signature that verifies,
because JSON serialises the subclass by value. Neighbouring dialects (`"deny"` lowercase,
a `StrEnum` from another engine, a bare string where an enum was assumed) produce the
same shape by accident rather than malice.

*Why it is not ASI-anything:* no prompt is injected, no privilege is over-broad, no tool
is misused. The enforcement layer simply disagrees with itself about what its own
verdict says. It is a **type-discipline flaw in authorization plumbing**, and it appeared
independently in two unrelated codebases in this corpus.

Evidence: `test_fixed_lying_verdict_is_a_real_veto`, `test_fixed_R2_normalize_canonicalizes_a_lying_str_subclass`,
`test_ESCAPE_A8`, `test_holds_offlattice_lowercase_denies`, `test_defence_authority_adapter_rejects_dialect_drift`.

### Family B — Ceilings keyed on an attacker-authored identifier

Every temporal or cumulative control — budget, step limit, rate limit, nonce replay
defence, cross-step taint pin — keyed on a `session_id` the agent supplies. Rotating it
resets all of them at once: a $100 budget became $1,000 of executed effects across 20
rotated sessions, while the monitor reported every session as compliant.

*Why it is not ASI-anything:* the generalisation is that **any control keyed on a field
the constrained party controls is not a control**. That is a design-level class covering
budgets, quotas, rate limits, dedupe and taint tracking simultaneously, and it is
reachable through shipped reference adapters rather than requiring a crafted client.

Evidence: `test_ESCAPE_A4`, `A4b`, `A4c`, `A4d`, and the negative control
`test_CONTAINED_kill_switch_cannot_be_outrun_by_a_new_session` — which shows the one
control in the same system that is *not* session-keyed survives.

### Family C — Audit integrity under partial failure

The evidence layer lies precisely when something else breaks. A tamper-evident log
records a full-stack **PERMIT** for an action the gate **DENIED**, because the record is
written before an external notary is called and the resulting failure is converted to a
denial that is never recorded. An attacker-influenced field that serialises for signing
but not for logging makes the mandatory audit write raise *after* the effect has run —
effect performed, log empty. Tail truncation passes `verify()` with no forgery and no
recomputation. A composed refusal is logged without the reason it was refused.

*Why it is not ASI-anything:* the taxonomies treat logging as a mitigation. This family
is about the mitigation being **actively false** under dependency failure — which is
worse than absent logging, because it is trusted.

Evidence: `test_ESCAPE_A5`, `A5b`, `A5c`, `A9`, `test_fixed_a_poisoned_reason_cannot_outrun_the_audit_log`,
`test_fixed6_a_composed_deny_is_audited_with_its_reason_and_tool`.

---

## What this map licenses, and what it does not

**Licensed:** proposing Families A–C to the OWASP GenAI Security Project through its
stated contribution path, as *runnable evidence attached to existing categories or as
candidate additions*. The project explicitly asks the community to refine the taxonomy
together rather than each team rebuilding it, and a battery of failing tests is the one
thing a prose taxonomy cannot supply.

**Also licensed:** the CSA is now a CVE Numbering Authority for agentic AI. Confirmed
defects in third-party software found with this corpus have a disclosure route, and
using it is participation in the infrastructure rather than a claim to have built one.

**Not licensed:** publishing a competing standard. ASI01–ASI10 exists, has 100+
contributors, and a companion MCP list. One person announcing a rival taxonomy is
ignored, and would repeat the exact error this project already made once — building
something that already existed because nobody checked first.

**Honest limits.** The corpus was produced against two codebases, one of which is our
own; Families A–C may be artefacts of a shared design lineage rather than general
classes. Running the battery against unrelated implementations is what would settle
that, and it has not been done yet. Until it is, these are **candidate** families, not
established ones.
