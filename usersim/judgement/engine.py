"""
Judgement engine — evaluates perceptions against user constraints using Z3.

Input:  perceptions JSON  { facts: {name: bool|float} }
        user files        [Person subclasses]
Output: results JSON      { satisfied: bool, score: float, violations: [...] }

The perceptions input can be supplied as:
  - a file path (str or Path)
  - the string "-"  → read from stdin
  - a dict          → used directly (for in-process pipeline)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from .z3_compat import Bool, BoolVal, Real, RealVal, Solver, sat
from .person import FactNamespace

if TYPE_CHECKING:
    from .person import Person


def _make_fact_vars(facts: dict) -> dict:
    """
    Turn the perceptions 'facts' dict into Z3 variables / values.

    - bool      → BoolVal(v)
    - int/float → RealVal(v)
    - str       → BoolVal for "true"/"false", else ignored
    """
    vars_ = {}
    for name, value in facts.items():
        safe = name.replace("-", "_").replace(".", "_")
        if isinstance(value, bool):
            vars_[safe] = BoolVal(value)
        elif isinstance(value, (int, float)):
            vars_[safe] = RealVal(float(value))
            # Convenience: Bool alias for 0/1 metrics
            if value in (0, 1, 0.0, 1.0):
                vars_[safe + "_bool"] = BoolVal(bool(value))
        elif isinstance(value, str):
            lower = value.lower()
            if lower in ("true", "yes", "1"):
                vars_[safe] = BoolVal(True)
            elif lower in ("false", "no", "0"):
                vars_[safe] = BoolVal(False)
    return vars_


def evaluate_person(person: "Person", facts: dict) -> dict:
    """
    Run Z3 constraint check for one person against one perceptions dict.

    Returns:
        {
            "person":     str,
            "satisfied":  bool,
            "score":      float,
            "violations": [str],
        }
    """
    fact_vars = _make_fact_vars(facts)
    namespace = FactNamespace(fact_vars)

    try:
        constraints = person.constraints(namespace)
    except AttributeError as e:
        return {
            "person":     person.name,
            "satisfied":  False,
            "score":      0.0,
            "violations": [f"AttributeError in constraints(): {e}"],
            "error":      str(e),
        }

    if not constraints:
        return {
            "person":     person.name,
            "satisfied":  True,
            "score":      1.0,
            "violations": [],
        }

    passed     = 0
    violations = []
    for i, c in enumerate(constraints):
        solver = Solver()
        solver.add(c)
        if solver.check() == sat:
            passed += 1
        else:
            label = getattr(c, "_repr", None) or repr(c) or f"constraint[{i}]"
            violations.append(label)

    score     = passed / len(constraints)
    satisfied = len(violations) == 0

    return {
        "person":     person.name,
        "satisfied":  satisfied,
        "score":      round(score, 4),
        "violations": violations,
    }


def _load_perceptions_doc(source) -> dict:
    """
    Load a perceptions document from:
      - a dict        → returned as-is
      - "-"           → read JSON from stdin
      - a file path   → read and parse JSON
    """
    if isinstance(source, dict):
        return source
    if source == "-" or source is None:
        return json.load(sys.stdin)
    path = Path(source)
    with open(path) as f:
        return json.load(f)


def _evaluate(perceptions_doc: dict, user_files: list) -> dict:
    """
    Core evaluation: check all persons against one perceptions document.
    Returns the results dict.  Does not write any output.
    """
    from usersim.schema import RESULTS_SCHEMA

    facts       = perceptions_doc["facts"]
    scenario    = perceptions_doc.get("scenario", "unknown")
    person_name = perceptions_doc.get("person", None)
    if person_name == "all":
        person_name = None

    persons = _load_persons(user_files, target_name=person_name)

    person_results = []
    for person in persons:
        result = evaluate_person(person, facts)
        result["scenario"] = scenario
        person_results.append(result)

    return {
        "schema":   RESULTS_SCHEMA,
        "scenario": scenario,
        "results":  person_results,
        "summary": {
            "total":     len(person_results),
            "satisfied": sum(1 for r in person_results if r["satisfied"]),
            "score":     round(
                sum(r["score"] for r in person_results) / max(len(person_results), 1), 4
            ),
        },
    }


def run_judgement(
    perceptions: "str | Path | dict",
    user_files: list,
    output_path: "str | Path | None" = None,
) -> dict:
    """
    Top-level judgement runner.

    Args:
        perceptions:  perceptions JSON as a file path, "-" (stdin), or dict
        user_files:   list of paths to Python user files (Person subclasses)
        output_path:  write results.json here; None → write JSON to stdout

    Returns the full results dict.
    """
    from usersim.schema import validate_perceptions

    doc = _load_perceptions_doc(perceptions)
    validate_perceptions(doc)
    output = _evaluate(doc, user_files)
    _write_output(output, output_path)
    return output


def run_matrix(
    perceptions_dir: "str | Path",
    user_files: list,
    output_path: "str | Path | None" = None,
) -> dict:
    """
    Run judgement across all perceptions JSON files in a directory.
    Returns a matrix of person × scenario results.
    """
    perceptions_dir = Path(perceptions_dir)
    files = sorted(perceptions_dir.glob("*.json"))

    all_results = []
    for pf in files:
        with open(pf) as f:
            doc = json.load(f)
        facts    = doc.get("facts", {})
        scenario = doc.get("scenario", pf.stem)
        persons  = _load_persons(user_files)
        for person in persons:
            r = evaluate_person(person, facts)
            r["scenario"] = scenario
            all_results.append(r)

    satisfied = sum(1 for r in all_results if r["satisfied"])
    output = {
        "schema":  "usersim.matrix.v1",
        "results": all_results,
        "summary": {
            "total":     len(all_results),
            "satisfied": satisfied,
            "score":     round(satisfied / max(len(all_results), 1), 4),
        },
    }

    _write_output(output, output_path)
    return output


def _write_output(data: dict, output_path) -> None:
    """Write JSON to a file if output_path given, otherwise stdout."""
    text = json.dumps(data, indent=2)
    if output_path:
        Path(output_path).write_text(text)
    else:
        print(text)


# ── Internal helpers ───────────────────────────────────────────────────────────

def _load_persons(user_files: list, target_name: str | None = None) -> list:
    """
    Import each user file and return instances of all Person subclasses found.
    """
    import importlib.util
    from .person import Person as PersonBase

    persons = []
    for path in user_files:
        path = Path(path)
        spec = importlib.util.spec_from_file_location(path.stem, path)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for attr in vars(mod).values():
            if (
                isinstance(attr, type)
                and issubclass(attr, PersonBase)
                and attr is not PersonBase
            ):
                instance = attr()
                if target_name is None or instance.name == target_name:
                    persons.append(instance)

    return persons
