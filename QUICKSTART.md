# Quickstart

Build a working user simulation in ~10 minutes.

We'll simulate three users evaluating a web API — does it feel fast enough? Are errors tolerable? You'll see how different personas have different needs, and how changing one metric ripples through to who's satisfied.

**Prerequisites:** Python 3.10+, `pip install usersim`

---

## 1. Create a project

```bash
mkdir api-sim && cd api-sim
usersim init
```

This creates:
```
api-sim/
├── usersim.yaml         # project config
├── instrumentation.js   # replace with your language of choice
├── perceptions.py       # translate metrics → human facts
└── users/
    └── example_user.py  # your first persona
```

We'll replace these files with our own. Delete the scaffolded ones:

```bash
rm instrumentation.js users/example_user.py
```

---

## 2. Write the instrumentation

Instrumentation collects raw measurements from your app and writes `metrics.json`. In production this would hook into your real system — for this tutorial, we'll simulate an API call.

Create `instrumentation.py`:

```python
import json, time, urllib.request

# Simulate measuring your API
# In production: replace with real measurements
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
        "p99_ms":      response_ms * 2.1,   # synthetic p99
        "cache_hit":   0.87,
    }

metrics = measure()
print(f"  response: {metrics['response_ms']:.0f}ms  errors: {metrics['error_rate']:.1%}")

json.dump({
    "schema":   "usersim.metrics.v1",
    "scenario": "default",
    "metrics":  metrics,
}, open("metrics.json", "w"), indent=2)
```

> **That's the only rule for instrumentation:** produce a JSON file with
> `"schema": "usersim.metrics.v1"` and a `"metrics"` object.
> The file can be written from any language.

Run it once to see what it produces:

```bash
python3 instrumentation.py
cat metrics.json
```

You'll see something like:
```json
{
  "schema": "usersim.metrics.v1",
  "scenario": "default",
  "metrics": {
    "response_ms": 183,
    "error_rate": 0.0,
    "uptime_pct": 99.95,
    "p99_ms": 384.3,
    "cache_hit": 0.87
  }
}
```

---

## 3. Write the perceptions

Perceptions translate raw numbers into what a human would *perceive*. This is the "semantic bridge" — instead of reasoning about `183ms`, users reason about `feels_fast: true`.

Replace `perceptions.py` with:

```python
from usersim.perceptions.library import threshold, flag

def compute(metrics, **_):
    return {
        # Speed
        "feels_fast":      threshold(metrics, "response_ms",  max=200),
        "p99_acceptable":  threshold(metrics, "p99_ms",       max=500),

        # Reliability
        "no_errors":       threshold(metrics, "error_rate",   max=0.01),
        "high_uptime":     threshold(metrics, "uptime_pct",   min=99.9),

        # Efficiency
        "cache_is_warm":   threshold(metrics, "cache_hit",    min=0.80),
    }
```

A few things to notice:
- The function is named `compute` — usersim calls this directly when the file is `.py`
- Each fact is a **human-readable name** for a threshold check
- `threshold(metrics, "key", max=X)` returns `True` if `metrics["key"] ≤ X`
- You have access to [more helpers](README.md#perceptions-layer-2): `ratio`, `in_range`, `normalise`, `flag`, `z_score`, ...

**Run it manually to verify:**

```bash
python3 - <<'EOF'
import json
from perceptions import compute

with open("metrics.json") as f:
    m = json.load(f)

facts = compute(m["metrics"])
for k, v in facts.items():
    print(f"  {k}: {v}")
EOF
```

```
  feels_fast:     True
  p99_acceptable: True
  no_errors:      True
  high_uptime:    True
  cache_is_warm:  True
```

Good — all facts are true for this healthy API response. Now let's define users who care about different subsets of these.

---

## 4. Define your users

Each user is a Python file with a class that extends `Person`. The `constraints()` method returns a list of Z3 expressions — all must be satisfied for this user to be happy.

### User 1: Power User

Needs speed, reliability, and efficiency. High expectations.

Create `users/power_user.py`:

```python
from usersim import Person
from usersim.judgement.z3_compat import And, Implies

class PowerUser(Person):
    name        = "power_user"
    description = "Technical user who notices every millisecond."

    def constraints(self, P):
        return [
            P.feels_fast,         # response must be under 200ms
            P.p99_acceptable,     # tail latency matters too
            P.no_errors,          # zero tolerance for errors
            P.cache_is_warm,      # expects efficient caching
        ]
```

### User 2: Casual User

Just needs the basics — works correctly, doesn't hang.

Create `users/casual_user.py`:

```python
from usersim import Person

class CasualUser(Person):
    name        = "casual_user"
    description = "Occasional user who only notices obvious problems."

    def constraints(self, P):
        return [
            P.no_errors,      # errors break the experience
            P.high_uptime,    # service must be available
            # doesn't care about speed or cache efficiency
        ]
```

### User 3: On-Call Engineer

Evaluating the API from an operational perspective.

Create `users/ops_engineer.py`:

```python
from usersim import Person
from usersim.judgement.z3_compat import Implies, And

class OpsEngineer(Person):
    name        = "ops_engineer"
    description = "On-call engineer watching SLA compliance."

    def constraints(self, P):
        return [
            P.high_uptime,                          # SLA requires 99.9%+
            P.no_errors,                            # errors page them at 3am
            Implies(P.cache_is_warm, P.feels_fast), # if cache works, it must be fast
            P.p99_acceptable,                       # p99 is in the SLA
        ]
```

> **`Implies(A, B)`** means "if A is true, then B must also be true." When A is false,
> the constraint is vacuously satisfied — this lets you express conditional requirements
> without failing when a feature is simply absent.

---

## 5. Run the judgement

First, run your instrumentation to get fresh metrics, then run perceptions to get facts:

```bash
python3 instrumentation.py
```

Then judge all users against those facts:

```bash
usersim run \
  --metrics     metrics.json \
  --perceptions perceptions.py \
  --users       users/power_user.py users/casual_user.py users/ops_engineer.py \
  --out         results.json
```

Expected output (healthy API):
```
  ✓ power_user      score=1.000
  ✓ casual_user     score=1.000
  ✓ ops_engineer    score=1.000

  3/3 satisfied  (score 100.0%)
```

---

## 6. Break something and see who notices

Edit `instrumentation.py` to simulate a slow, error-prone API:

```python
def measure():
    return {
        "response_ms": 480,    # slow
        "error_rate":  0.05,   # 5% errors
        "uptime_pct":  99.95,
        "p99_ms":      950,    # terrible p99
        "cache_hit":   0.60,   # cache is cold
    }
```

Re-run:

```bash
python3 instrumentation.py
usersim run \
  --metrics     metrics.json \
  --perceptions perceptions.py \
  --users       users/power_user.py users/casual_user.py users/ops_engineer.py
```

```
  ✗ power_user      score=0.000 — P.feels_fast
  ✗ casual_user     score=0.500 — P.no_errors
  ✗ ops_engineer    score=0.250 — P.no_errors

  0/3 satisfied  (score 25.0%)
```

Notice:
- **power_user** fails everything (first violation shown: `P.feels_fast`)
- **casual_user** only cares about errors and uptime — still fails because of the error rate
- **ops_engineer** fails too, but scores differently based on their constraint weights

Different users, different pain points. This is what user simulation tells you that a test suite can't.

---

## 7. Generate a report

```bash
usersim report --results results.json --out report.html
open report.html    # or xdg-open on Linux
```

The HTML report shows a persona × scenario matrix — green for satisfied, red for failed, with constraint violation details on hover.

---

## 8. Multiple scenarios

Real systems behave differently under different conditions. Test them all:

Create `perceptions/low_load.json`:
```json
{
  "schema": "usersim.perceptions.v1",
  "scenario": "low_load",
  "person": "all",
  "facts": {
    "feels_fast": true, "p99_acceptable": true,
    "no_errors": true, "high_uptime": true, "cache_is_warm": true
  }
}
```

Create `perceptions/peak_load.json`:
```json
{
  "schema": "usersim.perceptions.v1",
  "scenario": "peak_load",
  "person": "all",
  "facts": {
    "feels_fast": false, "p99_acceptable": false,
    "no_errors": true, "high_uptime": true, "cache_is_warm": false
  }
}
```

Run the matrix:

```bash
usersim judge \
  --perceptions-dir perceptions/ \
  --users users/*.py \
  --out results.json

usersim report --results results.json --out report.html
```

```
                      low_load      peak_load
  ────────────────────────────────────────────
  power_user              ✓             ✗
  casual_user             ✓             ✓
  ops_engineer            ✓             ✗
```

**casual_user doesn't care about speed**, so they're satisfied even at peak load. The engineer and ops roles both feel peak load.

---

## What to do next

**Add it to CI.** Run your instrumentation in your test suite and pipe results through usersim. Exit code is 0 when all users are satisfied, 1 otherwise — works with any CI system.

```yaml
# .github/workflows/usersim.yml
- run: python3 instrumentation.py
- run: |
    usersim run \
      --metrics metrics.json \
      --perceptions perceptions.py \
      --users users/*.py \
      --out results.json
- run: usersim report --results results.json --out report.html
- uses: actions/upload-artifact@v4
  with: { name: usersim-report, path: report.html }
```

**Add more scenarios.** Each scenario is just a different `metrics.json`. Automate generating them by running your instrumentation in different conditions (low load, peak load, degraded dependency, cold cache).

**Add more personas.** One file per persona. Common ones: power user, casual user, accessibility user, ops engineer, new hire, API consumer.

**Write instrumentation in your actual stack.** The JSON format is trivial to produce from any language. See `examples/graph-viz/instrumentation.js` for a JavaScript example.

**Add numeric constraints.** The `RealVal` type lets you express threshold constraints directly in user files:

```python
from usersim.judgement.z3_compat import RealVal

def constraints(self, P):
    return [
        P.response_ms <= RealVal(200),   # numeric threshold in the user layer
    ]
```

---

## Reference

- [README.md](README.md) — architecture overview and full CLI reference
- [`examples/graph-viz/`](examples/graph-viz/) — real-world example (JavaScript instrumentation, graph layout perceptions)
- [`usersim/perceptions/library.py`](usersim/perceptions/library.py) — full perception helper reference
- [`usersim/judgement/z3_compat.py`](usersim/judgement/z3_compat.py) — Z3 expressions reference
