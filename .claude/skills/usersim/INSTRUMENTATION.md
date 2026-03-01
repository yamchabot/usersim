# usersim — Instrumentation Layer

Read this when implementing Layer 1 (the witness) for a project.
This is a sub-skill of `.claude/skills/usersim/SKILL.md` — read that first.

> **Web app?** Read `.claude/skills/usersim/web.md` instead of this file.
> It provides a ready-made scenario runner and page automation API.

---

## Contract

Instrumentation is the witness. It connects to the application and records what happened.

**What goes here:** exit codes, timing in ms, file counts, byte counts, parse results,
binary observable facts (file exists, output is parseable, request was made).

**What does NOT go here:** thresholds, ratios, computed scores, boolean decisions.
The moment you write `"passed": exit_code == 0`, you've made a judgement that belongs in Z3.

A useful test: *could a camera extract this from the output?* If yes, it belongs here.
If it requires reasoning about what the number means, it belongs in perceptions or Z3.

---

## Output format

Each scenario run must print exactly one JSON object to stdout:

```json
{
  "schema":   "usersim.metrics.v1",
  "scenario": "normal_run",
  "metrics":  {
    "exit_code":    0,
    "wall_ms":      4230,
    "file_count":   4,
    "output_bytes": 18432
  }
}
```

No other output on stdout. Errors and diagnostics go to stderr.

---

## Implementation template

```python
# instrumentation.py
import sys, os, subprocess, json, time, tempfile, shutil

SCENARIO = os.environ.get("USERSIM_SCENARIO", "normal_run")


def emit(scenario, metrics):
    print(json.dumps({
        "schema":   "usersim.metrics.v1",
        "scenario": scenario,
        "metrics":  metrics,
    }))


def run_normal():
    """Full pipeline on known-good input."""
    t0 = time.time()
    result = subprocess.run(
        ["your-tool", "run", "--config", "examples/good.yaml"],
        capture_output=True, text=True
    )
    wall_ms = int((time.time() - t0) * 1000)

    try:
        output = json.loads(result.stdout)
        valid_json = 1
    except Exception:
        output = {}
        valid_json = 0

    return {
        "exit_code":      result.returncode,
        "wall_ms":        wall_ms,
        "valid_json":     valid_json,
        "result_count":   len(output.get("results", [])),
        "stderr_bytes":   len(result.stderr),
    }


def run_bad_config():
    """Broken config — verify clean non-zero exit."""
    result = subprocess.run(
        ["your-tool", "run", "--config", "/nonexistent/path.yaml"],
        capture_output=True, text=True
    )
    return {
        "exit_code":         result.returncode,
        "stderr_bytes":      len(result.stderr),
        "stdout_bytes":      len(result.stdout),
        "stderr_has_output": int(len(result.stderr) > 0),
        "stdout_has_output": int(len(result.stdout) > 0),
    }


def run_full_integration():
    """All subsystems in one pass. Must exercise every code path."""
    # Run each subsystem in sequence, recording each exit code
    results = {}

    # Step 1: init
    r1 = subprocess.run(["your-tool", "init", "--dir", "/tmp/sim-test"],
                        capture_output=True, text=True)
    results["init_exit_code"]   = r1.returncode
    results["init_stderr_bytes"] = len(r1.stderr)

    # Step 2: main run
    t0 = time.time()
    r2 = subprocess.run(["your-tool", "run", "--config", "examples/good.yaml"],
                        capture_output=True, text=True)
    results["pipeline_exit_code"]      = r2.returncode
    results["pipeline_wall_clock_ms"]  = int((time.time() - t0) * 1000)

    try:
        out = json.loads(r2.stdout)
        results["output_is_valid_json"]  = 1
        results["results_total"]         = len(out.get("results", []))
        results["results_satisfied"]     = sum(1 for r in out.get("results", []) if r.get("satisfied"))
    except Exception:
        results["output_is_valid_json"]  = 0
        results["results_total"]         = 0
        results["results_satisfied"]     = 0

    # Step 3: error cases (exercise denial paths)
    r3 = subprocess.run(["your-tool", "run", "--config", "/bad"],
                        capture_output=True, text=True)
    results["bad_config_exit_code"] = r3.returncode

    return results


SCENARIOS = {
    "normal_run":       run_normal,
    "bad_config":       run_bad_config,
    "full_integration": run_full_integration,
}

if __name__ == "__main__":
    fn = SCENARIOS.get(SCENARIO)
    if not fn:
        print(f"Unknown scenario: {SCENARIO}", file=sys.stderr)
        sys.exit(1)
    emit(SCENARIO, fn())
```

---

## Scenario design

### What makes a good scenario

- **Exercises distinct code paths** — scenarios that produce identical metrics are redundant
- **Zero or near-zero vacuous antecedents** — every perception used by a constraint is populated
- **Isolated** — scenarios don't share state; each starts from a clean environment
- **Fast** — instrumentation should complete in seconds, not minutes

### Required scenarios for every project

| Scenario | Purpose |
|----------|---------|
| A normal success case | Proves the happy path works end-to-end |
| An error/failure case | Proves the system fails cleanly and non-zero |
| `full_integration` | Exercises *all* subsystems — prevents vacuous constraints |

### `full_integration` is mandatory

This is the most important scenario. It is the only way to guarantee no constraint ever
fires vacuously (antecedent never triggered = constraint never tested = false confidence).

`full_integration` should:
- Run every subsystem the perceptions layer measures
- Exercise both success and failure paths within the same scenario
- Populate every perception variable that any persona constraint references

A `full_integration` that leaves 20 perceptions at their default value is not doing its job.
Check after writing it:

```bash
python3 -c "
import json
r = json.load(open('results.json'))
fi = [x for x in r['results'] if x['scenario'] == 'full_integration']
vac = [c['label'] for x in fi for c in x.get('constraints',[])
       if c.get('antecedent_fired') is False]
print(f'{len(vac)} vacuous in full_integration')
for l in vac[:10]: print(f'  {l}')
"
```

### Signs of a bad scenario

- Two scenarios that produce identical perceptions → merge them
- Many `antecedent_fired: false` → scenario doesn't exercise the system
- Scenario depends on previous scenario's output → make it independent

---

## Testing scenarios individually

Always test each scenario in isolation before running the full suite:

```bash
USERSIM_SCENARIO=normal_run      python3 instrumentation.py
USERSIM_SCENARIO=bad_config      python3 instrumentation.py
USERSIM_SCENARIO=full_integration python3 instrumentation.py
```

Each should:
1. Print valid JSON to stdout
2. Print nothing else to stdout (errors → stderr)
3. Exit 0

If a scenario prints invalid JSON or errors on stdout, the perceptions layer will receive
bad data silently. Fix it before moving to perceptions.

---

## Measuring timing correctly

Always measure wall clock time around the subprocess call, not inside it:

```python
t0 = time.time()
result = subprocess.run([...], capture_output=True, text=True)
wall_ms = int((time.time() - t0) * 1000)
```

Include the wall_ms in every scenario that runs the main pipeline. The timing constraints
in Z3 (`wall_ms <= person_count * scenario_count * 3000`) only work if the metric exists.

---

## What NOT to measure

- Don't measure things you can't observe — if you have to guess, don't include it
- Don't measure intermediate state that the application doesn't expose
- Don't include the same measurement under two different names
- Don't compute ratios (`satisfied / total`) — record both components separately
