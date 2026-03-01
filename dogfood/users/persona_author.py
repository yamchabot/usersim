"""UX researcher writing persona constraint files — needs clear, detailed results."""
from usersim import Person
from usersim.judgement.z3_compat import Implies


class PersonaAuthor(Person):
    name    = "persona_author"
    role    = "UX researcher writing persona constraints"
    goal    = "see clear, detailed results that explain what failed and why"
    pronoun = "she"

    def constraints(self, P):
        return [
            # ── Results must be complete and meaningful ───────────────────
            Implies(P.pipeline_exit_code == 0, P.all_constraints_present),
            Implies(P.pipeline_exit_code == 0, P.person_count >= 3),
            Implies(P.pipeline_exit_code == 0, P.scenario_count >= 3),
            # Total = persons × scenarios (3×3 = 9 for data-processor)
            Implies(P.results_total >= 1, P.results_total >= 9),
            # A useful result set has at least something passing
            Implies(P.results_total >= 1, P.results_satisfied >= 1),
            Implies(P.results_total >= 1, P.results_score > 0),
            # If we have 9+ results, person and scenario counts must be consistent
            Implies(P.results_total >= 9, P.person_count >= 3),
            Implies(P.results_total >= 9, P.scenario_count >= 3),

            # ── Report must support her review workflow ───────────────────
            Implies(P.report_file_created, P.report_has_cards),
            Implies(P.report_file_created, P.report_is_self_contained),
            Implies(P.report_file_created, P.report_file_size_bytes >= 5000),
            # Report must have doctype (otherwise browser quirks mode breaks layout)
            Implies(P.report_file_created, P.report_has_doctype),
        ]
