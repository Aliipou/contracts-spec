# Obligation Composition

> Status: **design specification, not implemented.** This document answers
> [`COMPOSITION.md`](COMPOSITION.md) §7 ("obligations do not yet compose") and
> ADR-0001 **Q2**. It fixes the algebra for composing *decisions that carry
> obligations*, the resolution rule for conflicting obligations, and the
> constraint under which composition stays order-independent. Nothing here is
> built yet; §7 is the minimal migration and §8 lists what is deliberately **not**
> built.
>
> **Novelty status: none claimed.** §6 is the honest accounting. The short version
> is in §6.4: this is an engineering integration of known results (XACML
> obligations, Bettini et al. provisions/obligations, Lupu & Sloman conflict
> analysis, CRDT-style commuting operations, generalization lattices). Read §6
> before any README or paper uses the word "novel."

---

## 0. Orientation (read first, the direction matters)

COMPOSITION.md §3 writes the verdict chain **least → most restrictive**
(`ALLOW ≺ LIMIT ≺ CONTAIN ≺ DEFER ≺ DENY`) and calls most-restrictive-wins
`meet`. Strictly, that operation is the *greatest lower bound of the dual order*.
Every argument below turns on the direction of the order, so this document uses
the **safety order** throughout:

```
a ≼ b   ≝   "a is at least as restrictive as b"          (a is safer)
DENY = ⊥      ALLOW = ⊤      composition = ⊓ (glb)
```

Nothing about the implementation changes; `compose.meet` computes the same
function. Only the reading direction of the diagrams is inverted, so that *every*
step of composition — verdicts and obligations alike — is a genuine greatest
lower bound. This is the point that makes §2.2 work.

A second symbol, `⊑`, is used for the **payload information order**: `p ⊑ q` means
"`p` reveals no more than `q`". These are different orders on different sets and
are never mixed.

---

## 1. The failure, concretely

`compose.more_restrictive` selects **one** evaluator's decision dict and discards
the other's entirely. Obligations ride in that dict as ad-hoc keys
(`transformed_payload` for `LIMIT`, `containment` for `CONTAIN`), so discarding
the dict discards the obligation. Two demonstrable losses:

**(a) Within a single evaluator.** `kernel._evaluate` checks containment
*before* the redaction loop and returns immediately, so an action that policy says
must be redacted is never redacted once it is also contained. Reproduced against
the current tree with one policy carrying both `redactions` and
`contain_threat_classes`:

```
threat_class = None        -> LIMIT   transformed_payload = {'ssn': '[REDACTED]', 'body': 'hi'}
threat_class = 'malicious' -> CONTAIN containment = {...}          # ssn never redacted
```

The sandboxed tool receives the real SSN. A sandbox constrains *egress and
lifetime*; it does not constrain **what the tool is shown**. Those are orthogonal
obligations and collapsing one into the other is unsound.

**(b) Across evaluators.** An external authority engine adapted through
`evaluators.authority()` returns `LIMIT` + `transformed_payload`; the kernel
returns `CONTAIN`. `more_restrictive` keeps the `CONTAIN` dict. Same loss. And on
a **tie** — two evaluators both returning `CONTAIN` with different sandbox specs —
`more_restrictive` keeps `d1`, so the second spec is dropped by *evaluator
argument order*.

The generalisation: a verdict is a **scalar summary**; an obligation is
**structured content**. A total order composes summaries. It cannot compose
content. Under a scalar meet, "more restrictive verdict" is silently read as
"strictly stronger decision", which is false: `CONTAIN` is not stronger than
`LIMIT`, it is *incomparable in the obligation dimension*.

---

## 2. Formal model (task item 1)

### 2.1 The soundness criterion, before any algebra

Fix the criterion first, so the algebra can be *checked* rather than asserted.

Give a decision a denotation: `⟦d⟧` is the set of executions (payload delivered to
the tool, runtime environment, side effects) that `d` permits. `DENY` and `DEFER`
denote `∅`. Composing independent evaluators must mean **every evaluator is
satisfied**, so the criterion is:

```
SOUND:   ⟦d₁ ⊓ d₂⟧  =  ⟦d₁⟧ ∩ ⟦d₂⟧
```

Anything weaker permits an execution some evaluator forbade — the failure in §1.
Anything stronger denies an execution every evaluator permitted (safe, but a
false refusal). The verdict-only meet satisfies `SOUND` when obligations are
absent, because the five verdicts form a chain whose denotations are nested.
Everything below is the search for the obligation operator that keeps `SOUND`.

### 2.2 Obligation sets: union is a meet, not a join

An obligation `o` denotes a **constraint** on executions, `⟦o⟧ ⊆ Exec`. A set of
obligations denotes their conjunction, `⟦O⟧ = ⋂_{o∈O} ⟦o⟧`. Then

```
⟦O₁ ∪ O₂⟧ = ⋂_{o ∈ O₁∪O₂} ⟦o⟧ = ⟦O₁⟧ ∩ ⟦O₂⟧
```

which is exactly `SOUND` for the obligation component. So **union is forced**, not
chosen.

The task framing calls this "a JOIN-semilattice of obligation sets (union)". That
is right about the operation and misleading about the structure. Under the
**subset** order, union is the join. Under the **safety** order — the one the rest
of the system is written in — more obligations is *more restrictive*, so

```
O₁ ≼ O₂  ≝  O₁ ⊇ O₂          and    O₁ ⊓ O₂ = O₁ ∪ O₂
```

Union *is* the greatest lower bound in the safety order. The apparent asymmetry
("meet the verdicts, join the obligations") is an artifact of writing obligation
sets with subset ordering. There is no asymmetry: **composition is componentwise
glb in one uniform safety order.** That uniformity is what lets §5's invariants be
stated once instead of twice, and it is why `DENY`-dominance and
obligation-accumulation are the same principle rather than two principles that
happen to point the same way.

*Why obligations accumulate while verdicts restrict* is therefore not two facts.
It is one fact — both components move down the safety order — expressed in two
notations. A verdict moving down removes permitted executions by shrinking the
mode of execution; an obligation set moving down removes permitted executions by
adding constraints. Same direction, same operator.

### 2.3 The algebra

```
Decision  D = V × 𝒪         V = {ALLOW, LIMIT, CONTAIN, DEFER, DENY}
                            𝒪 = finite sets of well-formed obligations

(v₁, O₁) ⊓ (v₂, O₂) = ( v₁ ⊓ v₂ , reduce(O₁ ∪ O₂) )        -- reduce: §3
```

| property | holds | consequence |
|---|---|---|
| commutative | yes (both components) | evaluator order carries no verdict/obligation content |
| associative | yes | n-ary fold is well defined |
| idempotent | yes (`v⊓v=v`, `O∪O=O`) | re-running an evaluator changes nothing; retries are safe |
| identity | `(ALLOW, ∅)` | `compose([]) = (ALLOW, ∅)`; unchanged from today |
| absorbing | `(DENY, O_audit)` — **partially**, see Break 1 | a DENY still carries its audit obligations |

Commutative + associative + idempotent means the fold is a function of the
*set* of evaluator results. That is the formal content of "order has no meaning" —
subject entirely to §4.

### 2.4 Three kinds of obligation, and only one is hard

Obligations are not homogeneous. The distinction drives everything after this
point, and it is the provisions/obligations split of Bettini et al. (§6) crossed
with predicate-vs-function.

| kind | shape | example | composes by |
|---|---|---|---|
| **Filter** (predicate) | `Exec → Bool` | `sandbox{network:none, ttl:5s}`, `require_audit` | pointwise glb of parameters; always defined on a per-parameter chain |
| **Transform** (function) | `Payload → Payload` | `redact(ssn)`, `truncate(body,500)` | **not by union — §4** |
| **Escalation / post** | names a principal or a future act | `defer_to(security-oncall)`, `notify(dpo, 24h)` | union of targets, conjunctive discharge |

Filters and escalations are unproblematic. Filter parameters each sit on their own
chain (`network: any ≻ restricted ≻ none`; `allowed_tools`: glb = **intersection**;
`ttl`: glb = **min**; `persistence`: glb = **false**), so two sandbox specs always
have a glb and never conflict. Escalation targets union: more required approvers is
more restrictive, and the `DEFER` is discharged only when **all** are satisfied.

Transform obligations are the entire difficulty. §4.

### 2.5 Where the (meet, union) intuition breaks

Three breaks. Two are fixable by constraint; one is a permanent limitation.

**Break 1 — the product is dependent, not free.** `D = V × 𝒪` is not a clean
product, because an obligation's *scope* is only meaningful for some verdicts. A
`redact` obligation composed onto a `DENY` is vacuous: there is no execution to
redact. If union is applied blindly, `DENY` decisions accumulate execution-scoped
obligations that can never be discharged, and I5 below becomes untestable (you
cannot check that a dropped obligation was honoured when nothing ran). The fix is
a **scope filter after union**:

```
scope(o) ∈ {EXECUTION, DECISION}
compose = ( v₁⊓v₂ , { o ∈ reduce(O₁∪O₂) : v₁⊓v₂ ∈ PERMITTING or scope(o) = DECISION } )
```

`DECISION`-scoped obligations (audit, notify, escalate) survive a `DENY`;
`EXECUTION`-scoped ones (transform, sandbox) do not. This is a real dent in the
clean algebra and should be stated as such: the obligation component is
verdict-dependent, so `D` is a dependent product. The operator remains
commutative/associative/idempotent because the filter is applied to the already-
computed verdict, which is itself order-independent.

**Break 2 — transform obligations are not predicates.** §4.

**Break 3 — composition is single-pass, so it authorises an action nobody
evaluated.** Under `LIMIT ⊓ CONTAIN` the thing that executes is `redact(p)` in a
sandbox — but *every* evaluator ruled on `p`, not on `redact(p)`. Sound only if
evaluators are **monotone in the payload information order**:

```
MONO:   p ⊑ q   ⟹   eval(p) ≼ eval(q)          "less information cannot buy more permission"
```

`MONO` is not free. A rule of the form "allow only if `payload.amount ≤ 100`" that
treats a missing field as passing is non-monotone: redacting `amount` widens
permission. This is the Crampton–Morisset attribute-hiding hazard (COMPOSITION.md
§7) relocated from attributes to the payload. The alternatives are (a) require
`MONO` and state it as a constraint on evaluators, (b) re-evaluate on the
transformed payload to a fixed point, (c) accept and document.

**Recommendation: (a).** (b) costs an unbounded number of evaluator round-trips
and has no termination guarantee once transforms are parameterised; it also
reintroduces order-dependence through the iteration schedule. (a) is a
single-line constraint that is *testable* (I9) and that plugin authors can satisfy
by treating a missing/redacted field as **fail** rather than pass. Note (a) is a
constraint on **untrusted plugins**, so it cannot be assumed — it must be enforced
by the fail-closed default, which is why I9 is phrased as "missing ⇒ deny", not
"evaluators are monotone".

---

## 3. Conflicting obligations (task item 2)

### 3.1 Reject before resolving: not every demand is a legal obligation

The task's example — one evaluator redacts `ssn`, another *rewrites* it — is not a
conflict to be resolved. It is an **illegal obligation** that must be rejected at
the evaluator boundary, and the reason is load-bearing for ADR-0001.

ADR-0001's central result is that non-authority evaluators are **antitone /
veto-only**: they can restrict but never authorise, so a malicious plugin's ceiling
is denial-of-service. Admitting arbitrary payload *rewrites* as obligations
destroys that result. `redact(ssn)` is a restriction. `ssn := attacker_value`,
`recipient := attacker@evil.com`, `amount := 1_000_000` are not restrictions — they
are **effects**, and an untrusted plugin that can demand one has escalated from
veto to authorship of the action. It does not need to overturn a verdict; it
rewrites what the permitted verdict applies to.

So transform obligations are admissible only if **reductive** in the payload
information order:

```
REDUCTIVE:   t(p) ⊑ p   for all p          "a transform may only remove information"
```

together with idempotence (`t(t(p)) = t(p)`) and a declared **field support**
`supp(t)` outside which `t` is the identity. A transform that adds, invents, or
alters a value toward a *different* value is rejected: the evaluator's decision
composes as `DENY` with reason `illegal-obligation`, exactly as an unknown verdict
string does today (`compose.py` fail-closed).

This is the one place where obligations interact with the TCB argument rather than
sitting beside it: **reductivity is not a modelling convenience, it is the
precondition under which ADR-0001's antitone theorem survives the introduction of
obligations.** Section 6.4 assesses how much credit that observation deserves
(answer: very little, but it is worth writing down).

A practical consequence: obligations must be **declarative data**, not callables —
`{"kind": "redact", "target": "payload.ssn", "params": {}}`. A callable cannot be
checked for reductivity, cannot be signed (I7), cannot cross a process boundary
(ADR-0001 Q1), and cannot be compared for the meet below. This closes the
obligation vocabulary to a **registry**. That is a real cost — plugin authors
cannot ship arbitrary transforms — and it is the cost that buys everything else.

### 3.2 The resolution rule

For genuinely competing legal obligations:

```
reduce(O):
  1. group O by (kind, target)                    -- e.g. ("redact","payload.ssn")
  2. within each group, fold the registered  meet_kind : params × params → params ∪ {⊥conflict}
  3. union across groups
  4. if any group folded to ⊥conflict:  the composed decision is DENY,
     reason "obligation-conflict: <kind>@<target>",  obligations = DECISION-scoped only
```

Each `kind` registers its own parameter meet. Concretely:

- `sandbox` — pointwise, per §2.4. Never conflicts. `allowed_tools` may meet to `∅`,
  which the PEP already treats as "nothing runs".
- `redact` / `truncate(k)` / `mask(...)` on the **same field** — meet in that
  field's transformation lattice:

```
                identity            ⊤  (reveals everything)
               /        \
       truncate(k)     mask_last4
               \        /
              [REDACTED]           ⊥  (reveals nothing)
```

  `meet(truncate(200), truncate(500)) = truncate(200)`. `meet(redact, anything) =
  redact` (⊥ absorbs). `meet(truncate(k), mask_last4)` is **incomparable**: no
  registered glb ⇒ `⊥conflict`.
- `defer_to(X)` vs `defer_to(Y)` — union, conjunctive discharge. Not a conflict:
  requiring two approvers is more restrictive than requiring one. Only an
  *unreachable or unregistered* target fails closed.
- `notify` / `audit` — union. Idempotent, never conflict.

### 3.3 Why DENY and not "over-redact", and why never "pick one"

Deny-dominance in the obligation dimension says: an outcome is admissible only if
it is `≼` **both** inputs. That leaves exactly two admissible responses to an
incomparable pair, and rules out a third that implementations reach for:

1. **`⊥` of the field lattice** (redact it entirely). Always exists, always `≼`
   both. Sound.
2. **`DENY`** (`⊥` of the whole decision lattice). Always `≼` everything. Sound.
3. **Pick one / last-writer-wins / warn-and-drop.** *Not* `≼` the discarded input.
   This is today's behaviour and it is a straight violation of Invariant 2 lifted
   into the obligation dimension: an evaluator's restriction was overridden by
   another evaluator. Forbidden — no configuration flag, no "lenient mode".

Between (1) and (2), **the rule is DENY**, with `⊥`-fallback permitted only where a
field's registry entry declares it explicitly. Reason: option (1) is sound with
respect to I5 but produces an action **no evaluator sanctioned** — Break 3 again.
A payment whose `amount` was silently redacted to `[REDACTED]` because two
evaluators disagreed about masking is not a safer payment; it is an unevaluated
one, and it will either fail confusingly downstream or, worse, be interpreted as a
default. Failing closed surfaces the policy conflict to the operator, which is
where a policy conflict belongs. Silent over-redaction hides it in the payload.

**The accepted cost.** DENY-on-conflict is a DoS surface: an untrusted plugin can
force refusal by emitting a deliberately unmeetable obligation. This is not a new
exposure — ADR-0001 §9 already accepts DoS as the plugin ceiling — but it widens
it from "emit DENY" to "emit an awkward obligation", which is less obviously
attributable in an audit log. Mitigation is operational, not architectural: the
conflict reason names both `kind@target` and the emitting evaluators, so the log
attributes it. No mitigation is specified beyond that.

---

## 4. Order-dependence — the crux (task item 3)

### 4.1 The problem stated at full strength

`⊓` on verdicts is commutative and associative, so COMPOSITION.md §3 concludes
that evaluator order has **no semantic content** and sequencing is a pure
performance choice. Transform obligations threaten that conclusion directly,
because function composition is not commutative:

```
truncate(body,10) ∘ redact(body)   =   "[REDACTE"        -- redact first
redact(body) ∘ truncate(body,10)   =   "[REDACTED]"      -- truncate first
```

If the composed obligation set were "apply `t₁` then `t₂`", the executed payload —
and therefore the audit digest, and therefore the effect — would depend on which
evaluator was listed first in a Python list. That would silently reintroduce
exactly the ordering semantics ADR-0001 spent its argument removing, and it would
do so *below* the verdict, where nobody is looking.

**This is answer (a): restrict to a commutative subset, and enforce the
restriction.** The rest of §4 states the restriction, proves the property it buys,
and — §4.4 — states honestly and specifically what the restriction costs, because
a restriction whose cost is not enumerated is not an answer.

### 4.2 The move: compose transforms by meet, not by function composition

The instinct is to compose transforms the way you compose functions. That instinct
is the bug. A set of transforms is not applied *in sequence*; it is first
**reduced to at most one transform per field** by §3.2's per-field meet, and only
then applied. Function composition never occurs, so its non-commutativity never
arises.

```
{ redact(ssn), truncate(body,500), truncate(body,200) }
        ↓ group by target, meet within group
{ redact(ssn), truncate(body,200) }              -- at most one transform per field
        ↓ apply (fields are disjoint ⇒ any order)
T(p) = { ssn: "[REDACTED]", body: p.body[:200], ... }
```

Two transforms on **disjoint** field supports commute trivially: each is the
identity on the other's support, so neither can observe or overwrite the other's
effect.

**Property (order-independence of obligation composition).** If
(i) every transform declares a field support `supp(t)` and is the identity outside
it, (ii) transforms sharing a support are reduced to one by the registered per-field
meet before application, and (iii) the meet is itself commutative and associative
(a registry obligation, mechanically checkable per kind), then applying the
reduced set in any order yields the same payload, and `compose` over any
permutation of evaluators yields the same `(verdict, obligations, payload)`.

*Argument.* After (ii) the reduced set has at most one transform per field, so
their supports are pairwise disjoint; on disjoint supports the transforms commute
pointwise, so the composite is well defined as a single per-field rewrite. The
verdict component is order-independent by §2.3; the obligation component reduces
by a commutative/associative meet inside groups and a commutative union across
them; the scope filter (Break 1) is a function of the already-order-independent
verdict. ∎

Note what carries the weight: not "transformations happen to commute" — they do
not — but **the reduction step, which guarantees no two transformations ever touch
the same field.** Non-commutativity is designed out of reach rather than reasoned
around. This is the CRDT/Operational-Transformation discipline (§6.2) applied to
obligations: restrict the operation set until concurrent operations commute, then
order genuinely stops carrying information.

### 4.3 One residual order-dependence that exists **today**

Independent of transforms, `more_restrictive` breaks ties by keeping `d1`. So with
two evaluators both returning `DENY` for different reasons, `decision["reason"]`
already depends on argument order. The verdict does not; the *decision object* —
which is what gets signed, audited, and shown to an operator — does. Under
obligations this becomes substantive rather than cosmetic (a tie drops the second
evaluator's obligations entirely, §1(b)).

Fix: the composed decision carries `reasons` as a **canonically sorted list**, and
the obligation list is canonically sorted before signing. This is not pedantry — I8
is stated over the *signed bytes*, and `json.dumps(sort_keys=True)` sorts object
keys but **not list elements**, so two logically identical compositions produced in
different evaluator orders would otherwise yield different signatures. Byte-level
order-independence has to be arranged deliberately.

### 4.4 What the restriction costs — enumerated

The commutative subset is not free. Excluded, each with a concrete example:

1. **Cross-field transforms.** `pseudonym := H(user_id ‖ email)` writing to
   `email` while reading `user_id` has no well-defined single-field support; the
   disjointness argument fails. Excluded.
2. **Non-idempotent transforms.** "append a provenance marker", "increment a
   counter". `t(t(p)) ≠ t(p)` breaks the idempotence needed for retry-safety and
   for the meet to be well defined. Excluded.
3. **Structural transforms.** "drop the third element", "reshape into a list of
   records". These change the *field identity* the support argument is stated
   over. Excluded.
4. **Content-dependent redaction.** "redact any field matching an SSN regex" has a
   support that depends on the payload, so two such obligations may or may not
   overlap depending on input — the conflict check becomes data-dependent and can
   only be decided at composition time, not registration time. **Admissible but
   downgraded**: the meet must be computed per-action, and a per-action overlap
   with an incomparable partner is a per-action `DENY`. This makes some conflicts
   invisible to policy review, surfacing only in production, and that is a genuine
   ergonomic loss.
5. **Open-ended plugin transforms.** Obligations must be registry entries, not
   callables (§3.1). A plugin author who needs a new transform must land a registry
   entry with a declared support, meet, and reductivity proof-obligation. Slow by
   design.

Whether (1)–(3) matter depends on demand that does not exist yet. Today's entire
obligation vocabulary is `{redact, sandbox}`, both of which satisfy the
restriction. Per the project's rule against expanding architecture ahead of
demand, the restriction is adopted **and** the exclusions are recorded so the
decision can be revisited against a real requirement rather than a hypothetical.

### 4.5 What is honestly conceded

Order-independence is **not** preserved for free; it is **purchased** by a
restriction that is real, enumerated above, and mechanically enforced at
registration time. COMPOSITION.md §3's claim needs a rider:

> Evaluator order carries no semantic content **for verdicts unconditionally, and
> for obligations only within the registered commutative obligation vocabulary.**
> The vocabulary is closed for this reason and not merely for schema hygiene. An
> implementation that admits an unrestricted transform obligation has silently
> revoked the claim.

That rider should be added to COMPOSITION.md §3 when this is implemented.

---

## 5. Invariants (task item 4)

Continuing COMPOSITION.md §5's numbering. Each is phrased to be directly testable;
the test sketch is the invariant's meaning, not an illustration of it.

```
Invariant 5  (no obligation is silently weakened)
    For every evaluator result (vᵢ, Oᵢ) and every o ∈ Oᵢ, the composed decision
    (v, O) satisfies:  v = DENY  ∨  ∃ o' ∈ O with same (kind,target) and o' ≼ o.
    TEST: property test over random evaluator multisets; for each input obligation
    assert the witness exists and that meet_kind(o', o) = o'.

Invariant 6  (the executed payload is the image of every demanded transform)
    Let p be action.payload and E the payload handed to the tool. Then
    E = T(p) for the composed transform T, and for every transform obligation t
    demanded by any evaluator,  E ⊑ t(p)  fieldwise in the information order.
    TEST: for each evaluator's t, assert fieldwise E ⊑ t(p). Cheap because
    execute.py already digests the executed payload (W-3).

Invariant 7  (obligations are signed, bound, and never ignored)
    Every obligation in the composed decision lies inside the signed decision body
    and under action_binding. A PEP that encounters an obligation kind it cannot
    interpret or discharge MUST refuse execution — it may never execute and skip.
    TEST: (a) mutate any obligation field -> verify() false;
          (b) inject kind "kind:unknown" -> ExecutionRefused;
          (c) present a decision whose obligations were stripped -> verify() false.

Invariant 8  (composition is order-independent, at the byte level)
    For every permutation π of evaluator results,
        canonical(compose(D₁..Dₙ)) == canonical(compose(D_π(1)..D_π(n)))
    excluding only fields that are timestamps or nonces.
    TEST: property test over permutations comparing the canonical signing bytes,
    NOT the Python dicts. Catches unsorted obligation lists and tie-broken reasons.

Invariant 9  (obligations may only remove information; missing means deny)
    Every registered transform t satisfies t(p) ⊑ p and t(t(p)) = t(p) on all
    payloads, and is the identity outside supp(t). Every evaluator treats an
    absent or redacted field as FAILING its check, never as passing (the
    enforceable form of MONO, §2.5 Break 3).
    TEST: (a) registry-level property test per transform over generated payloads;
          (b) for each evaluator, assert eval(redact_all(p)) ≼ eval(p).
```

I5's phrasing is deliberately weaker than the obvious "no obligation demanded by
any evaluator is absent from the composed decision". Literal set-membership is the
**wrong** invariant: reduction legitimately replaces `truncate(500)` with
`truncate(200)`, and demanding literal presence would forbid the meet that makes
§4 work. The correct statement is that every demand is **dominated** by something
in the composed set. Testing literal membership would produce a test suite that
fails on correct behaviour.

I9(b) is the invariant that carries Break 3, and it is stated as an enforceable
behaviour ("missing ⇒ fail") rather than an assumption about plugin authors,
because plugins are outside the TCB and their good behaviour cannot be assumed.

---

## 6. Prior art and non-claims (task item 5)

### 6.1 What is not new — obligations in access control

- **XACML 2.0 / 3.0** — `Obligation` (and 3.0's `Advice`) expressions attached to
  Permit/Deny; obligations from policies whose decision matches the combined
  decision are **collected together** by the combining algorithm. That is
  obligation union, in the standard, since 2005. XACML 3.0 further requires that a
  PEP which does not understand or cannot discharge an obligation **must act as if
  access were denied**. That is Invariant 7, restated. Neither is contributed here.
- **Bettini, Jajodia, Wang & Wijesekera**, *Provisions and Obligations in Policy
  Management and Security Applications*, VLDB 2002 — the provisions (must hold
  before/as a condition of the decision) vs obligations (must be discharged after)
  distinction, plus reasoning over provision sets. §2.4's Transform/Filter vs
  Escalation/post split is that distinction.
- **Ni, Bertino & Lobo**, *An obligation model bridging access control policies and
  privacy policies*, SACMAT 2008 — obligations bound to purpose and to data
  subjects; obligation dominance and redundancy.
- **Park & Sandhu**, UCON_ABC, ACM TISSEC 7(1) 2004 — pre / ongoing / post
  obligations and attribute mutability. §8's "the PEP cannot verify post-obligation
  discharge" is the known UCON post-obligation problem, not a discovery.
- **Irwin, Yu & Winsborough**, *On the modeling and analysis of obligations*,
  CCS 2006 — obligation systems, accountability, and whether an obligation set is
  *satisfiable*; **Gama & Ferreira**, POLICY 2005 — obligation enforcement
  platforms.
- **Lupu & Sloman**, *Conflicts in Policy-Based Distributed Systems Management*,
  IEEE TSE 25(6) 1999 — the canonical taxonomy of modality and application-specific
  policy conflicts and their resolution by precedence/meta-policy. §3 is a
  narrow instance of it with a specific resolution (fail closed).
- **Sticky policies** — Karjoth, Schunter & Waidner (E-P3P, PET 2002); Casassa
  Mont, Pearson & Bramhall (2003) — obligations travelling bound to the data. The
  binding of obligations into a signed, action-bound decision (I7) is a
  cryptographic instance of that idea.
- Composition algebras already cited in COMPOSITION.md §6 — Bonatti/di
  Vimercati/Samarati TISSEC 2002; Wijesekera & Jajodia 2003; Rao/Lin/Li/Lobo
  SACMAT 2009; Bruns & Huth TISSEC 2011; Crampton & Morisset PTaCL POST 2012 (and
  their attribute-hiding non-monotonicity, which §2.5 Break 3 reuses wholesale);
  Tschantz & Krishnamurthi SACMAT 2006.

### 6.2 What is not new — the order-independence technique

§4's move (restrict the operation set so concurrent operations commute, then
order stops carrying information) is a standard distributed-systems discipline,
not a policy-theory result:

- **Ellis & Gibbs**, Operational Transformation, SIGMOD 1989.
- **Shapiro, Preguiça, Baquero & Zawirski**, *Conflict-free Replicated Data Types*,
  SSS 2011 — commutativity/associativity/idempotence as the design constraint that
  makes replica order irrelevant. §2.3's property table is a CvRDT/CmRDT table.

### 6.3 What is not new — the per-field transformation lattice

§3.2's field lattice with a registered meet is the **generalization lattice** of
the anonymity literature:

- **Samarati & Sweeney**, k-anonymity / generalization hierarchies, 1998;
  **LeFevre, DeWitt & Ramakrishnan**, *Incognito*, SIGMOD 2005 — full-domain
  generalization lattices where the meet of two generalizations is the coarser
  common one. Structurally identical to `meet(truncate(200), truncate(500))`.
- **Denning**, *A Lattice Model of Secure Information Flow*, CACM 19(5) 1976 — the
  information order `⊑` and the reductivity constraint (§3.1) are that lattice.
- Elementary order theory supplies the rest: a product of meet-semilattices is a
  meet-semilattice with componentwise meet; **Ward**, *The closure operators of a
  lattice*, Ann. Math. 1942, for the operator-lattice framing.

### 6.4 Novelty verdict

**Nothing in this document is a new result. This is an engineering integration of
known results.** Stated plainly because a negative answer is the correct
deliverable when it is the true one, and because COMPOSITION.md §0 commits the
repository to not claiming novelty it has not established.

Component by component: obligations attached to verdicts — XACML, Bettini et al.
Union under combination — XACML 3.0. PEP must deny what it cannot discharge —
XACML 3.0. Conflict detection and resolution — Lupu & Sloman. Restricting
operations so order stops mattering — CRDT/OT. Per-field generalization meet —
k-anonymity. "Transforms may only remove information" — Denning. Pre/ongoing/post
obligations — UCON. Product of semilattices — undergraduate order theory. There
is no gap in that list for a contribution to sit in.

Two observations are worth *recording* — not claiming — with visible reluctance:

1. **Reductivity as a TCB precondition, not a modelling choice** (§3.1): that
   admitting unrestricted transform obligations from untrusted plugins breaks
   ADR-0001's antitone/veto-only theorem, because a rewrite is an effect rather
   than a restriction, so a plugin gains authorship of the action without ever
   overturning a verdict. Honest assessment: this is one short step from the
   antitone argument composed with Denning, it is the kind of thing that is
   probably folklore in any system that has actually shipped obligations, and I
   have not run the literature search that would settle it. **Do not call it
   novel.** It is worth writing down because the failure it prevents is easy to
   walk into, not because it is new.
2. **The pairing of reduce-then-apply with fail-closed-on-incomparable** (§3.2 +
   §4.2): CRDT discipline supplies commutativity, XACML supplies deny-on-
   undischargeable, and the combination is what yields order-independence *and*
   no-silent-drop simultaneously. That is a combination of two known techniques.
   Combination is not novelty.

The one thing this repository can claim without hedging is **not a research
claim**: that the obligation algebra is enforced end-to-end — obligations are
inside the Ed25519-signed decision, bound by `action_binding`, and a PEP that
cannot discharge one refuses. That is an implementation property, checkable by
running the tests in §5, and it is the only kind of claim §6 supports.

---

## 7. Migration (task item 6)

Minimal, in dependency order. Four files, one new concept (`Obligation` as
declarative data), no new module.

### 7.1 `compose.py`

```python
# ILLUSTRATIVE SKETCH — not the implementation.
# Obligation = {"kind": str, "target": str, "params": {...}}  -- JSON only, no callables.

OBLIGATION_MEET: dict[str, Callable[[dict, dict], dict | None]] = {...}  # None = conflict
OBLIGATION_SCOPE: dict[str, str] = {"redact": EXECUTION, "sandbox": EXECUTION,
                                    "audit": DECISION, "notify": DECISION}

def compose_decisions(d1: dict, d2: dict) -> dict:
    verdict = meet(d1.get("verdict", DENY), d2.get("verdict", DENY))
    groups: dict[tuple[str, str], dict] = {}
    for o in (*d1.get("obligations", ()), *d2.get("obligations", ())):
        key = (o["kind"], o["target"])
        if key in groups:
            merged = OBLIGATION_MEET[o["kind"]](groups[key]["params"], o["params"])
            if merged is None:                                   # §3.2 step 4
                return _conflict(d1, d2, o["kind"], o["target"])  # -> DENY
            groups[key] = {**o, "params": merged}
        else:
            groups[key] = o
    obligations = [o for o in groups.values()
                   if verdict in PERMITTING or OBLIGATION_SCOPE[o["kind"]] == DECISION]
    return {"verdict": verdict,
            "reasons": sorted({*_reasons(d1), *_reasons(d2)}),      # §4.3
            "obligations": sorted(obligations, key=_canonical_key), # §4.3 / I8
            "action_ref": d1.get("action_ref") or d2.get("action_ref", "")}
```

`meet` and `compose` (the scalar verdict API) are **untouched** — they remain
correct for verdict-only use and are what `compose_decisions` calls.
`more_restrictive` becomes a thin deprecated wrapper delegating to
`compose_decisions`, so existing callers keep working with changed *content*
(§7.5).

### 7.2 `kernel.py`

- `_evaluate` **declares** obligations instead of materialising them: the `LIMIT`
  branch returns `{"kind":"redact","target":f"payload.{f}","params":{}}` rather
  than a finished `transformed_payload`; the `CONTAIN` branch returns
  `{"kind":"sandbox","target":"runtime","params": _CONTAINMENT}`. Materialising
  early is precisely what made the obligation non-composable.
- The containment early-return stops short-circuiting redaction — both branches
  contribute obligations, `verdict = CONTAIN ⊓ LIMIT = CONTAIN`, and the redact
  obligation survives. This alone fixes §1(a).
- `decide` folds with `compose_decisions`, then — **once, after composition** —
  materialises `transformed_payload = apply(composed transforms, action.payload)`
  and writes both `obligations` and `transformed_payload` into the decision before
  `_sign`. Keeping `transformed_payload` and `containment` as mirrored keys
  preserves the current PEP contract during rollout.
- Obligation list is canonically sorted before signing (I8, §4.3).
- An evaluator returning an unregistered `kind`, or a transform failing the
  registry's reductivity check, composes as `DENY` — the same fail-closed path as
  an unknown verdict string.

### 7.3 `execute.py`

The one-line fix that closes the reported hole:

```python
# before:
payload = decision.get("transformed_payload") if verdict == LIMIT else action.get("payload")
# after:
payload = decision.get("transformed_payload", action.get("payload"))   # any verdict
```

Plus one new refusal path for I7: if `decision["obligations"]` contains a `kind`
this PEP does not implement, `raise ExecutionRefused("undischargeable obligation
<kind>")` — never execute-and-ignore. `_payload_digest` already covers I6 with no
change; the `CONTAIN` allowlist check now reads the composed `sandbox` obligation
(intersected allowlist) instead of the first evaluator's spec.

### 7.4 The signed decision

Adds `obligations: [...]` and `reasons: [...]`. Both are inside `_canonical`
automatically (they are decision keys), so the signature covers them with no
change to `_sign`/`verify`. **`json.dumps(sort_keys=True)` sorts object keys, not
list elements** — the obligation and reason lists must be sorted by the *producer*
or I8 fails at the byte level while passing at the dict level.

### 7.5 What breaks for existing callers

| # | Break | Severity |
|---|---|---|
| 1 | `decision["reason"]` (singular) becomes derived from `reasons`; the composed decision is no longer literally one evaluator's dict | cosmetic, but log-parsers break |
| 2 | New keys in the signed body. **Verifiers are fine** (they canonicalise whatever is present); anything that *reconstructs* a decision from a whitelist of fields produces a signature mismatch | hard break for re-serialisers |
| 3 | PEP refuses unknown obligation kinds ⇒ new evaluator + old PEP = refusals | intended, but forces an upgrade order |
| 4 | `transformed_payload` now applied under `CONTAIN` too — this **is** the fix; a deployment that relied on the sandbox receiving the raw payload changes behaviour | intended |
| 5 | Audit `payload_digest` changes for previously-`CONTAIN` actions | expected consequence of 4 |

**Upgrade order is not optional: PEPs first, then evaluators.** An old PEP with a
new kernel silently ignores obligations it does not know — the exact failure this
document exists to remove. A new PEP with an old kernel merely sees no
`obligations` key and behaves as today.

---

## 8. Deliberately not built

Recorded so absence reads as a decision rather than an omission (project rule: no
architecture ahead of demand).

- **Obligation discharge tracking.** Post-obligations ("notify the DPO within 24h")
  cannot be verified by a synchronous PEP. The kernel **records** them in the
  signed decision and the audit chain; discharge is out of scope. This is the known
  UCON post-obligation gap (§6.1) and it is not closed here.
- **An obligation DSL / expression language.** The registry is a closed dict of
  kinds. XACML-style obligation expressions are not adopted.
- **Cross-field, structural, and non-idempotent transforms** (§4.4 items 1–3).
  Excluded until a real requirement names one.
- **Re-evaluation to a fixed point** over transformed payloads (§2.5 Break 3
  option b). Replaced by I9.
- **Refactoring `LIMIT`/`CONTAIN` into derived labels.** With obligations
  first-class, those two verdicts are arguably just summaries of "has a redact
  obligation" / "has a sandbox obligation", and the lattice could shrink to
  `{ALLOW, DEFER, DENY}` + obligations. That is a cleaner model and it is **not**
  taken: it changes the public verdict vocabulary, every policy file, and every
  consumer, in exchange for elegance and no capability. Recorded as a possible
  future simplification, explicitly deferred.
- **Per-tenant obligation registries**, obligation priorities, and meta-policies
  for conflict precedence (Lupu & Sloman's resolution style). Fail-closed is the
  whole conflict policy.
