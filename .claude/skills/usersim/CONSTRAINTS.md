# usersim — Constraint Architecture

Read this when designing the Z3 judgement layer for a project.
This is a sub-skill of `.claude/skills/usersim/SKILL.md` — read that first for pipeline overview.

---

## What Z3 is doing here

Z3 is not running tests. It is evaluating whether a flat dict of numeric signals satisfies
a set of logical constraints — and by extension, computing *coverage* over the space of
possible signal combinations.

The effective test count formula captures this:

```
effective_tests = sum(4^k  for each constraint, k = distinct Z3 variables)
```

A single constraint `P.wall_ms <= P.person_count * P.scenario_count * 3000` with 3 variables
covers 4³ = 64 combinations. This is why multi-variable constraints are the goal — not because
they're clever, but because they give you combinatorial coverage automatically.

---

## Single-variable vs. multi-variable constraints

| Complexity | Pattern | Effective tests | When to use |
|-----------|---------|----------------|-------------|
| 1 var | `P.exit_code == 0` | 4 | Sanity checks, hard requirements |
| 2 var | `P.wall_ms <= P.results_total * 3000` | 16 | Scalability relationships |
| 3 var | `P.wall_ms <= P.persons * P.paths * 3000` | 64 | Budget proportionality |
| 4 var | `P.bytes >= P.total * P.persons * P.paths * 50` | 256 | Size/content relationships |

Single-variable checks are the floor, not the ceiling. A system with only single-variable
constraints has shallow coverage. Aim to have at least a third of your constraints touch
2+ variables.

---

## The `named()` wrapper

Always name constraints. Always.

```python
from usersim.judgement.z3_compat import named

named("group/check-name", expr)
```

The name appears in:
- Report failure output
- The Group × Path coverage matrix
- The constraint list in each persona card
- The bipartite graph visualization

Naming convention: `group/check-name` where group is a domain prefix:

| Group | What it covers |
|-------|---------------|
| `pipeline` | Exit code → output coherence |
| `timing` | Wall clock budgets |
| `errors` | Denial paths, non-zero exits, stderr |
| `matrix` | results_total = persons × paths invariants |
| `report` | File creation, size, self-containment |
| `scaffold` | Init output, file structure |
| `judge` | Judge subcommand correctness |
| `<persona>` | Persona-specific checks |

---

## Conditional constraints with `Implies`

```python
from usersim.judgement.z3_compat import Implies, And, Not

# "If pipeline exited 0, output must be valid JSON"
named("pipeline/exit-0-implies-valid-json",
      Implies(P.pipeline_exit_code == 0, P.output_is_valid_json))

# "If both conditions hold, then..."
named("pipeline/valid-json-and-schema-implies-results",
      Implies(And(P.output_is_valid_json, P.schema_is_correct),
              P.results_total >= 1))

# "This must never happen"
named("pipeline/no-silent-success",
      Not(And(P.pipeline_exit_code == 0, P.results_total == 0)))
```

**Vacuous antecedents are wasted coverage.** If `P.pipeline_exit_code` is never 0 in any
path, then every `Implies(P.pipeline_exit_code == 0, ...)` fires vacuously and provides
zero signal. Check after every run:

```bash
python3 -c "
import json
r = json.load(open('results.json'))
vac = [(x['person'], x['path'], c['label'])
       for x in r['results']
       for c in x.get('constraints', [])
       if c.get('antecedent_fired') is False]
print(f'{len(vac)} vacuous')
for p,s,l in vac[:20]: print(f'  {p}/{s}: {l}')
"
```

If vacuous constraints exist, add a path that exercises the antecedent.

---

## Structural invariants with `Not(And(...))`

For constraints that express "this combination must never occur":

```python
# No results without persons
named("matrix/no-results-without-persons",
      Not(And(P.results_total >= 1, P.person_count == 0)))

# Exit 0 with empty output is a silent failure
named("pipeline/no-silent-success",
      Not(And(P.pipeline_exit_code == 0, P.results_total == 0)))
```

These are different from `Implies` — they assert a combination is *impossible*, not that
one thing follows from another. Use `Not(And(...))` for invariants that must hold universally,
`Implies(antecedent, consequent)` for conditional rules.

---

## Sequential constraints

The flat dict model handles sequential reasoning through one of two patterns depending on
granularity required. The key insight: **Z3 should not reason about sequence transitions**.
It should reason about summary scalars that the perceptions layer computes from the trace.

### Pattern 1: Ordinal witness (most sequences)

When you need to express "how far did the system get", encode the sequence as an integer
ordinal in perceptions:

```python
# perceptions.py — run a state machine over the trace, emit the result
"last_successful_phase": 3,  # 0=none 1=init 2=config 3=run 4=report
"phase_skipped": 0,          # 1 if any phase was skipped
"first_failure_phase": -1,   # -1 means no failure observed
```

Z3 constraints over these scalars:
```python
# If we reached phase 3, nothing was skipped to get there
named("seq/no-skipped-phases",
      Implies(P.last_successful_phase >= 3, P.phase_skipped == 0))

# Failure must come after at least one success
named("seq/failure-after-progress",
      Implies(P.first_failure_phase >= 0, P.last_successful_phase >= 0))
```

This is **O(1) variables for O(n) sequence length**. The solver sees flat scalars, not state.

### Pattern 2: Per-step Implies chains (step-specific constraints)

When you need to express specific ordering requirements between named steps:

```python
named("seq/config-requires-init",
      Implies(P.config_attempted, P.init_exit_code == 0))
named("seq/run-requires-config",
      Implies(P.run_attempted,    P.config_exit_code == 0))
named("seq/report-requires-run",
      Implies(P.report_attempted, P.run_exit_code == 0))
```

Each constraint is simple — one antecedent, one consequent. Z3 handles each in O(1).
**Linear in step count, no combinatorial explosion.**

The perceptions dict needs one boolean per step:
```python
"init_attempted":   1,
"config_attempted": 1,
"run_attempted":    1,
"report_attempted": 1,
"init_exit_code":   0,
"config_exit_code": 0,
"run_exit_code":    0,
"report_exit_code": 0,
```

### What NOT to do: temporal unrolling

The expensive approach is BMC-style full state unrolling — adding `step_1_state`,
`step_2_state`, ..., `step_n_state` to the flat dict and writing cross-step constraints
that force Z3 to reason about all combinations simultaneously. This causes the solver
latency Daniel described and should be avoided.

**Rule:** if you find yourself writing `step_N_X` and `step_N+1_X` variables and constraints
that relate them, stop. Move the sequence reasoning into the perceptions layer and emit a
summary scalar instead.

### When sequences genuinely require more

If a sequence has branching logic (success path A, failure path B, recovery path C) that
you need to verify separately:

1. Instrument each path as a separate path — paths are free, solver time is not
2. Use a `path_taken` integer perception (`0=A, 1=B, 2=C`) and condition constraints on it
3. Consider whether the branching logic belongs in instrumentation (did it take path A?) or
   in Z3 (given it took path A, were the postconditions met?)

The perceptions layer is allowed to be stateful and complex. Z3 should always see simple scalars.

---

## The constraint library pattern

Don't copy constraints across persona files. Extract shared groups into `constraint_library.py`:

```python
def pipeline_invariants(P):
    """Exit code → output coherence invariants. Used by all technical personas."""
    return [
        named("pipeline/exit-0-implies-results-exist",
              Implies(P.pipeline_exit_code == 0, P.results_total >= 1)),
        named("pipeline/exit-0-implies-valid-json",
              Implies(P.pipeline_exit_code == 0, P.output_is_valid_json)),
        named("pipeline/valid-json-implies-satisfied-lte-total",
              Implies(P.output_is_valid_json, P.results_satisfied <= P.results_total)),
        named("pipeline/no-silent-success",
              Not(And(P.pipeline_exit_code == 0, P.results_total == 0))),
    ]

def timing_invariants(P, max_ms_per_result=3000, max_total_ms=60000):
    """Wall clock budget, parameterized by persona tolerance."""
    return [
        named("timing/budget-scales-with-result-count",
              Implies(P.pipeline_wall_clock_ms > 0,
                      P.pipeline_wall_clock_ms <= P.results_total * max_ms_per_result)),
        named("timing/budget-scales-with-matrix-dimensions",
              Implies(P.pipeline_wall_clock_ms > 0,
                      P.pipeline_wall_clock_ms
                      <= P.person_count * P.scenario_count * max_ms_per_result)),
        named("timing/hard-ceiling",
              Implies(P.pipeline_wall_clock_ms > 0,
                      P.pipeline_wall_clock_ms <= max_total_ms)),
        named("timing/floor-at-least-10ms-per-path",
              Implies(P.results_total >= 1,
                      P.pipeline_wall_clock_ms >= P.scenario_count * 10)),
    ]
```

**Parameterize groups when personas have different tolerances:**
- SRE: `timing_invariants(P, max_ms_per_result=2000, max_total_ms=30000)` — tight
- ML Engineer: `timing_invariants(P, max_ms_per_result=10000, max_total_ms=300000)` — generous

---

## Constraint density checklist

Before committing a persona, check:

- [ ] At least 30% of constraints touch 2+ variables
- [ ] Every `Implies` antecedent fires in at least one path (not vacuous)
- [ ] At least one constraint is unique to this persona (not shared with all others)
- [ ] No constraint always passes regardless of system state (verify by imagining a broken system)
- [ ] No constraint always fails (verify by reading actual perception values from a run)
- [ ] Constraints from different library groups present (coverage of multiple concerns)

---

## Reading constraint results

After a run, `results.json` has per-constraint outcomes:

```json
{
  "label": "timing/budget-scales-with-matrix-dimensions",
  "expr":  "If (pipeline_wall_clock_ms > 0), then (pipeline_wall_clock_ms ≤ (person_count * scenario_count * 3000))",
  "passed": true,
  "antecedent_fired": true
}
```

- `passed: false` → the constraint was violated; the system broke this rule
- `antecedent_fired: false` → the antecedent never became true in this path; vacuous pass
- `antecedent_fired: null` → no antecedent (plain assertion); always counted as fired

The `expr` field shows the human-readable Z3 formula including the actual evaluated values
of the consequent. This is what appears in the report's constraint list.

---

## Common mistakes and fixes

**Mistake: boolean perception encoding a decision**
```python
# WRONG — this is Z3's job
"pipeline_passed": int(exit_code == 0)
# RIGHT — pass the raw value
"pipeline_exit_code": exit_code
# Z3 constraint: Implies(P.pipeline_exit_code == 0, ...)
```

**Mistake: precomputed ratio**
```python
# WRONG
"results_score": satisfied / max(total, 1)
# RIGHT — let Z3 do the arithmetic
"results_satisfied": satisfied,
"results_total":     total,
# Z3 constraint: Implies(P.results_total >= 1, P.results_satisfied == P.results_total)
```

**Mistake: temporal unrolling**
```python
# WRONG — causes solver latency
"step_1_exit": 0, "step_2_exit": 0, "step_3_exit": 0
# + constraints: Implies(step_2_ran, step_1_exit == 0), etc.
# RIGHT — emit ordinal or per-step booleans from perceptions
"last_successful_step": 3,
"step_config_attempted": 1,
"step_config_exit_code": 0,
```

**Mistake: constraint that can never fire vacuously**

If a path never exercises a code path, constraints gated on that path are vacuously true.
Add a `full_integration` path that exercises every subsystem in one pass. This is the
strongest guarantee against vacuous coverage.
