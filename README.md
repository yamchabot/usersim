# usersim

**Test whether your application satisfies real users — not just whether it works.**

Most test suites check correctness: *did this return 200? did this render?*  
usersim checks satisfaction: *would the CTO understand this screen? would the on-call engineer trust this dashboard?*

You define simulated personas. You express what each one needs as logical constraints. usersim measures whether your application satisfies them — automatically, on every build.

---

## How it works

Three layers, connected as a Unix pipeline. Each layer reads JSON from stdin and writes JSON to stdout.

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1 — Instrumentation     (your language)              │
│                                                             │
│  Collect raw measurements from your app.                    │
│  Write metrics JSON to stdout.                              │
└───────────────────────┬─────────────────────────────────────┘
                        │  { "load_time_ms": 240, "errors": 0 }
                        ▼  (pipe)
┌─────────────────────────────────────────────────────────────┐
│  Layer 2 — Perceptions         (any language)               │
│                                                             │
│  Read metrics JSON from stdin.                              │
│  Translate numbers into what a human would perceive.        │
│  Write perceptions JSON to stdout.                          │
└───────────────────────┬─────────────────────────────────────┘
                        │  { "loads_fast": true, "no_errors": true }
                        ▼  (pipe)
┌─────────────────────────────────────────────────────────────┐
│  Layer 3 — Judgement           (Z3, controlled by usersim)  │
│                                                             │
│  Read perceptions JSON from stdin.                          │
│  Check each persona's logical constraints.                  │
│  Write results JSON to stdout.  Human summary to stderr.    │
└─────────────────────────────────────────────────────────────┘
```

**You write layers 1 and 2. We handle layer 3.**

```bash
python3 instrumentation.py | python3 perceptions.py | usersim judge --users users/*.py
```

Instrumentation runs in your app's language. Perceptions can be anything; we ship a Python helper library. Judgement always runs through Z3 — usersim owns that layer so the constraint evaluation is sound and consistent.

---

## Install

```bash
pip install usersim          # includes a pure-Python Z3 fallback
pip install "usersim[z3]"    # with the real Z3 solver (recommended)
```

---

## A taste

**Instrumentation** — measure your app, write metrics JSON to stdout:
```python
import json, sys

metrics = {
    "response_ms": 180,
    "error_rate":  0.002,
    "p99_ms":      420,
}
json.dump({"schema": "usersim.metrics.v1", "scenario": "api_under_load", "metrics": metrics}, sys.stdout)
```

**Perceptions** — read metrics from stdin, write perceptions to stdout (`perceptions.py`):
```python
import json, sys
from usersim.perceptions.library import threshold

def compute(metrics, **_):
    return {
        "feels_fast":     threshold(metrics, "response_ms", max=200),
        "no_errors":      threshold(metrics, "error_rate",  max=0.01),
        "p99_acceptable": threshold(metrics, "p99_ms",      max=500),
    }

# Called in-process by usersim run, or as a subprocess via shell pipe
if __name__ == "__main__":
    doc = json.load(sys.stdin)
    facts = compute(doc["metrics"])
    json.dump({"schema": "usersim.perceptions.v1", "scenario": doc.get("scenario", "default"),
               "person": "all", "facts": facts}, sys.stdout)
```

**Users** — express what each persona needs (`users/lead_engineer.py`):
```python
from usersim import Person

class LeadEngineer(Person):
    name = "lead_engineer"

    def constraints(self, P):
        return [
            P.feels_fast,
            P.no_errors,
            P.p99_acceptable,
        ]
```

**Run — full pipeline with shell pipes:**
```bash
python3 instrumentation.py | python3 perceptions.py | usersim judge --users users/*.py
```

**Or let usersim drive the perceptions step:**
```bash
python3 instrumentation.py | usersim run --perceptions perceptions.py --users users/*.py
```

Results JSON goes to stdout. Human summary goes to stderr:
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

Runs in your application's language. The only contract: write a JSON object to stdout matching this schema:

```json
{
  "schema":   "usersim.metrics.v1",
  "scenario": "optional-name",
  "metrics":  { "key": value, ... }
}
```

Can be a script you call in CI, a test hook, a benchmark runner — whatever fits your workflow. The downstream layers read it from a pipe; no files needed.

### Perceptions (Layer 2)

Reads metrics JSON from stdin, translates raw numbers into human-meaningful facts, writes perceptions JSON to stdout. Python is recommended — we ship a library of helpers:

```python
from usersim.perceptions.library import threshold, ratio, flag, in_range, normalise
```

This layer can also be any other executable (Node, Go, Ruby…) as long as it respects the stdin → stdout JSON contract.

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

Run the same users against multiple scenarios (e.g. "low load" vs "peak load"). The matrix output shows who is satisfied under which conditions.

---

## CLI reference

```bash
# Scaffold a new project
usersim init [directory]

# Full pipeline: usersim drives perceptions + judgement
# metrics JSON read from stdin (pipe your instrumentation in)
python3 instrumentation.py | usersim run \
  --perceptions perceptions.py \
  --users       users/*.py

# Judgement only: pipe perceptions JSON in from stdin
python3 perceptions.py | usersim judge --users users/*.py

# Judgement from a file (backward compat)
usersim judge --perceptions perceptions.json --users users/*.py

# Matrix mode: directory of perceptions files × all users
usersim judge --perceptions-dir perceptions/ --users users/*.py

# Save results to a file instead of stdout
python3 instrumentation.py | usersim run \
  --perceptions perceptions.py \
  --users       users/*.py \
  --out         results.json

# Generate HTML report (pipe results in, or use --results file)
usersim run ... | usersim report
usersim report --results results.json --out report.html
```

**Flags available on all commands:**
- `--out FILE` — write JSON output to a file (default: stdout)
- `--quiet` — suppress human summary on stderr (`run` and `judge` only)

---

## Example

[`examples/graph-viz/`](examples/graph-viz/) shows usersim applied to a force-directed graph visualization. The instrumentation is JavaScript (measuring layout physics), the perceptions translate geometry into legibility facts, and two personas (CTO, Staff Engineer) express what they need to understand the graph. This is the real-world case that motivated usersim's creation.

---

## Z3 on ARM64

`z3-solver` isn't packaged for all ARM64 Python versions (Apple Silicon, Raspberry Pi). usersim ships a pure-Python fallback that handles all the constraint patterns above. Install `usersim[z3]` when possible; the fallback activates automatically otherwise.

---

## License

MIT
