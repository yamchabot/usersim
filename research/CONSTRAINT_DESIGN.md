# Constraint Design for UX Evaluation Systems

Notes from discussion on 2026-03-01.

---

## What qualifies as a dimension

A dimension earns its integer range if and only if constraints use it in **arithmetic
relationships with other dimensions** — not just point checks. The test is simple: if
every constraint referencing this dimension is of the form `== k` or `>= k` for some
constant k, it is a boolean wearing integer clothes. You are using one point out of 2^32.

An integer dimension is legitimate when:
- It appears in **proportionality**: `D <= N * 0.1` (durability bounded by session size)
- It appears in **conservation**: `A + B == C` (parts sum to whole)
- It appears in **monotonicity**: `before <= after` (ordering across time)
- It appears in **conditional scaling**: `Implies(N >= 10, F <= N * 200)` (budget grows with scale)
- Its precise value changes the truth value of constraints involving *other* variables

The dimension `zero_result_count` is only real if it appears in something like
`zero_result_count * 5 <= total_searches` ("at most 20% of searches return nothing").
If it only appears as `== 0`, collapse it into the boolean `search_ever_failed` computed
in perceptions, and do not give it a Z3 dimension slot.

---

## How to identify a useless dimension

Three failure modes:

**Point-only usage.** All constraints on dimension X are `X == k` or `X >= k` for a
constant. Run `usersim audit` and look at the bottom of the variable density table —
variables appearing in ≤1 constraint with another variable are candidates.

**Invariant across scenarios.** If X has the same value in every scenario, it is a
constant. Z3 gains nothing from treating it as a variable.

**No cross-dimensional entanglement.** If removing X does not affect the satisfiability
of any constraint containing another variable, X is isolated. A dimension earns its place
by being load-bearing — other constraints depend on its value.

---

## How to come up with dimensions

Start from the question: **what does the user experience as a continuum?**

Not "did the save work" (boolean) — that is a point check.
Yes "how much of what I wrote survived" (fraction of writes retained) — that is a continuum.

Not "were there outbound requests" (boolean).
Yes "how many outbound events per user action" — that scales with session length.

Not "was search fast" (boolean).
Yes "how many searches failed to return results the user expected" — that accumulates.

The test: can a user experience this as *worse* or *better* on a spectrum? If yes, it is a
dimension. If it is strictly pass/fail with no gradation, it is a boolean and should be
computed in perceptions, not given a Z3 variable slot.

---

## What constraints look like with 3–7 dimensions

With k dimensions, target roughly:

| Type | Count | Description |
|------|-------|-------------|
| Anchor | k | establish valid range per dimension (non-negative, bounded above) |
| Conservation | k | each dimension bounded by or equal to another (D <= N, A + B == C) |
| Cross-dimensional | k*(k-1)/2 | one relationship for each pair of dimensions |
| Ternary | ~k | most important invariants involving 3 dimensions |
| **Total** | **~25–30** | for k=5 |

Each constraint involves **2–4 unique variables**. No constraint should involve all k
dimensions — that is unreadable and hard to debug when it fails.

The typical shape: `A <= B * coefficient`, `Implies(A > k, B <= C)`, `A + B <= C + D`.

---

## Concrete example: notes app, 5 dimensions

```
F  friction_ms          — total time before user can write (ms, 0–∞)
D  data_lost_count      — notes not present after reload (0–N)
P  outbound_event_count — data-leaving events in the session (0–∞)
S  search_fail_count    — searches returning no results (0–total_searches)
N  session_write_count  — total notes written (sets session scale)
```

All five are raw integers. All participate in cross-dimensional constraints.
None is only checked for `== 0`.

```python
# Anchors (5)
F >= 0
D >= 0
P >= 0
S >= 0
N >= 0

# Conservation (5)
D <= N                           # can't lose more notes than you wrote
S <= N                           # can't fail more searches than you have notes
F <= N * 2000 + 500              # friction budget grows with session (2s/note + 500ms baseline)
P <= N * 0                       # zero outbound events regardless of N (coefficient = 0)
S + (N - S) == N                 # documents that S is a subset of N

# Cross-dimensional (10)
Implies(D > 0,  D * 20 <= N)     # if any loss, at most 5% of notes lost
Implies(P > 0,  P * 10 <= N)     # if any outbound, at most 10% of operations leaked
Implies(S > 0,  S * 5  <= N)     # if any search failures, at most 20% of notes cause them
Implies(N >= 5, D == 0)          # bulk sessions: perfect retention required
Implies(N >= 5, F <= N * 1000)   # bulk sessions: friction stays proportional to size
Implies(P > 0,  S > 0)           # domain hypothesis: outbound events degrade search
Implies(D > 0,  F > 1000)        # domain hypothesis: data loss correlates with high friction
Implies(P > 0,  D == 0)          # privacy violations don't cause data loss (orthogonality check)
Implies(N >= 1, F >= 100)        # any session has at least 100ms friction (sanity lower bound)
Implies(S > 0,  F > 500)         # failed searches correlate with high-friction scenarios

# Ternary (5)
D + S <= N                       # loss + search failures together bounded by session size
F + P * 100 <= N * 3000          # combined friction+privacy penalty bounded by session scale
Implies(And(D == 0, P == 0), S * 10 <= N)    # clean sessions: search failures < 10%
Implies(And(P > 0, S > 0), D <= N // 10)     # when privacy+search fail, cap data loss
Implies(And(N >= 10, D == 0), F <= N * 500)  # large clean sessions: friction < 500ms/note
```

25 constraints, 5 dimensions. Every dimension appears in both anchor and cross-dimensional
constraints. `P` appears as `<= 0` in one anchor, but also in `Implies(P > 0, S > 0)` and
`F + P * 100 <= N * 3000`. Its coefficient (100) means one outbound event carries the same
penalty as 100ms of friction — Z3 reasons about that tradeoff. That is why `P` is not just
a boolean.

---

## The rules in short

1. A dimension is real when its *numeric value* changes the truth of constraints
   referencing *other dimensions*
2. A constraint earns its place when it would be *false* for some combination of values
   the system could plausibly produce
3. `== 0` on an integer dimension is legitimate only if other constraints use that
   dimension in non-point ways
4. If all constraints on dimension X reduce to pass/fail independent of other dimensions,
   X is a boolean and should be collapsed into perceptions
5. Target: 3–5 unique variables per constraint, 20–30 total constraints for k=5 dimensions,
   most cross-dimensional
6. Conservation laws (`A + B == C`, `D <= N`) are the cheapest high-value constraints —
   they immediately establish the feasible region without needing domain knowledge
7. The interesting constraints are proportionality (`D * 20 <= N`) and conditional
   relationships (`Implies(P > 0, S > 0)`) — these are the ones Z3 can reason about
   combinatorially that no simple threshold check can replicate

---

## Relationship to the FINDINGS.md research

The Jepsen/Hypothesis/Lighthouse research supports these rules:
- Jepsen uses anomaly *counts* (not booleans) because counts participate in order relationships
- Lighthouse uses p10/median calibration because fixed thresholds are point checks;
  relative thresholds (`F <= N * 2000`) self-calibrate
- Hypothesis `@invariant` is what a cross-dimensional constraint is: a property that
  must hold across all combinations of rule applications, not just at a fixed point
