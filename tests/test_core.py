"""
Core framework unit tests.
"""
import json
import tempfile
from pathlib import Path

import pytest

from usersim.judgement.engine  import evaluate_person, _make_fact_vars
from usersim.judgement.person  import Person, FactNamespace
from usersim.judgement.z3_compat import BoolVal, RealVal, And, Or, Not, Implies, Solver, sat, unsat
from usersim.perceptions.library  import threshold, in_range, ratio, flag
from usersim.schema               import validate_metrics, validate_perceptions


# ── z3_compat ─────────────────────────────────────────────────────────────────

class TestZ3Compat:
    def test_bool_val_true(self):
        s = Solver(); s.add(BoolVal(True)); assert s.check() == sat

    def test_bool_val_false(self):
        s = Solver(); s.add(BoolVal(False)); assert s.check() == unsat

    def test_and_both_true(self):
        s = Solver(); s.add(And(BoolVal(True), BoolVal(True))); assert s.check() == sat

    def test_and_one_false(self):
        s = Solver(); s.add(And(BoolVal(True), BoolVal(False))); assert s.check() == unsat

    def test_or_one_true(self):
        s = Solver(); s.add(Or(BoolVal(False), BoolVal(True))); assert s.check() == sat

    def test_or_both_false(self):
        s = Solver(); s.add(Or(BoolVal(False), BoolVal(False))); assert s.check() == unsat

    def test_not(self):
        s = Solver(); s.add(Not(BoolVal(False))); assert s.check() == sat

    def test_implies_true_true(self):
        s = Solver(); s.add(Implies(BoolVal(True), BoolVal(True))); assert s.check() == sat

    def test_implies_true_false(self):
        s = Solver(); s.add(Implies(BoolVal(True), BoolVal(False))); assert s.check() == unsat

    def test_implies_false_anything(self):
        # False => X is vacuously true
        s = Solver(); s.add(Implies(BoolVal(False), BoolVal(False))); assert s.check() == sat

    def test_real_comparison(self):
        val = RealVal(0.8)
        # val >= 0.5 should be True
        expr = val >= RealVal(0.5)
        s = Solver(); s.add(expr); assert s.check() == sat

    def test_multiple_constraints(self):
        s = Solver()
        s.add(BoolVal(True))
        s.add(BoolVal(True))
        assert s.check() == sat


# ── FactNamespace ─────────────────────────────────────────────────────────────

class TestFactNamespace:
    def test_attribute_access(self):
        ns = FactNamespace({"foo": BoolVal(True)})
        assert ns.foo is not None

    def test_missing_fact_raises(self):
        ns = FactNamespace({"foo": BoolVal(True)})
        with pytest.raises(AttributeError, match="bar"):
            _ = ns.bar

    def test_repr(self):
        ns = FactNamespace({"a": BoolVal(True), "b": BoolVal(False)})
        assert "a" in repr(ns) and "b" in repr(ns)


# ── _make_fact_vars ────────────────────────────────────────────────────────────

class TestMakeFactVars:
    def test_bool_facts(self):
        facts = {"is_fast": True, "has_errors": False}
        vars_ = _make_fact_vars(facts)
        assert "is_fast" in vars_ and "has_errors" in vars_

    def test_float_facts(self):
        facts = {"score": 0.85}
        vars_ = _make_fact_vars(facts)
        assert "score" in vars_

    def test_string_true(self):
        vars_ = _make_fact_vars({"up": "true"})
        assert "up" in vars_
        s = Solver(); s.add(vars_["up"]); assert s.check() == sat

    def test_string_false(self):
        vars_ = _make_fact_vars({"up": "false"})
        s = Solver(); s.add(vars_["up"]); assert s.check() == unsat

    def test_dash_in_name(self):
        vars_ = _make_fact_vars({"my-fact": True})
        assert "my_fact" in vars_


# ── evaluate_person ────────────────────────────────────────────────────────────

class TestEvaluatePerson:
    def _person(self, constraints_fn):
        class P(Person):
            name = "test"
            def constraints(self, P):
                return constraints_fn(P)
        return P()

    def test_satisfied(self):
        p = self._person(lambda P: [P.is_fast])
        r = evaluate_person(p, {"is_fast": True})
        assert r["satisfied"] is True
        assert r["score"] == 1.0
        assert r["violations"] == []

    def test_not_satisfied(self):
        p = self._person(lambda P: [P.is_fast])
        r = evaluate_person(p, {"is_fast": False})
        assert r["satisfied"] is False
        assert r["score"] == 0.0
        assert len(r["violations"]) == 1

    def test_partial_score(self):
        p = self._person(lambda P: [P.a, P.b])
        r = evaluate_person(p, {"a": True, "b": False})
        assert r["score"] == 0.5
        assert r["satisfied"] is False

    def test_empty_constraints(self):
        p = self._person(lambda P: [])
        r = evaluate_person(p, {})
        assert r["satisfied"] is True
        assert r["score"] == 1.0

    def test_implies_vacuous(self):
        # Implies(False, anything) is True
        p = self._person(lambda P: [Implies(P.is_large, P.has_clusters)])
        r = evaluate_person(p, {"is_large": False, "has_clusters": False})
        assert r["satisfied"] is True

    def test_missing_fact_returns_error(self):
        p = self._person(lambda P: [P.nonexistent_fact])
        r = evaluate_person(p, {})
        assert r["satisfied"] is False
        assert "error" in r or len(r["violations"]) > 0


# ── Perception library ─────────────────────────────────────────────────────────

class TestPerceptionLibrary:
    def test_threshold_max(self):
        assert threshold({"ms": 200}, "ms", max=300) is True
        assert threshold({"ms": 400}, "ms", max=300) is False

    def test_threshold_min(self):
        assert threshold({"score": 0.9}, "score", min=0.7) is True
        assert threshold({"score": 0.5}, "score", min=0.7) is False

    def test_threshold_missing_key(self):
        assert threshold({}, "missing", max=100, default=True) is True
        assert threshold({}, "missing", max=100, default=False) is False

    def test_in_range(self):
        assert in_range({"x": 5}, "x", 1, 10) is True
        assert in_range({"x": 15}, "x", 1, 10) is False

    def test_ratio(self):
        assert abs(ratio({"a": 3, "b": 4}, "a", "b") - 0.75) < 1e-9

    def test_ratio_zero_denominator(self):
        assert ratio({"a": 1, "b": 0}, "a", "b", default=-1) == -1

    def test_flag_bool(self):
        assert flag({"up": True}, "up") is True
        assert flag({"up": False}, "up") is False

    def test_flag_string(self):
        assert flag({"up": "yes"}, "up") is True
        assert flag({"up": "no"},  "up") is False


# ── Schema validation ──────────────────────────────────────────────────────────

class TestSchema:
    def test_valid_metrics(self):
        doc = {"schema": "usersim.metrics.v1", "metrics": {"x": 1}}
        validate_metrics(doc)  # should not raise

    def test_invalid_metrics_schema(self):
        doc = {"schema": "wrong", "metrics": {}}
        with pytest.raises(ValueError, match="usersim.metrics.v1"):
            validate_metrics(doc)

    def test_missing_metrics_key(self):
        doc = {"schema": "usersim.metrics.v1"}
        with pytest.raises(ValueError):
            validate_metrics(doc)

    def test_valid_perceptions(self):
        doc = {"schema": "usersim.perceptions.v1", "facts": {}, "person": "x"}
        validate_perceptions(doc)

    def test_invalid_perceptions_schema(self):
        doc = {"schema": "nope", "facts": {}, "person": "x"}
        with pytest.raises(ValueError):
            validate_perceptions(doc)


# ── End-to-end: evaluate against a perceptions.json ───────────────────────────

class TestEndToEnd:
    def test_full_judgement(self, tmp_path):
        from usersim.judgement.engine import run_judgement

        # Write a user file
        user_file = tmp_path / "alice.py"
        user_file.write_text("""
from usersim import Person
from usersim.judgement.z3_compat import Implies

class Alice(Person):
    name = "alice"
    def constraints(self, P):
        return [P.loads_fast, Implies(P.is_large, P.has_clusters)]
""")

        # Write perceptions.json
        perc_file = tmp_path / "perceptions.json"
        perc_file.write_text(json.dumps({
            "schema":   "usersim.perceptions.v1",
            "path": "homepage",
            "person":   "alice",
            "facts":    {"loads_fast": True, "is_large": False, "has_clusters": False},
        }))

        result = run_judgement(perc_file, [user_file])
        assert result["summary"]["satisfied"] == 1
        assert result["summary"]["score"] == 1.0
