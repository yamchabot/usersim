"""DevOps engineer running usersim in a pipeline — cares about exit codes and artifacts."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from usersim import Person
from usersim.judgement.z3_compat import Implies, And, Not, named
from constraint_library import (
    matrix_invariants,
    pipeline_invariants,
    timing_invariants,
    error_handling_invariants,
    report_invariants,
    judge_invariants,
)


class DevOpsEngineer(Person):
    name    = "devops_engineer"
    role    = "DevOps Engineer"
    goal    = "run usersim in CI/CD — exit codes gate deploys, artifacts are uploaded"
    pronoun = "he"

    def constraints(self, P):
        return [
            *matrix_invariants(P),
            *pipeline_invariants(P),
            *timing_invariants(P, max_ms_per_result=4000, max_total_ms=90000),
            *error_handling_invariants(P),
            *report_invariants(P),
            *judge_invariants(P),

            # ── DevOps-specific: artifact and exit-code contracts ─────────
            # Pipeline must exit 0 to gate a deploy
            named("devops/pipeline-exits-0",
                  Implies(P.pipeline_exit_code >= 0, P.pipeline_exit_code == 0)),
            # Report artifact must exist after successful run
            named("devops/report-artifact-produced",
                  Implies(P.report_exit_code == 0, P.report_file_created)),
            # Results JSON artifact must be valid
            named("devops/results-json-valid",
                  Implies(P.pipeline_exit_code == 0, P.output_is_valid_json)),
            # Non-zero exit on bad config — pipeline must fail loudly
            named("devops/bad-config-fails-loudly",
                  Implies(P.bad_yaml_exit_code >= 0, P.bad_yaml_exit_code > 0)),
            # Errors must go to stderr so CI log parsers can distinguish them
            named("devops/errors-to-stderr-for-ci-parsing",
                  Implies(P.missing_config_exit_code == 1, P.errors_use_stderr)),
            # Timing must fit within typical CI job budget
            named("devops/fits-ci-job-budget",
                  Implies(P.pipeline_wall_clock_ms > 0,
                          P.pipeline_wall_clock_ms <= 90000)),
            # All three error paths must be exercised — CI must test failure modes
            named("devops/all-failure-modes-exit-non-zero",
                  Implies(And(P.missing_config_exit_code >= 0,
                              P.bad_yaml_exit_code >= 0,
                              P.missing_users_exit_code >= 0),
                          And(P.missing_config_exit_code > 0,
                              P.bad_yaml_exit_code > 0,
                              P.missing_users_exit_code > 0))),
            # Full pass required to gate deploy
            named("devops/all-checks-pass-before-deploy",
                  Implies(P.results_total >= 1,
                          P.results_satisfied == P.results_total)),
        ]
