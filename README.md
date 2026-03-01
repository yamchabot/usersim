# usersim

**Combinatorial test coverage without combinatorial build cost.**

Traditional test suites scale linearly: one test, one assertion, one pass/fail.
When you need 10,000 tests, you run your application 10,000 times.
usersim breaks that coupling.

You run your application a small number of times — once per scenario.
Each run collects raw measurements. Then Z3, a theorem prover from Microsoft
Research, evaluates thousands of logical constraints against those measurements
simultaneously. One scenario run. Thousands of checks. For free.

---

## The problem it solves

AI coding tools are compressing feature timelines from months to days.
4–40× as many features means you need proportionally more tests — not just
to keep up, but exponentially more, because feature interactions multiply.
Think 10,000× coverage, not 40×.

The obvious problem: 10,000× more tests means 10,000× longer builds.
That's a dead end.

usersim's answer: **decouple the expensive part (running your app) from the
cheap part (evaluating assertions)**. Run your app N times. Evaluate millions
of constraint combinations against the results. Build time stays flat.
Coverage grows without bound.

---

## How it works

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1 — Instrumentation     (your language)              │
│                                                             │
│  Run your application. Collect raw measurements.            │
│  Write a JSON object to stdout. That's it.                  │
│                                                             │
│  Keep this dumb. Measure, don't judge.                      │
└───────────────────────┬─────────────────────────────────────┘
                        │  { "response_ms": 240, "errors": 0,
                        │    "results": 12, "duration_ms": 1800 }
                        ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 2 — Perceptions         (Python)                     │
│                                                             │
│  Rename and reshape raw metrics into stable variable names. │
│  Pass numbers through. Compute ratios only if the raw       │
│  numbers aren't available.                                  │
│                                                             │
│  Keep this thin. No thresholds. No opinions.                │
└───────────────────────┬─────────────────────────────────────┘
                        │  { "response_ms": 240, "error_count": 0,
                        │    "result_count": 12, "wall_ms": 1800 }
                        ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 3 — Judgement           (Z3)                         │
│                                                             │
│  Each persona is a set of Z3 constraints over the           │
│  perception variables. Z3 evaluates all of them against     │
│  the collected facts and reports which personas are         │
│  satisfied, which constraints failed, and why.              │
│                                                             │
│  This is where the work happens. Make this fat.             │
└─────────────────────────────────────────────────────────────┘
```

One scenario run produces one set of facts. Z3 evaluates every constraint
in every persona against those facts simultaneously. Add more personas and
more constraints — the scenario run cost doesn't change.

---

## Install

```bash
pip install usersim          # includes a pure-Python Z3 fallback
pip install "usersim[z3]"    # with the real Z3 solver (recommended)
```

---

## Quickstart

```bash
usersim init      # scaffold project files
usersim run       # run the full pipeline
```

See [QUICKSTART.md](QUICKSTART.md) for a full walkthrough.

---

## Configuration

```yaml
# usersim.yaml

version: 1

# Shell command that runs your app and writes metrics JSON to stdout.
# USERSIM_SCENARIO is set to the current scenario name.
instrumentation: "python3 instrumentation.py"

# Python file (or shell command) that translates metrics to perception vars.
perceptions: "python3 perceptions.py"

# Persona constraint files. All Person subclasses are loaded automatically.
users:
  - users/*.py

# Each scenario triggers one instrumentation run.
scenarios:
  - default
  - peak_load
  - degraded

output:
  results: results.json
  report:  report.html
```

---

## Layer 1: Instrumentation

Run your app. Write numbers to stdout. One JSON object:

```json
{
  "schema":   "usersim.metrics.v1",
  "scenario": "peak_load",
  "metrics":  {
    "response_ms":   480,
    "error_count":   12,
    "total_requests": 1000,
    "result_count":  847,
    "wall_ms":       3200
  }
}
```

Use `USERSIM_SCENARIO` to vary what you measure:

```python
scenario = os.environ.get("USERSIM_SCENARIO", "default")
```

**Rules:**
- Measure everything you can. More variables = more constraint surface.
- Don't compute derived values here if the raw numbers are available.
- Don't make judgements. Numbers only.

---

## Layer 2: Perceptions

Rename metrics into stable variable names that Z3 constraints will reference.
Pass numbers through. Compute only what can't be expressed as a Z3 constraint.

```python
def compute(metrics: dict, **_) -> dict:
    return {
        "response_ms":    metrics.get("response_ms", 0.0),
        "error_count":    metrics.get("error_count", 0.0),
        "total_requests": metrics.get("total_requests", 0.0),
        "result_count":   metrics.get("result_count", 0.0),
        "wall_ms":        metrics.get("wall_ms", 0.0),
    }
```

**Rules:**
- Pass raw numbers through. Let Z3 compute ratios and relationships.
- Booleans are fine for *definitional* facts: "did the process exit?",
  "does the file exist?". Not for threshold judgements.
- If you're writing `if x > threshold: return True` — stop. That's a Z3 constraint.
- If you're computing a ratio that different users will threshold differently — stop.
  Pass the numerator and denominator separately. Let each persona do the division in Z3.

---

## Layer 3: Judgement (Z3)

This is where the work happens. Each persona expresses its requirements as Z3
constraints over the perception variables. Z3 evaluates all of them and reports
which constraints passed, which failed, and for `Implies`, whether the antecedent fired.

```python
from usersim import Person
from usersim.judgement.z3_compat import Implies, And, Not

class PowerUser(Person):
    name = "power_user"

    def constraints(self, P):
        return [
            # Threshold
            P.response_ms <= 100,

            # Conditional: if cache was warm, response must be fast
            Implies(P.cache_hit_rate >= 0.8, P.response_ms <= 50),

            # Arithmetic invariant: error rate as cross-multiplication
            # (avoids computing error_rate in perceptions)
            P.error_count * 1000 <= P.total_requests * 1,  # < 0.1%

            # Structural invariant: can't succeed with zero results
            Not(And(P.exit_code == 0, P.result_count == 0)),

            # Matrix invariant: total = persons × scenarios
            P.results_total == P.person_count * P.scenario_count,

            # Timing budget scales with work done
            P.wall_ms <= P.result_count * 10,
        ]
```

**The goal:** push as much logic as possible into constraints. Every constraint
you add is free coverage — zero additional scenario runs. Z3 evaluates all of them
in milliseconds regardless of how many you define.

### What Z3 can express

| Pattern | Example |
|---|---|
| Threshold | `P.response_ms <= 200` |
| Conditional | `Implies(P.cache_warm, P.response_ms <= 50)` |
| Compound conditional | `Implies(And(P.load_high, P.cache_cold), P.response_ms <= 2000)` |
| Negation | `Not(P.error_flag)` |
| Invariant violation | `Not(And(P.exit_code == 0, P.result_count == 0))` |
| Cross-variable arithmetic | `P.error_count * 100 <= P.total_requests * 5` |
| Matrix invariant | `P.results_total == P.person_count * P.scenario_count` |
| Scaling budget | `P.wall_ms <= P.result_count * max_ms_per_result` |
| Consistency | `P.satisfied_count <= P.total_count` |
| Majority quality | `(P.has_doctype + P.is_self_contained + P.has_content) >= 2` |

### What belongs in perceptions vs Z3

| In perceptions | In Z3 |
|---|---|
| Rename `raw_response_time` → `response_ms` | `P.response_ms <= 200` |
| Parse a nested JSON value | `P.error_count * 100 <= P.total * 1` |
| Compute a rolling percentile from a time series | `P.p99_ms <= 500` |
| Detect whether a file exists | `Implies(P.file_exists, P.file_size_bytes >= 1000)` |
| Extract a status code from an HTTP response | `P.status_code == 200` |

If you can write it as a Z3 expression, it belongs in Z3.

---

## CLI reference

```bash
usersim init [DIR]               # scaffold a new project
usersim run                      # run the full pipeline (reads usersim.yaml)
usersim run --scenario peak_load # run one specific scenario
usersim run --out results.json   # save results to file
usersim run --quiet              # suppress human summary on stderr
usersim run --verbose            # print stage info to stderr

# One-off judgement (no config file needed):
usersim judge --users users/*.py            # reads perceptions JSON from stdin
usersim judge --perceptions p.json ...      # from a file
usersim judge --perceptions-dir perc/ ...   # matrix mode

# HTML report:
usersim run | usersim report                # pipe results into report
usersim report --results results.json       # from a file
```

Exit code is 0 when all personas are satisfied across all scenarios, 1 otherwise.

---

## CI integration

```yaml
# GitHub Actions
- run: pip install usersim
- run: usersim run --out results.json
- uses: actions/upload-artifact@v4
  with: { name: usersim-report, path: report.html }
```

```makefile
# Makefile
test-ux:
    usersim run
```

---

## Example

[`examples/data-processor/`](examples/data-processor/) tests an in-memory data
processor across three dataset sizes with three personas. All measurements are real.

```bash
cd examples/data-processor
usersim run
```

---

## Z3 on ARM64

`z3-solver` isn't packaged for all ARM64 Python versions. usersim ships a
pure-Python fallback. Install `usersim[z3]` when possible; the fallback activates
automatically otherwise.

---

## License

MIT
