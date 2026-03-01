# usersim — Setting Up a New Project

> Agent instructions for configuring usersim on any project from scratch.
> Read this entire document before touching any file.

---

## What usersim is

usersim is a **coverage engine**. It answers: for every type of person who uses this system,
across every scenario it can be in, do the things that person cares about hold true?

The combinatorial power is Z3. A constraint like `wall_ms <= person_count * scenario_count * 3000`
isn't one test — it's a bounded domain of satisfiability covering every combination of those
variables within their observed ranges. 15 personas × 6 scenarios × ~50 constraints × avg 3
variables per constraint ≈ 86,000 effective test assertions from a single run.

This is the point. Not test count. **Coverage of relationships.**

---

## The pipeline

Three layers. Each has a strict job. A layer that does another layer's job produces results
that are harder to inspect, harder to debug, and harder to trust.

```
instrumentation  →  perceptions  →  Z3 judgement
  (witness)          (analyst)        (ruling)
```

### Layer 1 — Instrumentation: the witness

Runs the system. Records everything it observes. Outputs a flat JSON dict per scenario.

**Contract:** no arithmetic, no thresholds, no interpretation. A witness who draws conclusions
is a bad witness. If you find yourself writing `"passed": true`, stop — that's a judgement.

**What goes here:** exit codes, timing in ms, file counts, byte counts, parse results, booleans
for observable binary facts (file exists? yes/no — not a threshold).

**Output format:**
```json
{"schema": "usersim.metrics.v1", "scenario": "full_integration",
 "metrics": {"exit_code": 0, "wall_ms": 4230, "file_count": 4}}
```

**`full_integration` is not optional.** Add a scenario that runs all subsystems in one pass.
This ensures every antecedent fires with real values — no vacuous coverage.

### Layer 2 — Perceptions: the analyst

Reads raw instrumentation output. Produces a flat dict of named numeric signals.

**Contract:** rename, reshape, and compute things that are genuinely awkward in Z3. That's it.
No thresholds. No booleans that encode decisions. No precomputed ratios unless Z3 truly can't
do the arithmetic.

**The canonical anti-pattern:**
```python
# WRONG — this is a Z3 constraint disguised as a perception
"results_score": satisfied / max(total, 1)

# RIGHT — pass both values; let Z3 do the arithmetic
"results_satisfied": satisfied,
"results_total":     total,
# Z3 constraint: P.results_satisfied == P.results_total
```

**What's allowed:** pass-throughs, sums of related counts, arithmetic Z3 can't easily express.
**What's not allowed:** booleans encoding thresholds, precomputed ratios, varying return types.

```python
def compute(metrics, scenario=None, person=None):
    def get(key, default=0.0):
        v = metrics.get(key, default)
        return float(v) if v is not None else default

    return {
        "pipeline_exit_code":      get("exit_code"),
        "pipeline_wall_clock_ms":  get("wall_ms"),
        "results_satisfied":       get("satisfied_count"),
        "results_total":           get("total_count"),
        # ...
    }
```

Return `1.0` (not `0.0`) for ratio perceptions when neither input was measured in the current
scenario. A missing measurement is not evidence of failure.

### Layer 3 — Z3 judgement: the ruling

Every boolean claim lives here. Exclusively.

**Multi-variable constraints are the goal**, not single-variable threshold checks:

| Variables | Example | Value |
|-----------|---------|-------|
| 1 | `P.exit_code == 0` | floor |
| 2 | `P.wall_ms <= P.results_total * 3000` | good |
| 3 | `P.wall_ms <= P.person_count * P.scenario_count * 3000` | better |
| 4+ | `P.report_bytes >= P.results_total * P.person_count * 80` | excellent |

Multi-variable constraints test *relationships*. Changing any input automatically re-evaluates
the constraint with the new combination.

**Always use `named()`:**
```python
from usersim.judgement.z3_compat import Implies, And, Not, named

named("pipeline/exit-0-implies-valid-json",
      Implies(P.pipeline_exit_code == 0, P.output_is_valid_json))
```

Naming convention: `group/check-name`. The group appears in the report's Group × Scenario matrix.
Unnamed constraints are invisible in the report.

**Vacuous antecedents are wasted coverage.** After every run, check:
```bash
python3 -c "
import json
with open('results.json') as f: r = json.load(f)
vac = [(res['person'],res['scenario'],c['label'])
       for res in r['results']
       for c in res.get('constraints',[])
       if c.get('antecedent_fired') is False]
print(f'{len(vac)} vacuous'); [print(f'  {p}/{s}: {l}') for p,s,l in vac[:20]]
"
```
If a constraint's antecedent never fires, add a scenario that exercises it.

---

## Personas

### Each persona must earn its place

A persona is useful only if it brings constraints that no other persona has. Before writing a
new persona, ask: *what would this person check that the existing personas don't?*

If two personas produce identical Z3 constraints, they're the same persona. Rename or delete.

### Diversity coverage

At minimum, cover these perspectives:

| Concern | Example persona | What they add |
|---------|----------------|---------------|
| Operational | SRE, DevOps | Timing SLOs, exit-code contracts, artifact production |
| Correctness | QA, Researcher | Coverage completeness, soundness, schema stability |
| Safety | Security, Compliance | Denial paths, no stdout leakage, audit trail |
| Experience | DevEx, TechWriter | Onboarding, self-contained output, readable errors |
| Outcome | PM, ML Engineer | Story satisfaction, behavioral contracts, pass rates |
| Extension | OSS Contributor | Non-regression, YAML parseability, extension surface |

### Persona template

```python
from usersim import Person
from usersim.judgement.z3_compat import Implies, And, Not, named
from constraint_library import pipeline_invariants, timing_invariants

class MyPersona(Person):
    name    = "my_persona"
    role    = "Short role description"
    goal    = "one sentence: what this person needs the system to do"
    pronoun = "they"

    def constraints(self, P):
        return [
            *pipeline_invariants(P),
            *timing_invariants(P, max_ms_per_result=2000),
            named("my-persona/specific-check",
                  Implies(P.something >= 1, P.other_thing == 0)),
        ]
```

---

## The constraint library

Don't copy constraints across persona files. Extract shared groups into a library.

```python
# constraint_library.py
def pipeline_invariants(P):
    """Exit code → output coherence invariants."""
    return [
        named("pipeline/exit-0-implies-valid-json",
              Implies(P.pipeline_exit_code == 0, P.output_is_valid_json)),
        named("pipeline/valid-json-implies-satisfied-lte-total",
              Implies(P.output_is_valid_json,
                      P.results_satisfied <= P.results_total)),
    ]

def timing_invariants(P, max_ms_per_result=3000, max_total_ms=60000):
    """Wall clock budget, parameterized by tolerance."""
    return [
        named("timing/budget-scales-with-result-count",
              Implies(P.pipeline_wall_clock_ms > 0,
                      P.pipeline_wall_clock_ms <= P.results_total * max_ms_per_result)),
        named("timing/hard-ceiling",
              Implies(P.pipeline_wall_clock_ms > 0,
                      P.pipeline_wall_clock_ms <= max_total_ms)),
    ]
```

Parameterize groups when personas have different tolerances. `timing_invariants(P, max_ms_per_result=2000)`
gives SRE tighter constraints than `timing_invariants(P, max_ms_per_result=10000)` for ML Engineer.

---

## Scenarios

Scenarios are *contexts*, not test cases. Each one puts the system in a specific situation.

**Required scenarios:**
- A normal success case (system works, all subsystems run)
- An error/failure case (broken config, bad input — verify clean failure)
- `full_integration` — runs all subsystems in sequence — ensures all antecedents fire

**Signs of a bad scenario:**
- Two scenarios with identical perceptions → merge them
- Many constraints fire vacuously → scenario isn't exercising the system

**Signs of a good scenario:**
- Zero or near-zero `antecedent_fired: false` on a full run
- Perceptions differ meaningfully across scenarios
- Some constraints pass in this scenario that would fail if the system were broken

**usersim.yaml:**
```yaml
version: 1

instrumentation: "python3 instrumentation.py"
perceptions: perceptions.py

users:
  - users/*.py

scenarios:
  - name: normal_run
    description: "Full pipeline on example input — verifies end-to-end output"
  - name: bad_config
    description: "Broken config — verify clean non-zero exit"
  - name: full_integration
    description: "All subsystems in one pass — no vacuous antecedents"

output:
  results: results.json
  report:  report.html
```

---

## Instrumentation implementation

```python
# instrumentation.py
import sys, os, subprocess, json, time

SCENARIO = os.environ.get("USERSIM_SCENARIO", "normal_run")

def run_scenario(name):
    if name == "normal_run":
        return run_normal()
    elif name == "bad_config":
        return run_bad_config()
    elif name == "full_integration":
        return run_full_integration()
    else:
        raise ValueError(f"Unknown scenario: {name}")

def emit(scenario, metrics):
    print(json.dumps({"schema": "usersim.metrics.v1",
                      "scenario": scenario, "metrics": metrics}))

if __name__ == "__main__":
    emit(SCENARIO, run_scenario(SCENARIO))
```

Each scenario function returns a flat dict of raw measurements. Keep each scenario function
independent — don't share state between them.

---

## The effective test count

```
effective_tests = sum(4^k  for each constraint, k = distinct Z3 variables)
```

4 is a conservative domain size (covers: 0, 1, many, max). A constraint with 3 variables
covers 64 combinations. A suite with 3,672 evaluations and avg 3 variables ≈ **86,000 effective tests**.

The report header shows this number. It's the honest way to count coverage when using Z3.

---

## Running

```bash
# Full run
usersim run --config usersim.yaml

# Report only (from existing results)
usersim report --results results.json --out report.html

# Check effective test count
python3 -c "import json; r=json.load(open('results.json')); print(r['summary'])"
```

All checks should pass before committing. If any fail:
1. Print the raw perceptions for the failing scenario to verify the instrumentation is correct
2. Check whether the threshold in the constraint is calibrated to actual values
3. Check whether the antecedent was actually exercised in this scenario

---

## File structure

```
my-project/
  src/                       ← the application
  user_simulation/           ← (or wherever you put it)
    users/
      persona_one.py
      persona_two.py
      ...
    constraint_library.py    ← shared constraint groups
    instrumentation.py       ← scenario runner
    perceptions.py           ← signal computation
    results.json             ← gitignore
    report.html              ← gitignore
  usersim.yaml
```

---

## Web/browser applications

If the application runs in a browser, instrumentation works differently: DOM queries, network
interception, storage reads, timing APIs.

For internal state not visible from outside (React component state, canvas renderer inputs),
the application registers hooks:
```js
window.__usersim?.emit('event_name', { ...data });
window.__usersim?.register('metric_name', () => store.someValue);
```

Instrumentation reads these at collection time. Hooks should be one line per data point —
do not put logic in them.

---

## Principles

**Stay in your lane.** Instrumentation witnesses. Perceptions interprets. Z3 decides. A layer
that does another's job produces results that are harder to inspect, harder to debug, and
harder to trust.

**Thin perceptions, fat Z3.** If you can express it as a Z3 arithmetic relationship, do that
instead of computing it in perceptions. `P.satisfied == P.total` is better than
`perceptions["score"] = satisfied/total` + `P.score == 1.0`.

**Multi-variable constraints are the goal.** Single-variable threshold checks are the floor.
The value of Z3 is relationships: `A <= B * C * K`. That single constraint covers the entire
space of (A, B, C) combinations.

**Name every constraint.** `named("group/check-name", expr)`. The name appears in the report
matrix, in failure output, and in the Group × Scenario coverage graph.

**Calibrate before you commit.** Run a scenario, read the raw perceptions, then set thresholds.
A constraint that always passes or always fails provides zero signal.

**`full_integration` is mandatory.** It's the only way to guarantee no constraint ever fires
vacuously. A vacuous constraint is not a test — it's a confidence trap.

**People first, metrics second.** The constraint system should feel like a natural expression
of what a real person would care about. If a constraint wouldn't make sense to the persona
you're writing it for, delete it.

**Diverse personas produce diverse constraints.** If two personas have nearly identical
constraint sets, one of them is not doing useful work. Return to persona design.
