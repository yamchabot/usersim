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

from .z3_compat import Bool, BoolVal, Real, RealVal, Solver, sat, Z3_REAL
from .person import FactNamespace

if TYPE_CHECKING:
    from .person import Person


def _make_fact_vars(facts: dict) -> dict:
    """
    Turn the perceptions 'facts' dict into Z3 variables / values.

    - bool      → BoolVal(v)
    - int/float → named real value — repr is the variable name so violation
                  messages say "(chain_elongation >= 1.8)" not "(2.1 >= 1.8)"
    - str       → BoolVal for "true"/"false", else ignored
    """
    vars_ = {}
    assignments = {}  # name → value, for solver assertions when using real Z3
    for name, value in facts.items():
        safe = name.replace("-", "_").replace(".", "_")
        if isinstance(value, bool):
            vars_[safe] = BoolVal(value)
        elif isinstance(value, (int, float)):
            vars_[safe] = _named_real_var(safe, float(value))
            assignments[safe] = float(value)
            # Convenience: Bool alias for 0/1 metrics
            if value in (0, 1, 0.0, 1.0):
                vars_[safe + "_bool"] = BoolVal(bool(value))
        elif isinstance(value, str):
            lower = value.lower()
            if lower in ("true", "yes", "1"):
                vars_[safe] = BoolVal(True)
            elif lower in ("false", "no", "0"):
                vars_[safe] = BoolVal(False)
    vars_["_assignments"] = assignments
    return vars_


def _named_real_var(name: str, value: float):
    """
    Return a fact variable whose repr is the variable name.

    Pure-Python shim: returns an _Expr with repr=name, evaluates to value.
    Real Z3: returns a symbolic Real(name) — the actual value is injected
             into the solver via _assignments so constraints stay symbolic.
    """
    if not Z3_REAL:
        from . import z3_compat as _zc
        return _zc._Expr(lambda env, _v=value: _v, name)
    return Real(name)


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
            "person":      person.name,
            "role":        getattr(person, "role",    ""),
            "goal":        getattr(person, "goal",    ""),
            "pronoun":     getattr(person, "pronoun", "they"),
            "satisfied":   True,
            "score":       1.0,
            "constraints": [{"label": getattr(c, "_repr", None) or repr(c), "passed": True}
                            for c in constraints],
            "violations":  [],
        }

    # When using real Z3, inject variable assignments so symbolic constraints
    # evaluate correctly (Real("x") == 1.0 added per variable).
    assignments = fact_vars.pop("_assignments", {})

    passed           = 0
    violations       = []
    all_labels       = []
    constraint_results = []   # [{"label": str, "passed": bool, "antecedent_fired": bool|None}]

    import math as _math

    def _make_solver():
        s = Solver()
        if Z3_REAL and assignments:
            for var_name, val in assignments.items():
                v = _math.copysign(1e9, val) if (_math.isinf(val) or _math.isnan(val)) else val
                s.add(Real(var_name) == v)
        return s

    for i, c in enumerate(constraints):
        label = getattr(c, "_repr", None) or repr(c) or f"constraint[{i}]"
        all_labels.append(label)

        solver = _make_solver()
        solver.add(c)
        ok = solver.check() == sat

        # For Implies constraints, check whether the antecedent ever fires
        antecedent = getattr(c, "_antecedent", None)
        if antecedent is not None:
            ant_solver = _make_solver()
            ant_solver.add(antecedent)
            antecedent_fired = ant_solver.check() == sat
        else:
            antecedent_fired = None

        expr_repr = getattr(c, "_expr_repr", None) or getattr(c, "_repr", None) or repr(c)

        # When a constraint fails and Z3 is available, generate a target
        # assignment: what values would satisfy this constraint?
        target = None
        if not ok and Z3_REAL:
            target = _target_assignment(c, fact_vars, assignments)

        constraint_results.append({
            "label":             label,
            "expr":              expr_repr,
            "passed":            ok,
            "antecedent_fired":  antecedent_fired,
            "target":            target,
        })
        if ok:
            passed += 1
        else:
            violations.append(label)

    score     = passed / len(constraints)
    satisfied = len(violations) == 0

    return {
        "person":      person.name,
        "role":        getattr(person, "role",    ""),
        "goal":        getattr(person, "goal",    ""),
        "pronoun":     getattr(person, "pronoun", "they"),
        "satisfied":   satisfied,
        "score":       round(score, 4),
        "constraints": constraint_results,
        "violations":  violations,
    }


def _target_assignment(constraint, fact_vars: dict, assignments: dict) -> "dict | None":
    """
    Given a failing constraint, ask Z3 to find a satisfying assignment of the
    observed variables that would make the constraint pass.

    Returns a dict like:
      {"error_count": {"current": 8, "target": 2, "direction": "decrease"}}
    or None if Z3 can't find one (e.g. constraint is unsatisfiable in general).
    """
    if not Z3_REAL:
        return None
    try:
        import re as _re
        _Z3K = {"If", "And", "Or", "Not", "Implies", "True", "False",
                "true", "false", "and", "or", "not"}
        _VRE = _re.compile(r'\b([a-z][a-z0-9_]*)\b')
        expr_repr = getattr(constraint, "_expr_repr", None) or repr(constraint)
        var_names = [m for m in _VRE.findall(expr_repr)
                     if m not in _Z3K and len(m) > 2 and m in fact_vars]

        if not var_names:
            return None

        s = Solver()
        s.add(constraint)
        # Add the constraint itself as the only thing to satisfy
        # Let the observed variables be free (Z3 finds satisfying values)
        if s.check() != sat:
            return None  # constraint is fundamentally unsatisfiable

        model = s.model()
        result = {}
        for name in var_names:
            current = assignments.get(name)
            if current is None:
                continue
            z3_val = model.eval(Real(name), model_completion=True)
            try:
                target_val = float(z3_val.as_fraction()) if hasattr(z3_val, "as_fraction") else float(str(z3_val))
            except Exception:
                continue
            if abs(target_val - current) < 1e-9:
                continue  # same value, not informative
            direction = "decrease" if target_val < current else "increase"
            result[name] = {
                "current":   round(current, 4) if isinstance(current, float) else current,
                "target":    round(target_val, 4),
                "direction": direction,
            }
        return result if result else None
    except Exception:
        return None


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
    path    = perceptions_doc.get("path", "unknown")
    person_name = perceptions_doc.get("person", None)
    if person_name == "all":
        person_name = None

    persons = _load_persons(user_files, target_name=person_name)

    person_results = []
    for person in persons:
        result = evaluate_person(person, facts)
        result["path"] = path
        person_results.append(result)

    return {
        "schema":   RESULTS_SCHEMA,
        "path": path,
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
    Returns a matrix of person × path results.
    """
    perceptions_dir = Path(perceptions_dir)
    files = sorted(perceptions_dir.glob("*.json"))

    all_results = []
    for pf in files:
        with open(pf) as f:
            doc = json.load(f)
        facts    = doc.get("facts", {})
        path = doc.get("path", pf.stem)
        persons  = _load_persons(user_files)
        for person in persons:
            r = evaluate_person(person, facts)
            r["path"] = path
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

    import sys as _sys
    persons = []
    for path in user_files:
        path = Path(path)
        # Add the file's directory to sys.path so it can import siblings
        # (e.g. `from judgement import Person`) without being a package.
        script_dir = str(path.parent)
        if script_dir not in _sys.path:
            _sys.path.insert(0, script_dir)
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
