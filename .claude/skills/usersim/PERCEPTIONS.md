# usersim — Perceptions Layer

Read this when implementing Layer 2 (the analyst) for a project.
This is a sub-skill of `.claude/skills/usersim/SKILL.md` — read that first.

---

## Contract

Perceptions is the analyst. It reads the raw witness record (instrumentation output) and
compresses it into meaningful signals that Z3 can reason about.

**What goes here:**
- Renaming metrics to clearer names
- Sums of related counts
- Derived quantities genuinely awkward to express in Z3 (rare)

**What does NOT go here:**
- Thresholds (`is_fast: wall_ms < 1000`) — that's Z3's job
- Booleans encoding decisions (`pipeline_passed: exit_code == 0`) — that's Z3's job
- Precomputed ratios that Z3 should compute — the canonical anti-pattern

---

## The canonical anti-pattern

```python
# WRONG — precomputed ratio, Z3's job stolen
"results_score": satisfied / max(total, 1)

# RIGHT — pass both values, let Z3 do the arithmetic
"results_satisfied": satisfied,
"results_total":     total,
```

The Z3 constraint then becomes:
```python
Implies(P.results_total >= 1, P.results_satisfied == P.results_total)
```

This is better because:
- Z3 reasons about the *relationship* between two quantities across all observed combos
- The constraint is transparent in the report (the formula shows what's being checked)
- Adding paths automatically re-evaluates the relationship with new values

Any time you write a division or a boolean comparison in perceptions, ask: *can Z3 express
this relationship directly from the two raw values?* If yes, pass both raw values instead.

---

## What's allowed

```python
# Pass-through: relay a metric under a clearer name
"pipeline_exit_code":      get("exit_code"),

# Sum: combine related counts into one signal
"total_error_bytes":       get("stderr_bytes") + get("stdout_error_bytes"),

# Availability guard: handle missing metrics cleanly
"scaffold_file_count":     get("file_count", default=-1),
# -1 signals "not measured in this path"; Z3 constraint gates on >= 0
```

---

## Implementation template

```python
# perceptions.py

def compute(metrics, path=None, person=None):
    """
    Transform raw instrumentation metrics into Z3-ready signals.

    Args:
        metrics:  flat dict from instrumentation output
        path: path name (available for conditional logic if truly needed)
        person:   persona name (rarely needed)

    Returns:
        flat dict of numeric values (int or float)
    """
    def get(key, default=0.0):
        v = metrics.get(key, default)
        return float(v) if v is not None else float(default)

    return {
        # Pipeline
        "pipeline_exit_code":      get("exit_code"),
        "pipeline_wall_clock_ms":  get("wall_ms"),

        # Results
        "results_satisfied":       get("satisfied_count"),
        "results_total":           get("total_count"),
        "person_count":            get("person_count"),
        "scenario_count":          get("scenario_count"),

        # Output validation
        "output_is_valid_json":    get("valid_json"),
        "schema_is_correct":       get("schema_correct"),

        # Error paths (use -1 as sentinel: "not observed in this path")
        "bad_config_exit_code":    get("bad_config_exit_code", default=-1),
        "missing_users_exit_code": get("missing_users_exit_code", default=-1),

        # Scaffold
        "init_exit_code":          get("init_exit_code", default=-1),
        "scaffold_file_count":     get("file_count", default=-1),

        # Report
        "report_exit_code":        get("report_exit_code", default=-1),
        "report_file_created":     get("report_created"),
        "report_file_size_bytes":  get("report_bytes"),
    }
```

---

## Sentinel values for unobserved metrics

When a metric is only measured in some paths (e.g., `bad_config_exit_code` is only
populated in error paths), use `-1` as the sentinel and gate Z3 constraints on `>= 0`:

```python
# perceptions.py
"bad_config_exit_code": get("bad_config_exit_code", default=-1),

# constraint_library.py — only fires when the path measured it
named("errors/bad-config-exits-1",
      Implies(P.bad_config_exit_code >= 0, P.bad_config_exit_code == 1))
```

This pattern prevents vacuous constraints without requiring every path to measure
every metric. The `full_integration` path should populate all sentinels.

Do **not** use `0` as a sentinel — `0` is a valid exit code (success). `-1` is unambiguous.

---

## Sequential data

If your system has multi-step sequences, perceptions should absorb the sequential complexity
and emit ordinal summary scalars — **not** expose raw per-step state to Z3.

```python
# WRONG — expose raw sequence to Z3
"step_1_exit": get("step_1_exit"),
"step_2_exit": get("step_2_exit"),
"step_3_exit": get("step_3_exit"),
# (leads to Z3 temporal unrolling → solver latency)

# RIGHT — collapse sequence into ordinal witness
trace = [
    get("init_exit_code"),
    get("config_exit_code"),
    get("run_exit_code"),
    get("report_exit_code"),
]
last_successful = -1
phase_skipped   = 0
for i, code in enumerate(trace):
    if code < 0:   # not measured (sentinel)
        continue
    if code == 0:
        if last_successful >= 0 and i > last_successful + 1:
            phase_skipped = 1  # gap in successful phases
        last_successful = i
    else:
        break      # first failure

return {
    ...
    "last_successful_phase": last_successful,  # -1, 0, 1, 2, or 3
    "phase_skipped":         phase_skipped,
}
```

Z3 then reasons about `P.last_successful_phase >= 2` — did we get far enough?
One integer variable, no temporal logic in the solver.

See `CONSTRAINTS.md` for the full sequential constraint patterns.

---

## Return value conventions

| Type | Convention | Example |
|------|-----------|---------|
| Exit code | Raw integer | `0`, `1`, `-1` (sentinel) |
| Timing | Milliseconds as float | `4230.0` |
| Count | Non-negative integer | `4`, `0` |
| Boolean fact | `1` or `0` (not Python bool) | `1` if exists else `0` |
| Unobserved metric | `-1` sentinel | `-1` |
| Ratio/score | **Don't use** | Pass numerator + denominator instead |

Always return `float` or `int` — never `bool`, `None`, or `str`. The Z3 backend expects numeric types.

---

## Naming conventions

Use the perception name as the Z3 attribute name. Names should describe the signal,
not encode a judgement:

```python
# GOOD — describes what was observed
"pipeline_exit_code"      # the exit code of the pipeline
"report_file_size_bytes"  # size of the output file
"scaffold_file_count"     # number of files created by init

# BAD — encodes a decision (belongs in Z3)
"pipeline_succeeded"      # boolean judgement
"report_is_large_enough"  # threshold comparison
"init_worked"             # opinion
```

---

## Checking your perceptions

Before writing any Z3 constraints, print the actual perception values for each path:

```python
# quick_check.py
import subprocess, json, sys
sys.path.insert(0, '.')
import perceptions

for path in ["normal_run", "bad_config", "full_integration"]:
    result = subprocess.run(
        ["python3", "instrumentation.py"],
        env={**__import__('os').environ, "USERSIM_PATH": path},
        capture_output=True, text=True
    )
    raw = json.loads(result.stdout)
    p = perceptions.compute(raw["metrics"], path=path)
    print(f"\n--- {path} ---")
    for k, v in sorted(p.items()):
        print(f"  {k}: {v}")
```

Read these values before setting any Z3 thresholds. A constraint that always passes or
always fails provides zero signal. The perception values tell you what thresholds are
achievable and meaningful.
