# Quickstart

You'll have a working simulation in about 10 minutes.

**Prerequisites:** Python 3.10+, `pip install usersim`

---

## The idea

You run your application once per path. That produces raw numbers.
Z3 evaluates your constraints against those numbers — thousands of checks
from a single run. Build time stays flat. Coverage grows as you add constraints.

Three layers:
- **Instrumentation** — run your app, write raw numbers to stdout. Dumb.
- **Perceptions** — rename and reshape those numbers into stable variable names. Thin.
- **Constraints** — Z3 expressions over those variables, one set per persona. Fat.

All the work happens in constraints. That's the point.

---

## 1. Scaffold

```bash
mkdir my-sim && cd my-sim
usersim init
```

You get:
```
my-sim/
├── usersim.yaml
├── instrumentation.py
├── perceptions.py
└── users/
    └── example_user.py
```

---

## 2. Configure

`usersim.yaml` declares the pipeline:

```yaml
version: 1
instrumentation: "python3 instrumentation.py"
perceptions:     "python3 perceptions.py"
users:
  - users/*.py
paths:
  - default
  - peak_load
  - degraded
output:
  results: results.json
  report:  report.html
```

Each path triggers one instrumentation run with `USERSIM_PATH` set.
The results form a matrix: every persona × every path.

---

## 3. Instrumentation

Measure your app. Write numbers. Don't make judgements.

```python
# instrumentation.py
import json, os, time

path = os.environ.get("USERSIM_PATH", "default")

SCENARIOS = {
    "default":   {"response_ms": 120, "error_count": 0,  "requests": 100, "cache_hits": 87},
    "peak_load": {"response_ms": 480, "error_count": 12, "requests": 100, "cache_hits": 40},
    "degraded":  {"response_ms": 950, "error_count": 30, "requests": 100, "cache_hits": 5},
}

json.dump({
    "schema":   "usersim.metrics.v1",
    "path": path,
    "metrics":  SCENARIOS[path],
}, open("/dev/stdout", "w"))
```

Expose as many raw variables as you can. The more numbers you collect,
the more relationships Z3 can reason about.

---

## 4. Perceptions

Rename metrics into the variable names your constraints will use.
Pass numbers through. Don't compute thresholds.

```python
# perceptions.py
from usersim.perceptions.library import run_perceptions

def compute(metrics: dict, **_) -> dict:
    return {
        # Pass raw numbers through — Z3 will compute ratios and relationships
        "response_ms":  metrics.get("response_ms", 0.0),
        "error_count":  metrics.get("error_count", 0.0),
        "requests":     metrics.get("requests", 0.0),
        "cache_hits":   metrics.get("cache_hits", 0.0),
    }

if __name__ == "__main__":
    run_perceptions(compute)
```

**Stop yourself from writing this:**
```python
# Don't do this in perceptions
"is_fast": metrics["response_ms"] < 200,        # threshold — belongs in Z3
"error_rate": metrics["errors"] / metrics["total"],  # ratio — Z3 can do this
```

---

## 5. Personas

Each persona is a set of Z3 constraints. This is where you put the work.

```python
# users/power_user.py
from usersim import Person
from usersim.judgement.z3_compat import Implies, And, Not

class PowerUser(Person):
    name = "power_user"
    role = "Performance-critical application"

    def constraints(self, P):
        return [
            # Simple threshold
            P.response_ms <= 100,

            # Conditional: cache should help response time
            Implies(P.cache_hits >= 80, P.response_ms <= 50),

            # Cross-variable arithmetic (don't compute error_rate in perceptions)
            # This expresses: error_count / requests <= 0.001
            P.error_count * 1000 <= P.requests * 1,

            # Structural invariant: can't have success with zero cache hits
            # when we expect the cache to be warm
            Not(And(P.response_ms <= 50, P.cache_hits == 0)),
        ]
```

```python
# users/casual_user.py
from usersim import Person
from usersim.judgement.z3_compat import Implies

class CasualUser(Person):
    name = "casual_user"
    role = "Tolerant end user"

    def constraints(self, P):
        return [
            P.response_ms <= 3000,
            # Same cross-multiply pattern, looser threshold: < 5% error rate
            P.error_count * 100 <= P.requests * 5,
        ]
```

```python
# users/ops_engineer.py
from usersim import Person
from usersim.judgement.z3_compat import Implies, And

class OpsEngineer(Person):
    name = "ops_engineer"
    role = "On-call SRE"

    def constraints(self, P):
        return [
            # SLA: p99 under 500ms
            P.response_ms <= 500,

            # Under load, error rate must stay under 1%
            P.error_count * 100 <= P.requests * 1,

            # Cache degradation is expected in degraded mode,
            # but response must still be under 2000ms
            Implies(P.cache_hits <= 10, P.response_ms <= 2000),

            # If cache is warm, response must be fast — cache must be helping
            Implies(P.cache_hits >= 80, P.response_ms <= 200),
        ]
```

**The key:** same perceptions variables, completely different constraint logic per persona.
Z3 evaluates them all in one pass against each path's facts.

---

## 6. Run

```bash
usersim run
```

```
                      default    peak_load   degraded
  ────────────────────────────────────────────────────
  power_user              ✓             ✗          ✗
  casual_user             ✓             ✓          ✗
  ops_engineer            ✓             ✗          ✗

  3/9 satisfied  (score 33.3%)
```

---

## 7. Break it intentionally

Modify `instrumentation.py` to return degraded values for all paths, then run again.
You'll see exactly which constraints fail and why — every persona reports independently.

---

## 8. Make the constraints do real work

The quick-start above uses simple thresholds. That's the floor, not the ceiling.
Push more reasoning into Z3:

```python
def constraints(self, P):
    return [
        # Matrix invariant: total results must equal persons × paths
        P.results_total == P.person_count * P.scenario_count,

        # Timing budget scales with work: allow 10ms per result
        P.wall_ms <= P.result_count * 10,

        # Consistency: can't have more satisfied than total
        P.satisfied_count <= P.total_count,

        # Invariant violation: exit 0 with zero results is impossible
        Not(And(P.exit_code == 0, P.result_count == 0)),

        # Multi-condition: at least 2 of 3 quality signals must hold
        (P.has_doctype + P.is_self_contained + P.has_content) >= 2,
    ]
```

Every additional constraint is free coverage. The path runs don't change.
Z3 evaluates them all in milliseconds.

---

## CI

```yaml
- run: pip install usersim
- run: usersim run --out results.json
- uses: actions/upload-artifact@v4
  with: { name: usersim-report, path: report.html }
```

Exit code 0 = all personas satisfied. Exit code 1 = something failed.
Drop it in your pipeline like any other test command.

---

## Reference

- [README.md](README.md) — architecture and full CLI reference
- [VISION.md](VISION.md) — why this exists and the design philosophy
- [`examples/data-processor/`](examples/data-processor/) — complete working example
