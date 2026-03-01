"""UX researcher writing persona constraint files — needs clear, detailed results."""
from usersim import Person
from usersim.judgement.z3_compat import Implies, And, Not


class PersonaAuthor(Person):
    name    = "persona_author"
    role    = "UX researcher writing persona constraints"
    goal    = "see clear, detailed results that explain what failed and why"
    pronoun = "she"

    def constraints(self, P):
        return [
            # ── Result completeness: matrix must be structurally sound ─────
            # Total must equal persons × scenarios — an incomplete matrix is useless
            Implies(
                P.results_total >= 1,
                P.results_total == P.person_count * P.scenario_count,
            ),
            # Can't have results with no persons or no scenarios
            Not(And(P.results_total >= 1, P.person_count == 0)),
            Not(And(P.results_total >= 1, P.scenario_count == 0)),
            # The data-processor example must produce a full 3×3 matrix
            Implies(P.pipeline_exit_code == 0, P.results_total >= 9),
            Implies(P.pipeline_exit_code == 0, P.person_count >= 3),
            Implies(P.pipeline_exit_code == 0, P.scenario_count >= 3),
            # Constraints must be present for the results to be useful
            Implies(P.pipeline_exit_code == 0, P.all_constraints_present),

            # ── Result quality: at least something must be passing ─────────
            # A matrix of all failures is unreadable — needs contrast to be useful
            Implies(P.results_total >= 1, P.results_satisfied >= 1),
            # satisfied can never exceed total
            Implies(P.results_total >= 1, P.results_satisfied <= P.results_total),

            # ── Report: majority of quality signals must hold ─────────────
            # At least 3 of 4 structural quality checks must pass
            # (Z3 boolean arithmetic — each flag contributes 1 when True)
            Implies(
                P.report_file_created,
                P.report_has_cards + P.report_is_self_contained
                + P.report_has_doctype >= 3,
            ),
            # Report size must scale with the result matrix
            # A 9-result report under 1800 bytes (9×200) is suspiciously small
            Implies(
                And(P.report_file_created, P.results_total >= 1),
                P.report_file_size_bytes >= P.results_total * 200,
            ),
        ]
