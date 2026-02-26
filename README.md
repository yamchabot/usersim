# usersim

**User simulation framework.** Define simulated personas. Express their needs as logical constraints. Measure whether your application satisfies them — automatically, on every build.

---

## The idea

Most application testing checks *correctness* ("does this return 200?").  
User simulation checks *satisfaction* ("would Sarah the CTO understand this screen?").

You define:
1. **Metrics** — raw measurements from your app (load time, error rate, visual complexity)
2. **Perceptions** — what those numbers mean to a human ("loads fast", "too cluttered")
3. **Users** — named personas with logical constraints ("Sarah needs clusters visible on large graphs")

usersim runs the chain, uses Z3 to check the constraints, and tells you who's satisfied.

---

## Install

```bash
pip install usersim          # core (pure-Python Z3 fallback included)
pip install usersim[z3]      # with real Z3 solver (recommended)
```

---

## Quick start

```bash
usersim init               # scaffold instrumentation, perceptions.py, users/
# … edit the three layers …
node instrumentation.js    # write metrics.json
usersim judge \
  --perceptions perceptions.json \
  --users users/*.py
```

Output:
```
  ✓ power_user          score=1.000
  ✓ casual_user         score=1.000
  ✗ accessibility_user  score=0.667 — P.contrast_ratio >= RealVal(4.5)

  2/3 satisfied  (score 88.9%)
```

---

## The three layers

Each layer is a separate file that communicates with the next via JSON.  
**You write layers 1 and 2 in whatever language makes sense. We handle layer 3.**

```
Your app
  │
  ▼  writes ──────────────────────────────────────────────────────────
instrumentation.js / .py / .rs / …
  │
  │  metrics.json
  │  { "schema": "usersim.metrics.v1", "metrics": { ... } }
  │
  ▼  reads / writes ───────────────────────────────────────────────────
perceptions.py  (or any language)
  │
  │  perceptions.json
  │  { "schema": "usersim.perceptions.v1", "facts": { ... } }
  │
  ▼  reads ────────────────────────────────────────────────────────────
usersim (Z3 engine)
  │
  ▼  writes
results.json  +  report.html
```

---

### Layer 1 — Instrumentation (your app's language)

Collect measurements from your application and write `metrics.json`.

```js
// instrumentation.js
const metrics = {
  load_time_ms:  measurePageLoad(),
  error_count:   getErrorCount(),
  bundle_kb:     getBundleSize() / 1024,
};

require("fs").writeFileSync("metrics.json", JSON.stringify({
  schema:   "usersim.metrics.v1",
  scenario: process.env.USERSIM_SCENARIO || "default",
  metrics,
}));
```

```python
# instrumentation.py
import json, time

metrics = {
    "response_time_ms": measure_response(),
    "cache_hit_rate":   get_cache_stats()["hit_rate"],
    "error_count":      get_error_count(),
}

json.dump({"schema": "usersim.metrics.v1", "scenario": "api_load", "metrics": metrics},
          open("metrics.json", "w"))
```

**The only rule:** write `{ "schema": "usersim.metrics.v1", "metrics": { ... } }`.

---

### Layer 2 — Perceptions (Python recommended, any language accepted)

Translate raw numbers into what a human would perceive.

```python
# perceptions.py
from usersim.perceptions.library import threshold, flag, in_range

def compute(metrics, scenario="default", person=None):
    return {
        "loads_fast":      threshold(metrics, "load_time_ms",  max=300),
        "bundle_is_small": threshold(metrics, "bundle_kb",     max=200),
        "no_errors":       metrics.get("error_count", 0) == 0,
        "cache_warm":      threshold(metrics, "cache_hit_rate", min=0.80),
    }
```

**If you prefer another language**, write an executable that reads `metrics.json` from stdin and writes `perceptions.json` to stdout:

```json
{
  "schema":   "usersim.perceptions.v1",
  "scenario": "api_load",
  "person":   "power_user",
  "facts": {
    "loads_fast":      true,
    "bundle_is_small": false,
    "no_errors":       true,
    "cache_warm":      true
  }
}
```

#### Built-in perception helpers

```python
from usersim.perceptions.library import (
    threshold,       # threshold(m, "key", max=500) → bool
    in_range,        # in_range(m, "key", 10, 100) → bool
    ratio,           # ratio(m, "numerator", "denominator") → float
    flag,            # flag(m, "key") → bool (handles bool/int/string)
    normalise,       # normalise(m, "key", lo=0, hi=100) → 0.0–1.0
    percentile_rank, # percentile_rank(value, population) → 0.0–1.0
    z_score,         # z_score(value, mean, std) → float
)
```

---

### Layer 3 — Judgement (Z3, controlled by usersim)

Define who your users are and what they need:

```python
# users/power_user.py
from usersim import Person
from usersim.judgement.z3_compat import And, Implies, Or

class PowerUser(Person):
    name        = "power_user"
    description = "Experienced developer who needs speed and reliability."

    def constraints(self, P):
        """
        P.fact_name is a Z3 Bool/Real variable for each fact in perceptions.json.
        Return a list of constraints — all must be satisfiable for this user
        to be "satisfied".
        """
        return [
            P.loads_fast,
            P.no_errors,
            Implies(P.cache_warm, P.loads_fast),   # if cache is warm, it must be fast
        ]
```

**Z3 expressions you can use:**

| Expression | Meaning |
|---|---|
| `P.fact` | The fact must be true |
| `Not(P.fact)` | The fact must be false |
| `And(P.a, P.b)` | Both must hold |
| `Or(P.a, P.b)` | At least one must hold |
| `Implies(P.a, P.b)` | If a then b (vacuously true when a is false) |
| `P.score >= RealVal(0.8)` | Numeric comparison |

---

## Running

```bash
# Judge against an existing perceptions.json
usersim judge \
  --perceptions perceptions.json \
  --users users/power_user.py users/casual_user.py

# Run the full pipeline (instrumentation → perceptions → judgement)
usersim run \
  --metrics    metrics.json \
  --perceptions perceptions.py \
  --users      users/*.py \
  --out        results.json

# Matrix: one perceptions.json per scenario, all persons × all scenarios
usersim judge \
  --perceptions-dir perceptions/ \
  --users           users/*.py \
  --out             results.json

# HTML report
usersim report --results results.json --out report.html
```

---

## JSON schema reference

### metrics.json
```json
{
  "schema":   "usersim.metrics.v1",
  "scenario": "string (optional)",
  "context":  { "any": "extra metadata" },
  "metrics":  {
    "metric_name": 123,
    "another":     true,
    "ratio":       0.85
  }
}
```

### perceptions.json
```json
{
  "schema":   "usersim.perceptions.v1",
  "scenario": "string",
  "person":   "string (or 'all')",
  "facts": {
    "fact_name": true,
    "score":     0.85
  }
}
```

### results.json
```json
{
  "schema":   "usersim.results.v1",
  "scenario": "string",
  "results": [
    {
      "person":     "power_user",
      "satisfied":  true,
      "score":      1.0,
      "violations": [],
      "scenario":   "default"
    }
  ],
  "summary": { "total": 1, "satisfied": 1, "score": 1.0 }
}
```

---

## Example: graph visualization

See [`examples/graph-viz/`](examples/graph-viz/) for a complete worked example measuring whether a force-directed graph layout satisfies different engineering personas (CTO, Staff Engineer, etc.).

The instrumentation runs in JavaScript (measuring canvas layout metrics), the perceptions translate layout stress / blob separation / edge crossings into legibility facts, and the users express what each persona needs to make sense of the visualization.

---

## Z3 on ARM64

`z3-solver` isn't packaged for all ARM64 Python versions. usersim ships a pure-Python fallback that handles all the constraint patterns above. Install `usersim[z3]` when possible; the fallback activates automatically when z3 isn't available.

---

## Architecture

```
usersim/
├── judgement/
│   ├── engine.py       # Z3 evaluation loop
│   ├── person.py       # Person base class + FactNamespace
│   └── z3_compat.py    # Real z3 + pure-Python fallback
├── perceptions/
│   └── library.py      # threshold(), ratio(), flag(), etc.
├── report/
│   └── html.py         # Self-contained HTML report
├── cli.py              # usersim run/judge/report/init
├── runner.py           # Pipeline orchestrator
├── scaffold.py         # usersim init
└── schema.py           # JSON schema validation
```

---

## License

MIT
