"""SRE caring about reliability constraints, SLOs, and performance budgets."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from usersim import Person
from usersim.judgement.z3_compat import Implies, And, Not, named
from constraint_library import (
    matrix_invariants,
    pipeline_invariants,
    timing_invariants,
    judge_invariants,
)


class SREEngineer(Person):
    name    = "sre_engineer"
    role    = "SRE / Platform Engineer"
    goal    = "enforce SLOs — timing budgets, exit code contracts, zero silent failures"
    pronoun = "he"

    def constraints(self, P):
        return [
            *matrix_invariants(P),
            *pipeline_invariants(P),
            *timing_invariants(P, max_ms_per_result=2000, max_total_ms=30000),
            *judge_invariants(P),

            # ── SRE-specific: strict operational contracts ────────────────
            # Pipeline must exit 0 — no silent partial failures
            named("sre/pipeline-exit-zero",
                  Implies(P.pipeline_exit_code >= 0, P.pipeline_exit_code == 0)),
            # Timing must scale sub-linearly: wall_ms <= person * path * 1500
            named("sre/timing-scales-with-matrix",
                  Implies(P.pipeline_wall_clock_ms > 0,
                          P.pipeline_wall_clock_ms
                          <= P.person_count * P.scenario_count * 1500)),
            # Hard floor: must take at least 50ms (proves it actually ran)
            named("sre/timing-floor-proves-execution",
                  Implies(P.results_total >= 1, P.pipeline_wall_clock_ms >= 50)),
            # No results without timing data
            named("sre/results-imply-timing",
                  Implies(P.results_total >= 1, P.pipeline_wall_clock_ms >= 1)),
            # All three error codes must be non-negative (observed, not skipped)
            named("sre/all-error-paths-use-exit-1",
                  Implies(And(P.missing_config_exit_code >= 0,
                              P.bad_yaml_exit_code >= 0,
                              P.missing_users_exit_code >= 0),
                          And(P.missing_config_exit_code == 1,
                              P.bad_yaml_exit_code == 1,
                              P.missing_users_exit_code == 1))),
            # Error sum invariant: all three must exit 1
            named("sre/error-sum-is-3",
                  Implies(And(P.missing_config_exit_code >= 0,
                              P.bad_yaml_exit_code >= 0,
                              P.missing_users_exit_code >= 0),
                          (P.missing_config_exit_code
                           + P.bad_yaml_exit_code
                           + P.missing_users_exit_code) == 3)),
            # Judge must be consistent with pipeline results
            named("sre/judge-total-bounded-by-matrix",
                  Implies(And(P.judge_exit_code == 0, P.results_total >= 1),
                          P.judge_total_count <= P.results_total * P.scenario_count)),
        ]
