# Quickstart

Build a working user simulation in ~10 minutes.

We'll simulate three users evaluating a web API — does it feel fast enough? Are errors tolerable? You'll see how different personas have different needs, and how changing one metric ripples through to who's satisfied.

**Prerequisites:** Python 3.10+, `pip install usersim`

---

## 1. Create a project

```bash
mkdir my-sim && cd my-sim
usersim init
```

This creates:
```
my-sim/
├── usersim.yaml         # pipeline config — this is what usersim run reads
├── instrumentation.py   # collect metrics from your app
├── perceptions.py       # translate metrics → human facts
└── users/
    └── example_user.py  # your first persona
```

We'll replace the stub files with our own. Delete the scaffolded ones:

```bash
rm users/example_user.py
```

---

## 2. Configure the pipeline

Open `usersim.yaml` — it declares how to run each stage:

```yaml
version: 1
instrumentation: "python3 instrumentation.py"
perceptions: "python3 perceptions.py"
users:
  - users/*.py
scenarios:
  - default
output:
  results: results.json
  report:  report.html
```

This is all usersim needs to know. When you run `usersim run`, it executes each stage in sequence — no manual piping required.

---

## 3. Write the instrumentation

Instrumentation collects raw measurements from your app and **writes metrics JSON to stdout**. usersim reads it and passes it to the next stage automatically.

Replace `instrumentation.py` with:

```python
import json, sys, time, urllib.request, os

scenario = os.environ.get("USERSIM_SCENARIO", "default")

def measure():
    start = time.time()
    try:
        urllib.request.urlopen("http://httpbin.org/delay/0", timeout=2)
        response_ms = (time.time() - start) * 1000
        error_rate  = 0.0
    except Exception:
        response_ms = 9999
        error_rate  = 1.0

    return {
        "response_ms": response_ms,
        "error_rate":  error_rate,
        "uptime_pct":  99.95,
        "p99_ms":      response_ms * 2.1,
        "cache_hit":   0.87,
    }

metrics = measure()
print(f"  response: {metrics['response_ms']:.0f}ms", file=sys.stderr)

json.dump({
    "schema":   "usersim.metrics.v1",
    "scenario": scenario,
    "metrics":  metrics,
}, sys.stdout)
```

> `USERSIM_SCENARIO` is set automatically by usersim for each scenario run.
> One instrumentation script can serve all your scenarios.

---

## 4. Write the perceptions

A domain expert looks at the raw metrics and extracts meaningful observations.
**Perceptions should mostly be numeric** — pass values through or derive rates and
ratios. Thresholds ("is 400ms fast enough?") differ per user and belong in step 5.

Replace `perceptions.py`:

```python
def compute(metrics: dict, **_) -> dict:
    return {
        # Raw timing — pass through; each user decides what's "too slow"
        "response_ms": metrics.get("response_ms", 0.0),
        "p99_ms":      metrics.get("p99_ms", 0.0),

        # Rates and scores — pass through or derive
        "error_rate":  metrics.get("error_rate", 0.0),
        "uptime_pct":  metrics.get("uptime_pct", 100.0),
        "cache_hit":   metrics.get("cache_hit", 0.0),
    }
```

usersim detects `compute()` and calls it in-process — no subprocess needed.

> Booleans are fine for *definitional* facts: "did the job complete?", "is the
> feature enabled?". Avoid booleans for continuous values where users disagree
> on what counts as acceptable.

---

## 5. Define your users

Each user applies their own thresholds to the numeric perceptions.
Plain comparison operators work — no special Z3 imports needed for simple cases.

Create `users/power_user.py`:

```python
from usersim import Person

class PowerUser(Person):
    name        = "power_user"
    description = "Technical user who notices every millisecond."

    def constraints(self, P):
        return [
            P.response_ms <= 100,    # wants sub-100ms
            P.p99_ms      <= 300,
            P.error_rate  <= 0.001,
            P.cache_hit   >= 0.90,
        ]
```

Create `users/casual_user.py`:

```python
from usersim import Person

class CasualUser(Person):
    name        = "casual_user"
    description = "Occasional user who only notices obvious problems."

    def constraints(self, P):
        return [
            P.response_ms <= 3_000,  # barely notices a 3s wait
            P.error_rate  <= 0.05,
        ]
```

Create `users/ops_engineer.py`:

```python
from usersim import Person
from usersim.judgement.z3_compat import Implies

class OpsEngineer(Person):
    name        = "ops_engineer"
    description = "On-call engineer watching SLA compliance."

    def constraints(self, P):
        return [
            P.uptime_pct  >= 99.9,
            P.error_rate  <= 0.01,
            P.p99_ms      <= 500,
            # If cache is warm, response must be fast (cache should help)
            Implies(P.cache_hit >= 0.80, P.response_ms <= 200),
        ]
```

> **`Implies(A, B)`** means "if A holds, B must also hold." When A is false the
> constraint is vacuously satisfied — useful for conditional requirements.
>
> **Different users, different thresholds** — that's the point. The power user
> needs sub-100ms; the casual user is fine with 3s. Both use the same
> `response_ms` perception but express their own opinion in constraints.

---

## 6. Run it

```bash
usersim run
```

That's it. usersim reads `usersim.yaml`, runs instrumentation → perceptions → judgement, and prints a summary:

```
  ✓ power_user      score=1.000
  ✓ casual_user     score=1.000
  ✓ ops_engineer    score=1.000

  3/3 satisfied  (score 100.0%)
```

Results are saved to `results.json` and a human-readable report to `report.html` (as configured in `usersim.yaml`).

---

## 7. Break something and see who notices

Edit `instrumentation.py` — return hardcoded values to simulate a degraded API:

```python
def measure():
    return {
        "response_ms":    480,
        "p99_ms":         950,
        "error_rate":     0.05,   # 5% error rate
        "uptime_pct":     99.95,
        "cache_hit":      0.60,
    }
```

Re-run:

```bash
usersim run
```

```
  ✗ power_user      score=0.000
  ✓ casual_user     score=1.000
  ✗ ops_engineer    score=0.500

  1/3 satisfied  (score 33.3%)
```

Notice that the **casual user is satisfied** — 480ms is under their 3s threshold, and 5%
errors is at the edge of their tolerance. The power user and ops engineer fail on
completely different constraints. This is what user simulation tells you that a test suite can't.

---

## 8. Multiple scenarios

Add scenarios to `usersim.yaml`:

```yaml
scenarios:
  - default
  - peak_load
  - cold_cache
```

Use `USERSIM_SCENARIO` in `instrumentation.py` to vary conditions:

```python
scenario = os.environ.get("USERSIM_SCENARIO", "default")

SCENARIO_METRICS = {
    "default":    {"response_ms": 120, "error_rate": 0.0,  "cache_hit": 0.87, ...},
    "peak_load":  {"response_ms": 480, "error_rate": 0.02, "cache_hit": 0.40, ...},
    "cold_cache": {"response_ms": 350, "error_rate": 0.0,  "cache_hit": 0.05, ...},
}
metrics = SCENARIO_METRICS.get(scenario, SCENARIO_METRICS["default"])
```

Run:

```bash
usersim run
```

usersim runs the pipeline once per scenario and shows a matrix:

```
                      default    peak_load   cold_cache
  ──────────────────────────────────────────────────────
  power_user              ✓             ✗            ✗
  casual_user             ✓             ✓            ✓
  ops_engineer            ✓             ✗            ✓
```

---

## What to do next

**Add to CI:**

```yaml
- run: pip install usersim
- run: usersim run --out results.json
- uses: actions/upload-artifact@v4
  with: { name: usersim-report, path: report.html }
```

**Add to your Makefile:**

```makefile
test-ux:
    usersim run
```

**Add to package.json:**

```json
"scripts": { "test:ux": "usersim run" }
```

Exit code is 0 when all users are satisfied, 1 otherwise — compatible with any CI system.

**Use a different language for instrumentation.** The config just specifies a shell command:

```yaml
instrumentation: "cargo run --bin measure --release"
# or:
instrumentation: "mvn exec:java -Dexec.mainClass=Measure"
# or:
instrumentation: "./measure.sh"
```

---

## Reference

- [README.md](README.md) — architecture overview and full CLI reference
- [`examples/data-processor/`](examples/data-processor/) — complete working example with real measurements
- [`usersim/perceptions/library.py`](usersim/perceptions/library.py) — perception helper reference
