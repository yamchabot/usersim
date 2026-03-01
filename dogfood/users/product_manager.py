"""Product manager who wants provable user story satisfaction, not terminal output."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from usersim import Person
from usersim.judgement.z3_compat import Implies, And, Not, named
from constraint_library import (
    matrix_invariants,
    pipeline_invariants,
    report_invariants,
)


class ProductManager(Person):
    name    = "product_manager"
    role    = "Product Manager"
    goal    = "see provable user story satisfaction across all personas and paths"
    pronoun = "she"

    def constraints(self, P):
        return [
            *matrix_invariants(P),
            *pipeline_invariants(P),
            *report_invariants(P),

            # ── PM-specific: story-level outcomes ────────────────────────
            # All user stories must pass — 100% satisfaction required
            named("pm/all-stories-pass",
                  Implies(P.results_total >= 1,
                          P.results_satisfied == P.results_total)),
            # Must evaluate multiple personas — one user type isn't a product
            named("pm/multiple-personas-required",
                  Implies(P.pipeline_exit_code == 0, P.person_count >= 3)),
            # Must cover multiple paths — one path isn't a product
            named("pm/multiple-paths-required",
                  Implies(P.pipeline_exit_code == 0, P.scenario_count >= 3)),
            # Total results must represent full cross-product
            named("pm/full-cross-product-evaluated",
                  Implies(P.results_total >= 1,
                          P.results_total == P.person_count * P.scenario_count)),
            # Report must exist and be non-trivially sized
            named("pm/report-exists-and-is-substantial",
                  Implies(And(P.report_file_created, P.results_total >= 1),
                          P.report_file_size_bytes >= P.person_count * P.scenario_count * 200)),
            # Report must have DOCTYPE — basic quality signal for stakeholders
            named("pm/report-is-valid-html",
                  Implies(P.report_file_created, P.report_has_doctype)),
            # Satisfied count must grow with matrix size (proportionality)
            named("pm/satisfied-proportional-to-matrix",
                  Implies(And(P.results_total >= 1, P.results_satisfied >= 1),
                          P.results_satisfied * 10 >= P.person_count * P.scenario_count * 8)),
        ]
