# usersim

**Test whether your application satisfies real users — not just whether it works.**

Most test suites check correctness: *did this return 200? did this render?*  
usersim checks satisfaction: *would the CTO understand this screen? would the on-call engineer trust this dashboard?*

You define simulated personas. You express what each one needs as logical constraints. usersim measures whether your application satisfies them — automatically, on every build.

---

## How it works

Three layers. Each talks to the next through a JSON file.

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1 — Instrumentation     (your language)              │
│                                                             │
│  Collect raw measurements from your app.                    │
│  Output: metrics.json                                       │
└───────────────────────┬─────────────────────────────────────┘
                        │  { "load_time_ms": 240, "errors": 0 }
                        ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 2 — Perceptions         (any language)               │
│                                                             │
│  Translate numbers into what a human would perceive.        │
│  Output: perceptions.json                                   │
└───────────────────────┬─────────────────────────────────────┘
                        │  { "loads_fast": true, "no_errors": true }
                        ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 3 — Judgement           (Z3, controlled by usersim)  │
│                                                             │
│  Check each persona's logical constraints.                  │
│  Output: results.json + report.html                         │
└─────────────────────────────────────────────────────────────┘
```

**You write layers 1 and 2. We handle layer 3.**

Instrumentation runs in your app's language. Perceptions can be anything; we provide a Python helper library. Judgement always runs through Z3 — usersim owns that layer so the constraint evaluation is sound and consistent.

---

## Install

```bash
pip install usersim          # includes a pure-Python Z3 fallback
pip install "usersim[z3]"    # with the real Z3 solver (recommended)
```

---

## A taste

**Instrumentation** — measure your app and write `metrics.json`:
```json
{
  "schema":   "usersim.metrics.v1",
  "scenario": "api_under_load",
  "metrics":  { "response_ms": 180, "error_rate": 0.002, "p99_ms": 420 }
}
```

**Perceptions** — translate numbers into human facts (`perceptions.py`):
```python
from usersim.perceptions.library import threshold

def compute(metrics, **_):
    return {
        "feels_fast":    threshold(metrics, "response_ms", max=200),
        "no_errors":     threshold(metrics, "error_rate",  max=0.01),
        "p99_acceptable":threshold(metrics, "p99_ms",      max=500),
    }
```

**Users** — express what each persona needs (`users/lead_engineer.py`):
```python
from usersim import Person
from usersim.judgement.z3_compat import Implies

class LeadEngineer(Person):
    name = "lead_engineer"

    def constraints(self, P):
        return [
            P.feels_fast,
            P.no_errors,
            P.p99_acceptable,
        ]
```

**Run:**
```bash
usersim judge --perceptions perceptions.json --users users/*.py
```

```
  ✓ lead_engineer    score=1.000
  ✓ casual_user      score=1.000
  ✗ ops_engineer     score=0.667 — P.p99_acceptable

  2/3 satisfied  (score 88.9%)
```

---

## Getting started

→ **[QUICKSTART.md](QUICKSTART.md)** — build a working simulation from scratch in ~10 minutes

---

## Key concepts

### Instrumentation (Layer 1)

Runs in your application's language. The only contract: write a JSON file matching the schema below. Can be a script you call in CI, a test hook, a benchmark runner — whatever fits your workflow.

```json
{
  "schema":   "usersim.metrics.v1",
  "scenario": "optional-name",
  "metrics":  { "key": value, ... }
}
```

### Perceptions (Layer 2)

Translates raw numbers into meaningful boolean/numeric facts. Python is recommended — we ship a library of helpers. But this layer can be any executable that reads `metrics.json` from stdin and writes `perceptions.json` to stdout.

```python
from usersim.perceptions.library import threshold, ratio, flag, in_range, normalise
```

### Users (Layer 3)

Each user is a Python class. The `constraints()` method returns a list of Z3 expressions. Every constraint must be satisfiable for the user to be "satisfied". Partial satisfaction is scored (fraction of passing constraints).

```python
from usersim.judgement.z3_compat import And, Or, Not, Implies
```

| Expression | Meaning |
|---|---|
| `P.fact` | fact must be true |
| `Not(P.fact)` | fact must be false |
| `And(P.a, P.b)` | both must hold |
| `Or(P.a, P.b)` | at least one must hold |
| `Implies(P.a, P.b)` | if a then b (vacuously true when a is false) |
| `P.score >= RealVal(0.8)` | numeric threshold |

### Scenarios

Run the same users against multiple scenarios (e.g. "low load" vs "peak load", "small dataset" vs "large dataset"). The matrix output shows who is satisfied under which conditions.

---

## CLI reference

```bash
# Scaffold a new project
usersim init [directory]

# Judge: run Z3 against an existing perceptions.json
usersim judge \
  --perceptions perceptions.json \
  --users       users/*.py \
  --out         results.json

# Judge matrix: directory of perceptions files × all users
usersim judge \
  --perceptions-dir perceptions/ \
  --users           users/*.py

# Full pipeline: run perceptions script, then judge
usersim run \
  --metrics     metrics.json \
  --perceptions perceptions.py \
  --users       users/*.py

# Generate HTML report
usersim report --results results.json --out report.html
```

---

## Example

[`examples/graph-viz/`](examples/graph-viz/) shows usersim applied to a force-directed graph visualization. The instrumentation is JavaScript (measuring layout physics), the perceptions translate geometry into legibility facts, and two personas (CTO, Staff Engineer) express what they need to understand the graph. This is the real-world case that motivated usersim's creation.

---

## Z3 on ARM64

`z3-solver` isn't packaged for all ARM64 Python versions (Apple Silicon, Raspberry Pi). usersim ships a pure-Python fallback that handles all the constraint patterns above. Install `usersim[z3]` when possible; the fallback activates automatically otherwise.

---

## License

MIT
