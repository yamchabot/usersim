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
- Periodically — every few weeks on an active project

---

## The audit

Save this as `user_simulation/audit.py` and run it after every maintenance cycle:

```python
# audit.py
import json, re, glob
from collections import defaultdict

with open("user_simulation/results.json") as f:
    r = json.load(f)

results       = r["results"]
summary       = r["summary"]
all_persons   = sorted({x["person"]   for x in results})
all_scenarios = sorted({x["scenario"] for x in results})

print(f"\n=== usersim constraint audit ===")
print(f"Persons: {len(all_persons)}  Scenarios: {len(all_scenarios)}")
print(f"Effective tests:  {summary.get('effective_tests', '?')}")
print(f"Constraint evals: {summary.get('constraint_evals', '?')}")

# 1. Vacuous constraints
label_ever_fired = defaultdict(lambda: defaultdict(bool))
for x in results:
    for c in x.get("constraints", []):
        if c.get("antecedent_fired") is True:
            label_ever_fired[x["person"]][c["label"]] = True

print("\n--- Vacuous constraints (antecedent never fires in any scenario) ---")
seen = set()
for x in results:
    for c in x.get("constraints", []):
        if c.get("antecedent_fired") is False:
            key = (x["person"], c["label"])
            if key not in seen and not label_ever_fired[x["person"]][c["label"]]:
                seen.add(key)
                print(f"  {x['person']}: {c['label']}")
if not seen:
    print("  none ✓")

# 2. Always-passing constraints
print("\n--- Always-passing (100% pass rate -- verify they ask hard questions) ---")
label_stats = defaultdict(lambda: {"pass": 0, "total": 0})
for x in results:
    for c in x.get("constraints", []):
        if c.get("antecedent_fired") is not False:
            key = (x["person"], c["label"])
            label_stats[key]["total"] += 1
            if c.get("passed"):
                label_stats[key]["pass"] += 1

trivial = [(k, v) for k, v in label_stats.items()
           if v["total"] >= len(all_scenarios) and v["pass"] == v["total"]]
for (person, label), v in sorted(trivial)[:20]:
    print(f"  {person}: {label}  ({v['pass']}/{v['total']})")
if not trivial:
    print("  none (every constraint has at least one failure scenario)")

# 3. Constraint count per persona
print("\n--- Constraint count per persona ---")
for person in all_persons:
    pr = [x for x in results if x["person"] == person]
    counts = [len(x.get("constraints", [])) for x in pr]
    avg = sum(counts) / len(counts) if counts else 0
    print(f"  {person:<30} {int(avg):>4} constraints/scenario")

# 4. Variable density
keywords = {"If","then","And","Or","Not","Implies","True","False","else"}
density = {}
for x in results:
    for c in x.get("constraints", []):
        if c.get("antecedent_fired") is not False:
            label = c["label"]
            if label not in density:
                vs = set(t for t in re.findall(r'\b[a-z][a-z0-9_]*\b', c.get("expr",""))
                         if t not in keywords)
                density[label] = len(vs)

print("\n--- Most coverage (top 10 by variable count) ---")
for label, n in sorted(density.items(), key=lambda x: -x[1])[:10]:
    print(f"  {n} vars  {label}")
print("\n--- Least coverage (bottom 10, possible trivial checks) ---")
for label, n in sorted(density.items(), key=lambda x: x[1])[:10]:
    print(f"  {n} vars  {label}")

# 5. Dead perceptions
print("\n--- Dead perceptions (computed but never referenced in constraints) ---")
import os, sys
sys.path.insert(0, "user_simulation")
try:
    import inspect, perceptions as P_mod
    src = inspect.getsource(P_mod.compute)
    perception_keys = set(re.findall(r'"([a-z][a-z0-9_]*)"', src))
    referenced = set()
    for path in glob.glob("user_simulation/users/*.py"):
        with open(path) as f:
            for m in re.finditer(r'P\.([a-z][a-z0-9_]*)', f.read()):
                referenced.add(m.group(1))
    dead = perception_keys - referenced
    for k in sorted(dead): print(f"  {k}")
    if not dead: print("  none ✓")
except Exception as e:
    print(f"  (could not load perceptions module: {e})")
```

---

## The five constraint health problems

### 1. Vacuous constraints

The antecedent of an `Implies(...)` never becomes true in any scenario. Always passes —
but only because it was never evaluated. False confidence.

**Fix:** add or update a scenario so the antecedent fires. Add `full_integration` if missing.
Delete the constraint if no scenario will ever exercise the antecedent.

---

### 2. Trivially passing constraints

Passes in every scenario — not because the system is correct, but because the threshold is
too loose to ever fail.

**The broken-system test:** imagine the application regressed in a way a real user would
notice. Would this constraint catch it? If not, it is theater.

Examples of trivial constraints:
```python
P.wall_ms <= 999999             # always passes
P.exit_code >= -1               # trivially true
Implies(P.results_total >= 0, ...)  # antecedent always true
```

**Fix:** recalibrate. Read actual perception values and set a threshold so a 25-30% regression
causes failure. Or replace with a relationship constraint that scales automatically:
```python
# Before: absolute, trivially passes
Implies(P.wall_ms > 0, P.wall_ms <= 60000)

# After: scales with matrix size, catches proportional regressions
Implies(P.wall_ms > 0, P.wall_ms <= P.results_total * P.person_count * 3000)
```

---

### 3. Dead perceptions

A key computed in `perceptions.py` but referenced by no constraint anywhere.
The analyst is doing work nobody reads.

**Fix:** delete the perception, or add a constraint that uses it. If you added it for a
future constraint that never got written, write the constraint now or remove the perception.

---

### 4. Duplicate constraints across personas

The same logical check appears in multiple persona files under different names.

**Fix:** extract to `constraint_library.py`. Replace both inline occurrences with
`*group_function(P)`. Parameterize when personas need different tolerances.

---

### 5. Persona drift

The persona's `goal` field no longer matches what its constraints actually check.
Happens when constraints are added opportunistically without asking "does this match what
this persona cares about?"

**Fix:** re-read the goal. For each constraint ask: would this person actually care about
this? Remove what doesn't belong. Add what's missing.

---

## Calibrating thresholds

After any significant application change, print actual perception values before adjusting:

```python
# calibrate.py
import subprocess, json, os, sys
sys.path.insert(0, "user_simulation")
import perceptions as P_mod

for scenario in ["normal_run", "bad_config", "full_integration"]:
    env = {**os.environ, "USERSIM_SCENARIO": scenario}
    r = subprocess.run(["python3", "user_simulation/instrumentation.py"],
                       capture_output=True, text=True, env=env)
    if r.returncode != 0 or not r.stdout.strip():
        print(f"{scenario}: FAILED"); continue
    raw = json.loads(r.stdout)
    p = P_mod.compute(raw["metrics"], scenario=scenario)
    print(f"\n--- {scenario} ---")
    for k, v in sorted(p.items()):
        print(f"  {k}: {v}")
```

Rules:
- Threshold should fail if the metric regresses 25-30%
- If actual is always 100x below threshold, tighten it
- Prefer relationship constraints over absolute thresholds — they self-calibrate as the system grows

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
# Both persona files:
#   *exit_code_contract(P),
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

After each maintenance cycle, append a record to `user_simulation/docs/CONSTRAINT_HISTORY.md`:

```python
import json, datetime
r = json.load(open("user_simulation/results.json"))
s = r["summary"]
print(f"| {datetime.date.today()} "
      f"| {s.get('effective_tests','?'):>8} "
      f"| {s.get('constraint_evals','?'):>6} "
      f"| {s['satisfied']}/{s['total']} |")
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
