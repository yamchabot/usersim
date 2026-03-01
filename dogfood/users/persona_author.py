"""UX researcher writing persona constraint files — needs clear, detailed results."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from usersim import Person
from usersim.judgement.z3_compat import Implies, And, Not, named
from constraint_library import (
    matrix_invariants,
    pipeline_invariants,
    report_invariants,
)


class PersonaAuthor(Person):
    name    = "persona_author"
    role    = "UX researcher writing persona constraints"
    goal    = "see clear, detailed results that explain what failed and why"
    pronoun = "she"

    def constraints(self, P):
        return [
            *matrix_invariants(P),
            *pipeline_invariants(P),
            *report_invariants(P),

            # ── Persona-author-specific ───────────────────────────────────
            # data-processor example must produce a full 3×3 matrix
            named("persona-author/example-produces-3x3-matrix",
                  Implies(P.pipeline_exit_code == 0, P.results_total >= 9)),
            named("persona-author/example-has-3-persons",
                  Implies(P.pipeline_exit_code == 0, P.person_count >= 3)),
            named("persona-author/example-has-3-scenarios",
                  Implies(P.pipeline_exit_code == 0, P.scenario_count >= 3)),
            # All constraints must be present to write new personas against
            named("persona-author/all-constraints-present",
                  Implies(P.pipeline_exit_code == 0, P.all_constraints_present)),
            # Results must have contrast — at least one pass, at least one that
            # could fail in a degraded run (satisfied < total is acceptable here)
            named("persona-author/at-least-one-passing-result",
                  Implies(P.results_total >= 1, P.results_satisfied >= 1)),
            # Satisfied count is consistent with matrix dimensions
            named("persona-author/satisfied-consistent-with-matrix",
                  Implies(And(P.results_total >= 1, P.results_satisfied >= 1),
                          P.results_satisfied <= P.person_count * P.scenario_count)),
            # Report size must reflect the full matrix content
            named("persona-author/report-size-reflects-matrix",
                  Implies(And(P.report_file_created, P.results_total >= 1,
                              P.person_count >= 1),
                          P.report_file_size_bytes
                          >= P.results_total * P.person_count * 100)),
        ]
