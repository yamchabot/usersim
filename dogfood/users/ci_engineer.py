"""CI engineer integrating usersim into a build pipeline."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from usersim import Person
from usersim.judgement.z3_compat import Implies, And, Not, named
from constraint_library import (
    matrix_invariants,
    pipeline_invariants,
    timing_invariants,
    error_handling_invariants,
    judge_invariants,
)


class CIEngineer(Person):
    name    = "ci_engineer"
    role    = "Build/CI engineer"
    goal    = "integrate usersim into CI with confidence in exit codes and performance"
    pronoun = "they"

    def constraints(self, P):
        return [
            *matrix_invariants(P),
            *pipeline_invariants(P),
            *timing_invariants(P, max_ms_per_result=3000, max_total_ms=60000),
            *error_handling_invariants(P),
            *judge_invariants(P),

            # ── CI-specific: full pass required on the example ────────────
            named("ci/example-must-fully-pass",
                  Implies(P.results_total >= 1,
                          P.results_satisfied == P.results_total)),
        ]
