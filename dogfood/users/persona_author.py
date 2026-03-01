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
            # ── Matrix: must be structurally complete ─────────────────────
            Implies(
                P.results_total >= 1,
                P.results_total == P.person_count * P.scenario_count,
            ),
            Not(And(P.results_total >= 1, P.person_count == 0)),
            Not(And(P.results_total >= 1, P.scenario_count == 0)),
            # data-processor example must produce a full 3×3 matrix
            Implies(P.pipeline_exit_code == 0, P.results_total >= 9),
            Implies(P.pipeline_exit_code == 0, P.person_count >= 3),
            Implies(P.pipeline_exit_code == 0, P.scenario_count >= 3),
            Implies(P.pipeline_exit_code == 0, P.all_constraints_present),

            # ── Results: must be useful (some contrast between pass/fail) ──
            Implies(P.results_total >= 1, P.results_satisfied >= 1),
            # arithmetic consistency
            Implies(P.results_total >= 1, P.results_satisfied <= P.results_total),
            # satisfied count is consistent with matrix dimensions
            Implies(
                And(P.results_total >= 1, P.results_satisfied >= 1),
                P.results_satisfied <= P.person_count * P.scenario_count,
            ),

            # ── Report: all quality signals must hold simultaneously ───────
            # Majority vote: 3 of 3 structural quality flags required
            Implies(
                P.report_file_created,
                P.report_has_cards + P.report_is_self_contained
                + P.report_has_doctype >= 3,
            ),
            # Report size must scale with both result count and persona count
            # A 3-persona × 3-scenario report must have more bytes than a 1×1
            Implies(
                And(P.report_file_created, P.results_total >= 1, P.person_count >= 1),
                P.report_file_size_bytes >= P.results_total * P.person_count * 50,
            ),
            # Full-quality report (all 3 flags) should be larger still
            Implies(
                And(P.report_file_created, P.report_has_cards,
                    P.report_is_self_contained, P.report_has_doctype),
                P.report_file_size_bytes >= P.results_total * P.person_count * 100,
            ),

            # ── Cross-system coherence ────────────────────────────────────
            # If pipeline produced results AND report was created, report must
            # be proportional to what the pipeline generated
            Implies(
                And(P.pipeline_exit_code == 0, P.report_file_created,
                    P.results_total >= 1),
                P.report_file_size_bytes >= P.results_total * 200,
            ),
        ]
