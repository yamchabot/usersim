"""
Audits whether usersim's own constraints are doing useful work.

A constraint system that never produces violations is either testing the wrong
things or using thresholds so loose that nothing could trip them. This persona
checks that the constraint suite has healthy churn — some violations, not all,
not none — and that usersim correctly surfaces instrumentation failures rather
than swallowing them silently.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from usersim import Person
from usersim.judgement.z3_compat import Implies, And, Not, named


class ConstraintHealthAuditor(Person):
    name    = "constraint_health_auditor"
    role    = "Constraint Health Auditor"
    goal    = "verify usersim's constraints are doing real work — not vacuous, not always-failing"
    pronoun = "they"

    def constraints(self, P):
        return [
            # ── Violation health scenario ─────────────────────────────────────

            # The suite must have actually evaluated some constraints
            named("health/evals-happened",
                  Implies(P.vh_total_evals >= 0, P.vh_total_evals >= 10)),

            # There must be some unique constraints (not all duplicates)
            named("health/unique-constraints-exist",
                  Implies(P.vh_unique_constraints >= 0, P.vh_unique_constraints >= 5)),

            # Antecedents should fire for most evals (not all Implies vacuously true)
            # At least 50% of evals should have the antecedent fire
            named("health/antecedents-fire-meaningfully",
                  Implies(P.vh_total_evals >= 10,
                          P.vh_antecedent_fired * 2 >= P.vh_total_evals)),

            # Some constraints must fire — at least 1 violation per 50 evals
            named("health/some-violations-occur",
                  Implies(P.vh_total_evals >= 50,
                          P.vh_total_violations >= 1)),

            # But not everything should fail — if >50% fail the model is broken
            named("health/not-all-failing",
                  Implies(P.vh_total_evals >= 10,
                          P.vh_total_violations * 2 <= P.vh_total_evals)),

            # Most unique constraints should be passing
            named("health/most-constraints-satisfied",
                  Implies(P.vh_unique_constraints >= 5,
                          P.vh_violated_constraints * 4 <= P.vh_unique_constraints * 3)),

            # ── Broken example scenario ───────────────────────────────────────

            # When instrumentation exits non-zero, usersim must detect it
            named("health/broken-instrumentation-detected",
                  Implies(P.broken_exit_code >= 0,
                          P.broken_failure_detected == True)),

            # usersim should still run to completion even with broken instrumentation
            named("health/broken-does-not-crash-usersim",
                  Implies(P.broken_exit_code >= 0,
                          P.broken_ran_to_completion == True)),
        ]
