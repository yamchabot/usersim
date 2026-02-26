"""
Scaffold a new usersim project with the minimal file set.
Called by `usersim init [DIR]`.
"""
from pathlib import Path

_PERCEPTIONS_PY = '''\
"""
perceptions.py — extract domain-meaningful observations from raw metrics.

A domain expert looks at the instrumentation output and decides what matters.
Return numeric values wherever possible — different users will apply their
own thresholds in their constraint files.  Boolean perceptions are fine for
categorical facts (job completed, feature enabled) but avoid using them to
encode performance judgements that different users would disagree on.

usersim calls compute() in-process when running the pipeline.
The __main__ block at the bottom lets you also run this file directly:

    python3 perceptions.py < metrics.json    # manual testing
    cat metrics.json | python3 perceptions.py | python3 -m json.tool
"""
from usersim.perceptions.library import run_perceptions


def compute(metrics: dict, **_) -> dict:
    """
    Return a dict of {fact_name: bool | float | int}.
    Each key becomes an attribute on P in your user constraint files.
    """
    return {
        # ── Replace these with observations relevant to your application ────
        # Numeric — users apply their own thresholds
        "response_time_ms": metrics.get("response_time_ms", 0.0),
        "error_rate":       metrics.get("error_count", 0) / max(metrics.get("total_requests", 1), 1),

        # Boolean — only for definitionally true/false facts
        "service_available": bool(metrics.get("service_up", True)),
    }


if __name__ == "__main__":
    run_perceptions(compute)
'''

_USER_PY = '''\
"""
users/example_user.py — a simulated user persona.

Rename this file and the class.  Add as many user files as you need —
one per distinct persona (power user, casual user, ops engineer, etc.).
"""
from usersim import Person
from usersim.judgement.z3_compat import Implies


class ExampleUser(Person):
    name        = "example_user"
    description = "A user who cares about speed and reliability."

    def constraints(self, P):
        """
        Return a list of constraints this user needs satisfied.
        P.<fact> gives access to each fact from perceptions.py.
        All constraints must pass for this user to be "satisfied".
        """
        return [
            P.is_fast,
            P.has_no_errors,
            Implies(P.is_fast, P.is_available),
        ]
'''

_INSTRUMENTATION_PY = '''\
"""
instrumentation.py — collect metrics from your application.

Run by usersim via the command in usersim.yaml.  Write JSON to stdout.
USERSIM_SCENARIO env var is set to the current scenario name.

Replace the stub below with real measurements from your app.
"""
import json
import os
import sys

scenario = os.environ.get("USERSIM_SCENARIO", "default")

# TODO: replace with real measurements
metrics = {
    "response_time_ms": 120,
    "error_count":      0,
    "service_up":       True,
}

json.dump({
    "schema":   "usersim.metrics.v1",
    "scenario": scenario,
    "metrics":  metrics,
}, sys.stdout)
'''

_CONFIG_YAML = '''\
# usersim.yaml — project configuration
#
# Run the full simulation pipeline with: usersim run
# Add that to your Makefile, npm scripts, pyproject.toml, Bazel, etc.
#
# Simulation files live in usersim/ to keep them separate from your app.
# Commands run from the project root, so instrumentation.py can import
# your application code directly.
version: 1

# Shell command to collect metrics from your app (any language).
# Reads nothing; writes metrics JSON to stdout.
# USERSIM_SCENARIO env var is set to the current scenario name.
instrumentation: "python3 instrumentation.py"

# Shell command (or Python file with compute()) for perceptions.
# Reads metrics JSON from stdin, writes perceptions JSON to stdout.
# Python files with a compute() function are called in-process (faster).
perceptions: "python3 usersim/perceptions.py"

# User persona files.  Glob patterns supported.
users:
  - usersim/users/*.py

# Scenarios to run.  Each triggers one instrumentation + perceptions call.
# Use USERSIM_SCENARIO in your instrumentation to vary the conditions.
scenarios:
  - default

# Optional: where to save output.  Remove to write to stdout only.
output:
  results: usersim/results.json
  report:  usersim/report.html
'''

_GITIGNORE = '''\
usersim/results.json
usersim/report.html
__pycache__/
*.pyc
.usersim_cache/
'''


def init_project(target: Path) -> None:
    target   = target.resolve()
    sim_dir  = target / "usersim"
    users_dir = sim_dir / "users"
    users_dir.mkdir(parents=True, exist_ok=True)

    files = {
        target   / "usersim.yaml":           _CONFIG_YAML,
        target   / "instrumentation.py":     _INSTRUMENTATION_PY,
        sim_dir  / "perceptions.py":         _PERCEPTIONS_PY,
        users_dir / "example_user.py":       _USER_PY,
        target   / ".gitignore":             _GITIGNORE,
    }

    created = []
    skipped = []
    for path, content in files.items():
        if path.exists():
            skipped.append(path.relative_to(target))
        else:
            path.write_text(content)
            created.append(path.relative_to(target))

    print(f"\n✓ usersim project initialised in {target}\n")
    for f in created:
        print(f"  created  {f}")
    for f in skipped:
        print(f"  skipped  {f}  (already exists)")

    print(f"""
Layout:

  instrumentation.py       ← measures your app; lives at project root
  usersim/perceptions.py   ← translates metrics → domain observations
  usersim/users/*.py       ← simulated user personas
  usersim.yaml             ← pipeline config

Next steps:

  1. Edit  instrumentation.py  — replace the stub with real measurements.
     Write metrics JSON to stdout.  USERSIM_SCENARIO env var is set.

  2. Edit  usersim/perceptions.py  — return numeric domain observations.
     Different users will apply their own thresholds in step 3.

  3. Edit  usersim/users/example_user.py  — add Z3 numeric constraints.
     Add more user files (one per persona) as needed.

  4. Run:  usersim run

  Add `usersim run` to your Makefile, package.json, or CI pipeline.
""")
