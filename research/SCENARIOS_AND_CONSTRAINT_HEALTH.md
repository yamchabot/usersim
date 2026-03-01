# Scenarios, State Walkers, and Constraint Health

Notes from discussion on 2026-03-01.

---

## State-walker framing is more accurate than "scenarios"

A scenario is a fixed path. A state-walker explores the graph, potentially differently
each run — closer to what production users actually do. The instrumentation should care
about *what happened during the walk*, not *which walk was taken*. Dimensions are
properties of the walk, not identifiers for the path.

---

## Origin story

usersim emerged from doing statistical analysis over large sets of behavioral samples to
steer an AI agent on a specific task. The formalization: replace ad-hoc visualization with
constraint-based evaluation. The "cheap enough to keep" instinct matters — if it's
expensive it becomes a milestone gate; if it's cheap it becomes a continuous signal.

---

## Measuring usersim's own effectiveness

**Constraint violation frequency is the health metric for usersim itself.**

A constraint that fires frequently is actively shaping agent behavior — it's steering.
A constraint that never fires in N runs is either:
1. Catching a real regression → valuable, but could be a unit test
2. Never at risk → useless in this system

The right question for a never-firing constraint isn't "delete it?" but "why does it
never fire?" If the behavior is always safe by construction, the constraint belongs in a
unit test. If the behavior is risky and the constraint is the only guard, keep it but
tag it for regression-only runs.

---

## Constraint tagging by run context

Testing frameworks handle this with tags (`@pytest.mark.slow`, `@tag("regression")`).
usersim should support the same:

- `continuous` — runs on every agent invocation (must be cheap, high signal)
- `regression` — runs on release candidates and nightly, not every PR
- `smoke` — minimal set for fast sanity check

Constraints that frequently fire → `continuous` (actively steering)
Constraints that rarely fire but guard known failure modes → `regression`
Constraints that never fire after 50+ runs → candidate for downgrade to E2E / unit test

---

## The corollary

Constraints that frequently fire but are recoverable are the most valuable ones for the
agent feedback loop. They are actively shaping behavior, not just guarding against
known regressions. A usersim dashboard should surface violation frequency prominently —
that is the signal that the constraint system is doing useful work.
