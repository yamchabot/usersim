"""
Judgement engine — evaluates perceptions against user constraints using Z3.

Input:  perceptions.json  { facts: {name: bool|float} }
        user files        [Person subclasses]
Output: results.json      { satisfied: bool, score: float, violations: [...] }
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from .z3_compat import Bool, BoolVal, Real, RealVal, Solver, sat
from .person import FactNamespace

if TYPE_CHECKING:
    from .person import Person


def _make_fact_vars(facts: dict) -> dict:
    """
    Turn the perceptions.json 'facts' dict into Z3 variables / values.

    - bool  → BoolVal(v)
    - int/float → RealVal(v)   (also creates Bool(name) aliases for 0/1 values)
    - str   → BoolVal for "true"/"false", else ignored
    """
    from .z3_compat import And, Implies

    vars_ = {}
    for name, value in facts.items():
        safe = name.replace("-", "_").replace(".", "_")
        if isinstance(value, bool):
            vars_[safe] = BoolVal(value)
        elif isinstance(value, (int, float)):
            vars_[safe] = RealVal(float(value))
            # Convenience: also a Bool version for 0/1 metrics
            if value in (0, 1, 0.0, 1.0):
                vars_[safe + "_bool"] = BoolVal(bool(value))
        elif isinstance(value, str):
            lower = value.lower()
            if lower in ("true", "yes", "1"):
                vars_[safe] = BoolVal(True)
            elif lower in ("false", "no", "0"):
                vars_[safe] = BoolVal(False)
            # else: skip non-boolean strings
    return vars_


def evaluate_person(person: "Person", facts: dict) -> dict:
    """
    Run Z3 constraint check for one person against one perceptions dict.

    Returns:
        {
            "person":     str,
            "satisfied":  bool,
            "score":      float,   # fraction of constraints satisfied
            "violations": [str],   # names of failed constraints (best-effort)
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
            "person":    person.name,
            "satisfied": True,
            "score":     1.0,
            "violations": [],
        }

    # Check each constraint individually to identify violations
    passed    = 0
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


def run_judgement(
    perceptions_path: str | Path,
    user_files: list[str | Path],
    output_path: str | Path | None = None,
) -> dict:
    """
    Top-level judgement runner.

    Args:
        perceptions_path: path to perceptions.json
        user_files:       list of paths to Python user files (Person subclasses)
        output_path:      where to write results.json (None = don't write)

    Returns the full results dict.
    """
    from usersim.schema import validate_perceptions, RESULTS_SCHEMA

    perceptions_path = Path(perceptions_path)
    with open(perceptions_path) as f:
        doc = json.load(f)
    validate_perceptions(doc)

    facts    = doc["facts"]
    scenario = doc.get("scenario", "unknown")
    person_name = doc.get("person", "unknown")

    # Load person class(es) from each user file
    persons  = _load_persons(user_files, target_name=person_name)

    person_results = []
    for person in persons:
        result = evaluate_person(person, facts)
        result["scenario"] = scenario
        person_results.append(result)

    output = {
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

    if output_path:
        Path(output_path).write_text(json.dumps(output, indent=2))

    return output


def run_matrix(
    perceptions_dir: str | Path,
    user_files: list[str | Path],
    output_path: str | Path | None = None,
) -> dict:
    """
    Run judgement across all perceptions.json files in a directory.
    Returns a matrix of {person × scenario → result}.
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
            "total":         len(all_results),
            "satisfied":     satisfied,
            "score":         round(satisfied / max(len(all_results), 1), 4),
        },
    }

    if output_path:
        Path(output_path).write_text(json.dumps(output, indent=2))

    return output


# ── Internal helpers ───────────────────────────────────────────────────────────

def _load_persons(user_files: list, target_name: str | None = None) -> list:
    """
    Import each user file and return instances of all Person subclasses found.
    If target_name is given, only return persons matching that name.
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
