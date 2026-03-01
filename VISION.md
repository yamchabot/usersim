# VISION.md

## The core idea

You run your application a small number of times.
Each run produces a set of facts about how your system behaved.
Z3, a theorem prover, evaluates thousands of logical constraints against those facts simultaneously.

One run. Thousands of checks. Build time bounded by how many times you run your app, not by how many assertions you want to make.

That's the whole idea. Everything else follows from it.

---

## Why this matters now

AI coding tools are pushing feature velocity 4–40× faster than before.
Management is starting to expect week-long timelines for work that used to take months.
Features that once took a team a quarter now ship in a day.

This is genuinely useful. It's also a reliability time bomb.

When features accumulate at that rate, with no one tracking the relationships between them, you get drift. Silent regressions. A system that technically passes all its tests but slowly stops doing what the business actually needs.

The answer is more tests. Not 2× more. Not 10× more. To match the feature velocity with real safety margins, you need 100×, 1000×, maybe 10,000× the test coverage you have today.

The obvious problem: 10,000× more tests means 10,000× longer builds. That's untenable.

usersim's answer: break the coupling between running your app and evaluating assertions.

---

## The coupling problem

Every traditional test framework works the same way:

1. Set up state
2. Run the application
3. Make one assertion
4. Tear down

The application run is the expensive part. The assertion is cheap. But they're bundled — you pay the full cost of a run for every single assertion.

usersim inverts this. You run your application once per path. That produces a snapshot of facts — raw numbers about how your system behaved. Then Z3 evaluates every constraint in every persona against that snapshot simultaneously. The application run cost is fixed. The constraint evaluation cost is effectively zero.

Add 100 more constraints across 10 more personas: Z3 evaluates 1,000 additional checks in milliseconds. No additional application runs.

---

## Z3 is the engine

Z3 is a theorem prover and constraint satisfaction engine from Microsoft Research. It's not an assertion library. It reasons about relationships between variables, proves whether constraint systems are satisfiable, and finds counterexamples when they're not.

Most tools use Z3 as an expensive way to check `x > 5`. That's wasting it.

Z3 is built for:
- **Cross-variable arithmetic**: `error_count * 1000 <= total_requests * 1` (error rate < 0.1% without computing a ratio)
- **Structural invariants**: `Not(And(exit_code == 0, result_count == 0))` — can't succeed with zero results
- **Matrix arithmetic**: `results_total == person_count * scenario_count` — the output matrix must be complete
- **Conditional reasoning**: `Implies(And(load_high, cache_cold), response_ms <= 2000)` — multi-premise conditionals
- **Scaling constraints**: `wall_ms <= result_count * 10` — time budget scales with work done
- **Consistency proofs**: `satisfied_count <= total_count` — arithmetic invariants that catch corrupt data
- **Boolean arithmetic**: `(has_doctype + is_self_contained + has_cards) >= 2` — majority-vote quality checks

Every one of these is free once you've collected the facts. Z3 evaluates all of them in one pass.

The design target: write constraint files that are *dense*. Many personas. Many constraints per persona. Z3 doing real arithmetic and relational reasoning, not just threshold checks. The path runs stay small; the coverage is enormous.

---

## Three layers, one rule each

### Instrumentation: measure, don't judge

Instrumentation runs your application and collects raw numbers. Its only job is to produce a JSON object with as many measurements as you can extract. Response times, counts, error totals, file sizes, exit codes — everything.

The rule: **no judgements**. Numbers only. Don't compute derived values if the raw values are available. Don't decide whether something is "fast enough." That's Z3's job.

More raw variables means more constraint surface. Collect everything.

### Perceptions: rename, don't reason

Perceptions translates raw metric names into the stable variable names your constraints will reference. It normalizes the interface between instrumentation (which changes when your app changes) and constraints (which should be stable).

The rule: **no thresholds, no opinions**. Pass numbers through. Rename for clarity. Compute a ratio only if the raw numerator and denominator aren't available separately — because if they are, Z3 can do the division and different personas can apply different thresholds.

If you find yourself writing `"is_fast": x < 200` in perceptions, stop. That's a constraint: `Implies(P.measured, P.response_ms < 200)`. Put it in Z3.

If you find yourself computing `error_rate = errors / total` in perceptions, stop. Pass `errors` and `total` separately. Let each persona express its own rate threshold using cross-multiplication: `P.errors * 1000 <= P.total * 1`.

Perceptions should be boring. A thin translation layer. The moment it starts making decisions, you've moved logic out of Z3 and thrown away coverage.

### Constraints: this is where the work happens

Persona constraint files are Z3 programs. They express the requirements of a specific user class — not as a list of threshold checks, but as a logical model of what that user needs to be true for the system to be working for them.

Different personas should have genuinely different constraint logic, not just different threshold values. A CI engineer cares that error exits are exactly `== 1` (Unix convention), not just `>= 1`. An ops engineer cares that timing budgets scale with load. A persona author cares that `results_total == person_count * scenario_count` — if it doesn't, her report is structurally broken regardless of what the numbers say.

The rule: **if it can be expressed as a Z3 constraint, it belongs in Z3**. Push hard on this. The more you put in constraints, the more coverage you get for free.

---

## What good looks like

A mature usersim suite:
- 5–20 paths that exercise realistic application states
- Rich instrumentation that exposes every measurable variable
- A thin perceptions file that just passes numbers through with stable names
- 10–50+ personas with dense, differentiated constraint sets
- Z3 doing arithmetic, relational reasoning, and invariant checking — not just threshold comparisons

The path runs are bounded and cheap. The constraint evaluation is free. Coverage grows without limit as you add personas and constraints.

That's how you get 10,000× test coverage without a 10,000× build.
