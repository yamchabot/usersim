"""QA engineer verifying coverage gaps, flakiness, and regression signals."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from usersim import Person
from usersim.judgement.z3_compat import Implies, And, Not, named
from constraint_library import (
    matrix_invariants,
    pipeline_invariants,
    error_handling_invariants,
    judge_invariants,
    report_invariants,
)


class QAEngineer(Person):
    name    = "qa_engineer"
    role    = "QA / Test Engineer"
    goal    = "verify every scenario exercises real constraints and no coverage gaps exist"
    pronoun = "she"

    def constraints(self, P):
        return [
            *matrix_invariants(P),
            *pipeline_invariants(P),
            *error_handling_invariants(P),
            *judge_invariants(P),
            *report_invariants(P),

            # ── QA-specific: coverage completeness ───────────────────────
            named("qa/full-matrix-coverage",
                  Implies(P.results_total >= 1,
                          P.results_total == P.person_count * P.scenario_count)),
            named("qa/minimum-scenario-count",
                  Implies(P.pipeline_exit_code == 0, P.scenario_count >= 2)),
            named("qa/minimum-person-count",
                  Implies(P.pipeline_exit_code == 0, P.person_count >= 2)),
            # 80% pass rate minimum: 5*sat >= 4*total
            named("qa/80pct-pass-rate-minimum",
                  Implies(And(P.pipeline_exit_code == 0, P.results_total >= 1),
                          P.results_satisfied * 5 >= P.results_total * 4)),
            named("qa/error-scenarios-covered",
                  Implies(P.missing_config_exit_code >= 0,
                          P.missing_config_exit_code == 1)),
            named("qa/judge-result-count-consistent",
                  Implies(And(P.judge_exit_code == 0, P.judge_total_count >= 1),
                          P.judge_satisfied_count <= P.judge_total_count)),
            named("qa/report-covers-all-persons",
                  Implies(And(P.report_file_created, P.person_count >= 1),
                          P.report_file_size_bytes >= P.person_count * 500)),
            named("qa/no-missing-results",
                  Implies(P.results_total >= 1,
                          P.results_satisfied <= P.results_total)),
        ]
