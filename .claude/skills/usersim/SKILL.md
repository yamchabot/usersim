# usersim — Setting Up a New Project

> Agent instructions for configuring usersim on any project from scratch.
> Read this entire document before touching any file.

---

## Sub-skills — read these when relevant

This skill has two companion documents. Load them when you hit the relevant phase:

**`.claude/skills/usersim/CONSTRAINTS.md`** — read when designing the Z3 judgement layer.
Covers: multi-variable constraint patterns, sequential constraint encoding (ordinal witness
vs. per-step Implies chains), the constraint library pattern, naming conventions, effective
test count, and common mistakes. If you're writing `named(...)` calls, read this first.

**`.claude/skills/usersim/web.md`** — read when the application under test runs in a browser.
Covers: `usersim-web` package, Playwright/jsdom scenario runner, DOM extraction, network
interception hooks, localStorage monitoring. Skip if the application is a CLI, API, or
non-browser system.

---

## What usersim is

usersim is a **coverage engine**. It answers: for every type of person who uses this system,
across every scenario it can be in, do the things that person cares about hold true?

The combinatorial power is Z3. A constraint like `wall_ms <= person_count * scenario_count * 3000`
isn't one test — it's a bounded domain of satisfiability. 15 personas × 6 scenarios × ~50
constraints × avg 3 variables per constraint ≈ 86,000 effective test assertions from a single run.

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
is a bad witness.

**What goes here:** exit codes, timing in ms, file counts, byte counts, parse results,
observable binary facts (file exists? yes/no — not a threshold).

**Output format:**
```json
{"schema": "usersim.metrics.v1", "scenario": "full_integration",
 "metrics": {"exit_code": 0, "wall_ms": 4230, "file_count": 4}}
```

> **Web app?** Read `.claude/skills/usersim/web.md` before implementing this layer.

**`full_integration` is not optional.** Add a scenario that runs all subsystems in one pass.
This ensures every antecedent fires with real values — no vacuous coverage.

### Layer 2 — Perceptions: the analyst

Reads raw instrumentation output. Produces a flat dict of named numeric signals for Z3.

**Contract:** rename, reshape, and compute things genuinely awkward in Z3. No thresholds.
No booleans encoding decisions. No precomputed ratios.

**The canonical anti-pattern:**
```python
# WRONG — this is a Z3 constraint disguised as a perception
"results_score": satisfied / max(total, 1)

# RIGHT — pass both values; let Z3 do the arithmetic
"results_satisfied": satisfied,
"results_total":     total,
# Z3: Implies(P.results_total >= 1, P.results_satisfied == P.results_total)
```

```python
def compute(metrics, scenario=None, person=None):
    def get(key, default=0.0):
        v = metrics.get(key, default)
        return float(v) if v is not None else default

    return {
        "pipeline_exit_code":     get("exit_code"),
        "pipeline_wall_clock_ms": get("wall_ms"),
        "results_satisfied":      get("satisfied_count"),
        "results_total":          get("total_count"),
    }
```

Return `1.0` (not `0.0`) for ratio perceptions when neither input was measured.
A missing measurement is not evidence of failure.

**Sequential data:** if your system has multi-step sequences, perceptions should run a
state machine over the trace and emit ordinal summary scalars — not expose raw per-step
state to Z3. See `CONSTRAINTS.md` for the full sequential encoding patterns.

### Layer 3 — Z3 judgement: the ruling

Every boolean claim lives here. Exclusively.

> **Read `.claude/skills/usersim/CONSTRAINTS.md` before writing constraints.**
> It covers multi-variable patterns, sequential encoding, the constraint library,
> naming conventions, and common mistakes in depth.

Quick reference:

```python
from usersim.judgement.z3_compat import Implies, And, Not, named

# Conditional: "if A then B"
named("pipeline/exit-0-implies-valid-json",
      Implies(P.pipeline_exit_code == 0, P.output_is_valid_json))

# Multi-variable: "budget scales with matrix dimensions" (3 variables = 64 combos)
named("timing/budget-scales-with-matrix",
      Implies(P.pipeline_wall_clock_ms > 0,
              P.pipeline_wall_clock_ms <= P.person_count * P.scenario_count * 3000))

# Structural invariant: "this combination must never occur"
named("pipeline/no-silent-success",
      Not(And(P.pipeline_exit_code == 0, P.results_total == 0)))
```

---

## Personas

### Each persona must earn its place

A persona is useful only if it brings constraints that no other persona has.
If two personas produce identical Z3 constraints, they're the same persona.

### Diversity coverage

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

Don't copy constraints across persona files. Extract shared groups into `constraint_library.py`
and compose them. Parameterize groups when personas have different tolerances:

```python
*timing_invariants(P, max_ms_per_result=2000)   # SRE: tight
*timing_invariants(P, max_ms_per_result=10000)  # ML Engineer: generous
```

See `CONSTRAINTS.md` for a full worked example of the library pattern.

---

## Scenarios

Scenarios are *contexts*, not test cases. Each puts the system in a specific situation.

**Required scenarios:**
- A normal success case (system works, all subsystems run)
- An error/failure case (broken config, bad input — verify clean failure)
- `full_integration` — runs all subsystems in sequence — ensures all antecedents fire

**Signs of a bad scenario:** two scenarios with identical perceptions; many vacuous antecedents.

**Signs of a good scenario:** zero `antecedent_fired: false`; perceptions differ across scenarios.

**usersim.yaml:**
```yaml
version: 1

instrumentation: "python3 instrumentation.py"
perceptions: perceptions.py

users:
  - users/*.py

scenarios:
  - name: normal_run
    description: "Full pipeline on example input"
  - name: bad_config
    description: "Broken config — verify clean non-zero exit"
  - name: full_integration
    description: "All subsystems in one pass — no vacuous antecedents"

output:
  results: results.json
  report:  report.html
```

---

## Running and checking

```bash
# Full run
usersim run --config usersim.yaml

# Report only
usersim report --results results.json --out report.html

# Check for vacuous constraints (should be 0 on full_integration)
python3 -c "
import json
r = json.load(open('results.json'))
vac = [(x['person'], x['scenario'], c['label'])
       for x in r['results']
       for c in x.get('constraints', [])
       if c.get('antecedent_fired') is False]
print(f'{len(vac)} vacuous')
for p,s,l in vac[:20]: print(f'  {p}/{s}: {l}')
"

# Check effective test count
python3 -c "import json; print(json.load(open('results.json'))['summary'])"
```

---

## File structure

```
my-project/
  src/                       ← the application
  user_simulation/
    users/
      persona_one.py
      persona_two.py
    constraint_library.py    ← shared constraint groups
    instrumentation.py       ← scenario runner (or collect.js for web)
    perceptions.py           ← signal computation
    results.json             ← gitignore
    report.html              ← gitignore
  usersim.yaml
```

---

## Principles

**Stay in your lane.** Instrumentation witnesses. Perceptions interprets. Z3 decides.

**Thin perceptions, fat Z3.** If Z3 can express it as an arithmetic relationship, do that
instead of pre-computing it in perceptions.

**Multi-variable constraints are the goal.** Single-variable threshold checks are the floor.
Aim for at least a third of constraints touching 2+ variables.

**Name every constraint.** `named("group/check-name", expr)` — unnamed constraints are
invisible in the report.

**Calibrate before you commit.** Run a scenario, read the raw perceptions, then set thresholds.
A constraint that always passes or always fails provides zero signal.

**`full_integration` is mandatory.** The only guarantee against vacuous coverage.

**Diverse personas produce diverse constraints.** If two personas have nearly identical
constraint sets, one of them is not doing useful work.
