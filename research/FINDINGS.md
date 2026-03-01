# Research Findings: Constraint Design for UX Evaluation

## Sources examined
- Hypothesis (Python property-based testing) — stateful machines + invariants
- Jepsen (distributed systems correctness testing) — checkers as constraint systems
- Google Lighthouse — log-normal scoring, p10/median calibrated thresholds
- Google RAIL model — Response/Animation/Idle/Load timing constraints
- Google Core Web Vitals — LCP/INP/CLS as a three-constraint UX model
- Z3 official examples — pure solver usage patterns
- ISO/IEC 25010 — software quality characteristics hierarchy

---

## Key finding 1: The best UX constraint systems use DISTRIBUTIONS, not thresholds

Lighthouse doesn't say `lcp <= 2500ms`. It says:
- p10 (good): 2500ms
- median (needs improvement): 4000ms
- Score = logNormal(actual, p10=2500, median=4000)

The score is continuous: 1.0 at p10, 0.5 at median, 0.0 at 2x median.

**Implication for usersim:** A single threshold `P.lcp_ms <= 2500` is binary and brittle.
A constraint like `P.lcp_ms <= P.p10_threshold` where `p10_threshold` is derived from
observed data (stored in perceptions) is continuous and self-calibrating. Or use
multiple constraints per metric: one at "good" level, one at "acceptable" level.

---

## Key finding 2: Jepsen separates OPERATIONS from PROPERTIES

Jepsen architecture:
- **Nemesis**: injects faults (kills nodes, partitions network) — equivalent to scenarios
- **Client**: performs operations and records results — equivalent to instrumentation
- **History**: the raw trace — equivalent to metrics
- **Checker**: verifies properties over the history — equivalent to personas + Z3

Key insight: Jepsen's checkers (linearizability, monotonic reads, no stale reads) each
operate on the FULL history, not a summary. They ask: "is there ANY point in this sequence
where the property was violated?" not "what was the average value?"

**Implication for usersim:** A "search returned results" boolean is not a good constraint.
"Search NEVER returned stale results across all 3 queries" is. The constraint should be
over the sequence, not the aggregate. This requires passing individual-observation arrays
rather than aggregated counts.

---

## Key finding 3: Hypothesis `@invariant` is our closest analog

Hypothesis stateful machines:
```python
class BankAccount(RuleBasedStateMachine):
    balance = 0

    @rule(amount=st.integers(min_value=1))
    def deposit(self, amount):
        self.balance += amount

    @rule(amount=st.integers(min_value=1))
    @precondition(lambda self: self.balance > 0)
    def withdraw(self, amount):
        self.balance = max(0, self.balance - amount)

    @invariant()
    def balance_non_negative(self):
        assert self.balance >= 0

    @invariant()
    def balance_bounded(self):
        assert self.balance < 1_000_000
```

The invariant runs after EVERY rule application. Rules are operations. Invariants are
properties that must hold regardless of the sequence of operations.

**Implication for usersim:** Our scenarios are like rules. Our constraints are like invariants.
But invariants in Hypothesis can reference the full state machine history — not just the
final state. We're only using the final-state equivalent. We're missing invariants about
monotonicity, ordering, and sequential correctness.

---

## Key finding 4: The RAIL model defines constraints by USER ACTION TYPE

Google's RAIL (web.dev/articles/rail):
- **Response** (user tapped): 50ms to respond
- **Animation** (user scrolling): 16ms per frame
- **Idle** (background work): 50ms chunks
- **Load** (initial): 5s on slow 3G

Each CONSTRAINT is scoped to a specific USER INTENT, not just a general timing budget.
The same operation (JS execution) has a 50ms budget in Response context but 16ms in
Animation context. Context changes the constraint.

**Implication for usersim:** Our perceptions should include USER INTENT signals, not just
operation timings. `Implies(P.user_initiated_action, P.response_ms <= 100)` is different
from `Implies(P.background_operation, P.response_ms <= 5000)`. The distinction between
"user-visible" and "background" operations matters enormously to which constraints apply.

---

## Key finding 5: Web Vitals uses exactly THREE constraints for the whole UX

LCP: loading performance — did the page LOAD fast?
INP: interactivity — did the page RESPOND fast?
CLS: visual stability — did the page NOT JUMP?

These are orthogonal dimensions. A page can nail LCP and CLS but fail INP.
The three together cover the full UX quality space with no overlap.

**Implication for usersim:** A well-designed UX constraint system probably has 3-7
orthogonal dimensions. More than that and constraints start overlapping. For local-notes:
- **Capture**: can the user write quickly? (time_to_first_keystroke, arrival_friction)
- **Retention**: does data survive? (reload_loss, data_integrity)
- **Privacy**: does data stay local? (outbound_requests, vendor_surface)
- **Findability**: can the user find their notes? (search_latency, search_accuracy)
These four dimensions are genuinely orthogonal. A constraint system should saturate these.

---

## Key finding 6: The right variables are VIOLATIONS, not timings

Web Vitals measures Cumulative Layout Shift as a score, not a count.
Jepsen counts ANOMALIES (reads of stale data), not averages.
Hypothesis checks if an invariant was EVER violated.

All three converge on the same insight: **the interesting variable is "did X ever happen?"
not "what was the average of X?"**

**Implication for usersim:** Replace timing averages with:
- `sort_ms` → `sort_exceeded_slo_count` (how many times did sort exceed the SLO?)
- `search_hit_count` (aggregate) → `search_returned_zero_for_valid_query` (boolean)
- `storage_error_count` → keep this (it IS a violation count already)

The distinction: `sort_ms = 150` tells you nothing about user experience.
`sort_exceeded_100ms_count = 0` tells you the SLO was never violated.
These are different variables with different Z3 expressiveness.

---

## Summary: What good constraints look like for UX evaluation

1. **Violation counts, not averages** — `error_count == 0`, not `error_rate <= 0.01`
2. **User-intent scoped** — `Implies(P.user_action, P.response_ms <= 100)` not flat timing
3. **Orthogonal dimensions** — capture / retention / privacy / findability (not overlap)
4. **Sequence properties** — "never happened", "always happened", "happened before Y"
5. **Calibrated thresholds** — set from p10 of real observations, not arbitrary numbers
6. **Monotonicity constraints** — `P.data_after_reload >= P.data_before_reload`
7. **Cross-variable relationships** — `P.search_hits + P.search_misses == P.search_queries`

The pattern: observable events → violation counts → Z3 constraints about violation counts.
Not: raw timings → perceptions ratio → Z3 constraints about ratios.

---

## Repos cloned to /workspace/usersim/research/
- hypothesis/   — Python property-based testing (stateful machines, invariants)
- jepsen/       — Distributed systems testing (checkers, history, nemesis)
- z3/           — Z3 official Python examples

## Files downloaded
- lighthouse_scoring.js   — Google's log-normal scoring model
- lighthouse_lcp.js       — LCP audit with p10/median calibration
- lighthouse_constants.js — Timing budgets and device profiles
