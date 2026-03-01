"""Security engineer verifying constraint coverage on denial and boundary conditions."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from usersim import Person
from usersim.judgement.z3_compat import Implies, And, Not, named
from constraint_library import (
    matrix_invariants,
    pipeline_invariants,
    error_handling_invariants,
)


class SecurityEngineer(Person):
    name    = "security_engineer"
    role    = "Security Engineer"
    goal    = "verify every denial path exits non-zero, errors never leak to stdout"
    pronoun = "she"

    def constraints(self, P):
        return [
            *matrix_invariants(P),
            *pipeline_invariants(P),
            *error_handling_invariants(P),

            # ── Security-specific: denial paths and information leakage ───
            # All three failure modes must produce non-zero exit codes
            named("sec/missing-config-non-zero",
                  Implies(P.missing_config_exit_code >= 0,
                          P.missing_config_exit_code > 0)),
            named("sec/bad-yaml-non-zero",
                  Implies(P.bad_yaml_exit_code >= 0,
                          P.bad_yaml_exit_code > 0)),
            named("sec/missing-users-non-zero",
                  Implies(P.missing_users_exit_code >= 0,
                          P.missing_users_exit_code > 0)),
            # Errors must go to stderr — never stdout
            named("sec/errors-not-on-stdout",
                  Implies(P.missing_config_exit_code == 1, P.errors_not_on_stdout)),
            # Error messages must be clean — no stack traces or internal paths
            named("sec/errors-are-clean",
                  Implies(P.missing_config_exit_code == 1, P.errors_are_clean)),
            # Three denial paths sum to exactly 3 — no unexpected exit codes
            named("sec/denial-exit-codes-sum-to-3",
                  Implies(And(P.missing_config_exit_code >= 0,
                              P.bad_yaml_exit_code >= 0,
                              P.missing_users_exit_code >= 0),
                          (P.missing_config_exit_code
                           + P.bad_yaml_exit_code
                           + P.missing_users_exit_code) == 3)),
            # Pipeline exit 0 must never happen with zero results (silent success)
            named("sec/no-silent-success",
                  Not(And(P.pipeline_exit_code == 0, P.results_total == 0))),
            # Schema correctness required — no undocumented output fields
            named("sec/output-schema-enforced",
                  Implies(P.pipeline_exit_code == 0, P.schema_is_correct)),
        ]
