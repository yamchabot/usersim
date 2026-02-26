"""
Scaffold a new usersim project with the minimal file set.
Called by `usersim init [DIR]`.
"""
from pathlib import Path

_PERCEPTIONS_PY = '''\
"""
perceptions.py — translate raw metrics into human-meaningful boolean facts.

This file is called by usersim with your metrics.json on stdin (or directly
imported if it defines a compute() function).

Edit the facts below to match what matters for your users.
"""
from usersim.perceptions.library import threshold, flag, in_range


def compute(metrics: dict, scenario: str = "default", person: str = None) -> dict:
    """
    Return a dict of {fact_name: bool | float}.
    Each fact becomes a variable that person constraint files can reference.
    """
    return {
        # ── Replace these with facts that matter for your app ───────────────
        "is_fast":       threshold(metrics, "response_time_ms", max=300),
        "has_no_errors": metrics.get("error_count", 0) == 0,
        "is_available":  flag(metrics, "service_up", default=True),
    }
'''

_USER_PY = '''\
"""
users/example_user.py — a simulated user persona.

Rename this file and the class.  Add as many user files as you need.
"""
from usersim import Person
from usersim.judgement.z3_compat import And, Implies


class ExampleUser(Person):
    name        = "example_user"
    description = "A power user who cares about speed and reliability."

    def constraints(self, P):
        """
        P gives access to each fact produced by perceptions.py as an attribute.
        Return a list of Z3 expressions.  All must be satisfiable for this user
        to be considered satisfied.
        """
        return [
            P.is_fast,
            P.has_no_errors,
            Implies(P.is_fast, P.is_available),
        ]
'''

_INSTRUMENTATION_JS = '''\
/**
 * instrumentation.js
 *
 * Collect metrics from your application and write them to metrics.json.
 * This file runs in your application\'s language — edit freely.
 *
 * Output format:
 * {
 *   "schema":   "usersim.metrics.v1",
 *   "scenario": "my_scenario",
 *   "metrics":  { ... }
 * }
 */
const fs = require("fs");

// TODO: replace with real measurements from your application
const metrics = {
  response_time_ms: 120,
  error_count:      0,
  service_up:       true,
};

const output = {
  schema:   "usersim.metrics.v1",
  scenario: process.env.USERSIM_SCENARIO || "default",
  metrics,
};

fs.writeFileSync("metrics.json", JSON.stringify(output, null, 2));
console.log(`[instrumentation] wrote ${Object.keys(metrics).length} metrics`);
'''

_CONFIG_YAML = '''\
# usersim.yaml — project configuration
name: my-project
version: 1

instrumentation:
  # Command to run your instrumentation (any language).
  # It should write metrics.json to the current directory.
  command: "node instrumentation.js"
  output:  metrics.json

perceptions:
  # Python script (or any executable) that reads metrics and outputs facts.
  script: perceptions.py

users:
  - users/example_user.py

scenarios:
  - name: default

output:
  results: results.json
  report:  report.html
'''

_GITIGNORE = '''\
*.json
*.html
__pycache__/
*.pyc
.usersim_cache/
'''


def init_project(target: Path) -> None:
    target = target.resolve()
    users_dir = target / "users"
    users_dir.mkdir(parents=True, exist_ok=True)

    files = {
        target / "usersim.yaml":             _CONFIG_YAML,
        target / "perceptions.py":           _PERCEPTIONS_PY,
        target / "instrumentation.js":       _INSTRUMENTATION_JS,
        users_dir / "example_user.py":       _USER_PY,
        target / ".gitignore":               _GITIGNORE,
    }

    created = []
    skipped = []
    for path, content in files.items():
        if path.exists():
            skipped.append(path.name)
        else:
            path.write_text(content)
            created.append(path.relative_to(target.parent))

    print(f"\n✓ usersim project initialised in {target}\n")
    for f in created:
        print(f"  created  {f}")
    for f in skipped:
        print(f"  skipped  {f}  (already exists)")

    print(f"""
Next steps:

  1. Edit  instrumentation.js  to collect metrics from your app
     Output: metrics.json with schema "usersim.metrics.v1"

  2. Edit  perceptions.py  to translate metrics → human facts
     Each fact is a bool or float that your users reason about

  3. Edit  users/example_user.py  to define constraint formulas
     Add more user files — one per persona

  4. Run your instrumentation, then:
     usersim judge --perceptions perceptions.json --users users/*.py

  5. Generate a report:
     usersim report --results results.json
""")
