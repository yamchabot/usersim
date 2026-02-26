"""
Scaffold a new usersim project with the minimal file set.
Called by `usersim init [DIR]`.
"""
from pathlib import Path

_PERCEPTIONS_PY = '''\
"""
perceptions.py — translate raw metrics into human-meaningful boolean facts.

Receives metrics from usersim and returns a dict of facts that user
constraint files reason about.  Edit to match what matters in your app.
"""
from usersim.perceptions.library import threshold, flag, in_range


def compute(metrics: dict, scenario: str = "default", **kwargs) -> dict:
    """
    Return a dict of {fact_name: bool | float}.
    Each fact becomes an attribute on P in your user constraint files.
    """
    return {
        # ── Replace these with facts relevant to your application ───────────
        "is_fast":       threshold(metrics, "response_time_ms", max=300),
        "has_no_errors": metrics.get("error_count", 0) == 0,
        "is_available":  flag(metrics, "service_up", default=True),
    }
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
version: 1

# Shell command to collect metrics from your app (any language).
# usersim runs this and reads metrics JSON from its stdout.
# USERSIM_SCENARIO env var is set to the current scenario name.
instrumentation: "python3 instrumentation.py"

# Shell command (or Python file) to translate metrics into perceptions.
# Reads metrics JSON from stdin, writes perceptions JSON to stdout.
# Python files with a compute() function are called in-process (faster).
perceptions: "python3 perceptions.py"

# User persona files.  Glob patterns supported.
users:
  - users/*.py

# Scenarios to run.  Each triggers one instrumentation + perceptions call.
# Use USERSIM_SCENARIO in your instrumentation to vary the conditions.
scenarios:
  - default

# Optional: where to save output.  Remove to write to stdout only.
output:
  results: results.json
  report:  report.html
'''

_GITIGNORE = '''\
results.json
report.html
__pycache__/
*.pyc
.usersim_cache/
'''


def init_project(target: Path) -> None:
    target = target.resolve()
    users_dir = target / "users"
    users_dir.mkdir(parents=True, exist_ok=True)

    files = {
        target / "usersim.yaml":           _CONFIG_YAML,
        target / "instrumentation.py":     _INSTRUMENTATION_PY,
        target / "perceptions.py":         _PERCEPTIONS_PY,
        users_dir / "example_user.py":     _USER_PY,
        target / ".gitignore":             _GITIGNORE,
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
Next steps:

  1. Edit  instrumentation.py  to collect real metrics from your app.
     Write metrics JSON to stdout.  USERSIM_SCENARIO is set in env.

  2. Edit  perceptions.py  to translate metrics → human-readable facts.
     Each fact is a bool or float that your user personas reason about.

  3. Edit  users/example_user.py  (or add more files, one per persona).

  4. Run the full pipeline:

       usersim run

  Add `usersim run` to your Makefile, package.json, or CI pipeline.
  It reads usersim.yaml and handles the rest automatically.
""")
