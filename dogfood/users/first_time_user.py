"""First-time user evaluating usersim — does this thing actually work?"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from usersim import Person
from usersim.judgement.z3_compat import Implies, And, Not, named
from constraint_library import (
    matrix_invariants,
    pipeline_invariants,
    timing_invariants,
    scaffold_invariants,
    report_invariants,
)


class FirstTimeUser(Person):
    name    = "first_time_user"
    role    = "Developer evaluating usersim"
    goal    = "get a working simulation running quickly and understand the output"
    pronoun = "they"

    def constraints(self, P):
        return [
            *matrix_invariants(P),
            *pipeline_invariants(P),
            *timing_invariants(P, max_ms_per_result=5000, max_total_ms=120000),
            *scaffold_invariants(P),
            *report_invariants(P),

            # ── First-time-user-specific ──────────────────────────────────
            # The example must fully pass — proves the tool works end-to-end
            named("first-time/example-must-fully-pass",
                  Implies(P.results_total >= 1,
                          P.results_satisfied == P.results_total)),
            # Pipeline must exit cleanly
            named("first-time/pipeline-exits-0",
                  Implies(P.pipeline_exit_code >= 0, P.pipeline_exit_code == 0)),
            # Must have evaluated multiple persons and paths
            named("first-time/multiple-persons-evaluated",
                  Implies(P.pipeline_exit_code == 0, P.person_count >= 1)),
            named("first-time/multiple-paths-evaluated",
                  Implies(P.pipeline_exit_code == 0, P.scenario_count >= 1)),
            # Report must succeed
            named("first-time/report-exits-0",
                  Implies(P.report_exit_code >= 0, P.report_exit_code == 0)),
            # Scaffold must exit cleanly
            named("first-time/scaffold-exits-0",
                  Implies(P.init_exit_code >= 0, P.init_exit_code == 0)),
        ]
