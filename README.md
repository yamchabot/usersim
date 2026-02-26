# usersim

**Test whether your application satisfies real users — not just whether it works.**

Most test suites check correctness: *did this return 200? did this render?*  
usersim checks satisfaction: *would the CTO understand this screen? would the on-call engineer trust this dashboard?*

You define simulated personas. You express what each one needs as logical constraints. usersim measures whether your application satisfies them — automatically, on every build.

---

## How it works

Declare your pipeline in `usersim.yaml`. Run one command.

```bash
usersim run
```

usersim reads the config, runs three stages in sequence, and reports which simulated users are satisfied across all your scenarios:

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1 — Instrumentation     (your language)              │
│                                                             │
│  A shell command that collects metrics from your app        │
│  and writes metrics JSON to stdout.                         │
└───────────────────────┬─────────────────────────────────────┘
                        │  { "response_ms": 240, "errors": 0 }
                        ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 2 — Perceptions         (any language)               │
│                                                             │
│  A script that translates numbers into what a human         │
│  would perceive.  Reads stdin, writes to stdout.            │
└───────────────────────┬─────────────────────────────────────┘
                        │  { "loads_fast": true, "no_errors": true }
                        ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 3 — Judgement           (Z3, controlled by usersim)  │
│                                                             │
│  Evaluates each persona's logical constraints.              │
│  Reports who is satisfied and why.                          │
└─────────────────────────────────────────────────────────────┘
```

**You write layers 1 and 2 in whatever language fits your project. We handle layer 3.**

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
# edit instrumentation.*, perceptions.py, users/*.py
usersim run       # run the full pipeline
```

See [QUICKSTART.md](QUICKSTART.md) for a full walkthrough (~10 minutes).

---

## Configuration

`usersim.yaml` is the single source of truth for your simulation:

```yaml
version: 1

# Shell command to run instrumentation (any language).
# usersim runs this, reads metrics JSON from its stdout.
# USERSIM_SCENARIO env var is set to the current scenario name.
instrumentation: "node instrumentation.js"

# Shell command (or Python file with compute()) for perceptions.
# Reads metrics JSON from stdin, writes perceptions JSON to stdout.
perceptions: "python3 perceptions.py"

# User persona files. Glob patterns supported.
users:
  - users/*.py

# Run the pipeline once per scenario.
scenarios:
  - default
  - peak_load
  - degraded

# Optional: save output to files.
output:
  results: results.json
  report:  report.html
```

For each scenario, usersim:
1. Runs `instrumentation` with `USERSIM_SCENARIO=<name>` in the environment
2. Pipes its output to `perceptions` on stdin
3. Runs judgement in-process and collects results

If there are multiple scenarios, the final output is a matrix of person × scenario results.

---

## Integrating with your build system

`usersim run` is a single command with no arguments. Drop it anywhere:

**Makefile:**
```makefile
test-ux:
    usersim run
```

**package.json:**
```json
"scripts": {
    "test:ux": "usersim run"
}
```

**pyproject.toml:**
```toml
[tool.hatch.envs.default.scripts]
test-ux = "usersim run"
```

**GitHub Actions:**
```yaml
- run: pip install usersim
- run: usersim run --out results.json
- uses: actions/upload-artifact@v4
  with: { name: usersim-report, path: report.html }
```

Exit code is 0 when all users are satisfied across all scenarios, 1 otherwise.

---

## Key concepts

### Instrumentation (Layer 1)

Runs in your application's language. The only contract: write a JSON object to stdout:

```json
{
  "schema":   "usersim.metrics.v1",
  "scenario": "peak_load",
  "metrics":  { "response_ms": 480, "error_rate": 0.05 }
}
```

`USERSIM_SCENARIO` is available in the environment so one script can serve all scenarios:

```python
scenario = os.environ.get("USERSIM_SCENARIO", "default")
metrics  = measure_for_scenario(scenario)
```

### Perceptions (Layer 2)

Translates raw numbers into human-meaningful facts. Python files with a `compute()` function are called in-process (faster). Any other executable is spawned with metrics JSON on stdin:

```python
from usersim.perceptions.library import threshold, ratio, flag, in_range, normalise

def compute(metrics: dict, scenario: str = "default", **kwargs) -> dict:
    return {
        "feels_fast":  threshold(metrics, "response_ms", max=200),
        "no_errors":   threshold(metrics, "error_rate",  max=0.01),
    }
```

### Users (Layer 3)

Each user is a Python class. `constraints()` returns a list of Z3 expressions:

```python
from usersim import Person
from usersim.judgement.z3_compat import Implies

class OpsEngineer(Person):
    name = "ops_engineer"

    def constraints(self, P):
        return [
            P.no_errors,
            P.high_uptime,
            Implies(P.cache_is_warm, P.feels_fast),
        ]
```

| Expression | Meaning |
|---|---|
| `P.fact` | fact must be true |
| `Not(P.fact)` | fact must be false |
| `Implies(P.a, P.b)` | if a then b |
| `And(P.a, P.b)` | both must hold |
| `Or(P.a, P.b)` | at least one must hold |

---

## CLI reference

```bash
usersim init [DIR]               # scaffold a new project
usersim run                      # run the full pipeline (reads usersim.yaml)
usersim run --scenario peak_load # run one specific scenario
usersim run --out results.json   # save results to file (also stdout)
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

---

## Example

[`examples/graph-viz/`](examples/graph-viz/) shows usersim applied to a force-directed graph visualization. Instrumentation is JavaScript (synthetic layout metrics), perceptions translate geometry into legibility facts, and two personas evaluate three scenarios. Run it with:

```bash
cd examples/graph-viz
usersim run
```

---

## Z3 on ARM64

`z3-solver` isn't packaged for all ARM64 Python versions (Apple Silicon, Raspberry Pi). usersim ships a pure-Python fallback that handles all constraint patterns above. Install `usersim[z3]` when possible; the fallback activates automatically otherwise.

---

## License

MIT
