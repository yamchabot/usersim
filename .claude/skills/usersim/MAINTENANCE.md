# usersim — Iterative Constraint System Maintenance

Read this when reviewing, improving, or refactoring an existing constraint system.
This is a sub-skill of `.claude/skills/usersim/SKILL.md`.

The constraint system you ship on day one is not the constraint system you want on day thirty.
New code paths appear. Performance changes. Personas drift from their original goals. Constraints
that once asked hard questions now pass trivially. This skill is about keeping the system honest.

---

## When to run a maintenance cycle

- After any significant change to the application (new features, refactors, performance work)
- When effective test count drops between runs without an obvious reason
- When all personas pass 100% for many consecutive runs with no failures ever caught
- When adding a new persona and you suspect it duplicates existing coverage
- When a constraint fails and you don't understand why
- Periodically every few weeks on an active project

---

## The audit

```bash
usersim audit
```

Run this after every maintenance cycle. It runs the test suite, then analyses the results.
Detects all five health problems in one pass and exits 1 if vacuous constraints are found
(safe to add to CI).

To skip re-running tests and audit an existing results file:

```bash
usersim audit --results user_simulation/results.json
```

Pass `--config` to enable dead perceptions detection (usersim needs to locate perceptions.py):

```bash
usersim audit --config usersim.yaml
```

Output as JSON for scripting or historical tracking:

```bash
usersim audit --json
```

---

## The five constraint health problems

### 1. Vacuous constraints

The antecedent of an `Implies(...)` never becomes true in any scenario. Always passes --
but only because it was never evaluated. False confidence.

`usersim audit` flags these. Fix: add or update a scenario so the antecedent fires.
The `full_integration` scenario is designed to prevent this -- make sure it runs all
subsystems and exercises every antecedent. Delete constraints whose antecedent can never
fire in any scenario.

---

### 2. Trivially passing constraints

Passes in every scenario -- not because the system is correct, but because the threshold is
too loose to ever fail.

**The broken-system test:** imagine the application regressed in a way a real user would
notice. Would this constraint catch it? If not, it is theater.

`usersim audit` lists all 100%-passing constraints. Inspect each one:

```python
# Trivial: always passes regardless of actual value
P.wall_ms <= 999999

# Trivial: antecedent always true
Implies(P.results_total >= 0, P.results_satisfied >= 0)

# Better: scales with matrix size, catches proportional regressions
Implies(P.wall_ms > 0, P.wall_ms <= P.results_total * P.person_count * 3000)
```

---

### 3. Dead perceptions

A key computed in `perceptions.py` but referenced by no constraint anywhere.

`usersim audit --config usersim.yaml` flags these. Fix: delete the perception, or write
the constraint that was missing. Check the planning docs (METRICS.md, PERCEPTION_PLAN.md) --
if the key was never in the plan either, delete it.

---

### 4. Duplicate constraints across personas

The same logical check appears in multiple persona files under different names.

`usersim audit` surfaces this through the variable density report: identical `expr` patterns
across different persona/label pairs. Fix: extract to `constraint_library.py` and replace
both inline occurrences with `*group_function(P)`.

---

### 5. Persona drift

The persona's `goal` field no longer matches what its constraints actually check.
Happens when constraints are added opportunistically.

No automated detection. Fix: re-read the goal. For each constraint ask: would this person
actually care about this? Remove what does not belong. Add what is missing.

---

## Calibrating thresholds

After any significant application change, print actual perception values before adjusting:

```bash
usersim calibrate                         # all scenarios
usersim calibrate --scenario full_integration  # one scenario
```

Rules:
- Threshold should fail if the metric regresses 25-30%
- If actual is always 100x below threshold, tighten it
- Prefer relationship constraints over absolute thresholds -- they self-calibrate as the
  system grows: `P.wall_ms <= P.results_total * P.person_count * 3000`

---

## Refactoring patterns

### Extract to library
```python
# Before: same logic in two persona files
named("ci/pipeline-exits-0", Implies(P.pipeline_exit_code >= 0, P.pipeline_exit_code == 0))
named("devops/pipeline-exits-0", Implies(P.pipeline_exit_code >= 0, P.pipeline_exit_code == 0))

# After: constraint_library.py
def exit_code_contract(P):
    return [named("pipeline/must-exit-0",
                  Implies(P.pipeline_exit_code >= 0, P.pipeline_exit_code == 0))]
# Both persona files: *exit_code_contract(P),
```

### Condition a vacuous constraint
```python
# Before: metric is -1 sentinel in most scenarios -- always vacuous
named("errors/bad-config-exits-1", P.bad_config_exit_code == 1)

# After: only fires when the metric was actually observed
named("errors/bad-config-exits-1",
      Implies(P.bad_config_exit_code >= 0, P.bad_config_exit_code == 1))
```

### Upgrade single-variable to relationship
```python
# Before: 4 effective tests
named("report/size-ok", Implies(P.report_file_created, P.report_bytes >= 5000))

# After: 64 effective tests, catches proportional regressions
named("report/size-scales-with-matrix",
      Implies(And(P.report_file_created, P.results_total >= 1),
              P.report_bytes >= P.results_total * P.person_count * 80))
```

### Tighten a trivial threshold
```python
# Before: actual ~200ms, ceiling 999999 -- catches nothing
named("timing/ceiling", Implies(P.wall_ms > 0, P.wall_ms <= 999999))

# After: actual ~200ms, ceiling at 3x headroom -- catches 2x+ regressions
named("timing/ceiling", Implies(P.wall_ms > 0, P.wall_ms <= 600))
```

---

## Adding a new persona to an existing system

Before writing a new persona:

1. List what constraint groups exist across all current personas -- what is already covered?
2. Identify the missing concern dimension (see SKILL.md diversity table)
3. Write the goal first -- one sentence, from the person's perspective
4. Draft constraints against the goal -- does each one match the goal?
5. Check uniqueness -- does any existing persona already have this constraint?
6. Run and verify -- zero vacuous antecedents on `full_integration`

A persona that only adds library constraints adds zero coverage. Its value comes entirely
from its persona-specific constraints.

---

## Tracking health over time

Append a record after each maintenance cycle:

```bash
usersim audit --json | python3 -c "
import json, sys, datetime
d = json.load(sys.stdin)['summary']
print(f'| {datetime.date.today()} | {d[\"effective_tests\"]:>8} | {d[\"constraint_evals\"]:>6} | {d[\"satisfied\"]}/{d[\"total\"]} | {d[\"vacuous_count\"]} vacuous |')
" >> user_simulation/docs/CONSTRAINT_HISTORY.md
```

A healthy system: effective tests growing, vacuous count zero, occasional failures caught.
A degrading system: effective tests flat, vacuous count creeping up, 100% pass forever.

---

## The fundamental question

After any maintenance cycle, ask: **if this system regressed in a way that would hurt a
real user, would any constraint catch it?**

Walk through each persona. Imagine their specific frustration. Trace it back to a perception.
Check whether any constraint references that perception with a threshold tight enough to fail.

If the answer is no -- a real user would be hurt and all constraints would still pass -- that
is the gap to close. Not by adding constraints at random, but by adding the one constraint
that catches that specific failure mode.

That is how constraint systems get better over time.
