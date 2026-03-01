"""First-time user evaluating usersim — does this thing actually work?"""
from usersim import Person
from usersim.judgement.z3_compat import Implies


class FirstTimeUser(Person):
    name    = "first_time_user"
    role    = "Developer evaluating usersim"
    goal    = "get a working simulation running quickly and understand the output"
    pronoun = "they"

    def constraints(self, P):
        return [
            # ── The example must just work ────────────────────────────────
            Implies(P.pipeline_exit_code >= 0, P.pipeline_exit_code == 0),
            Implies(P.pipeline_exit_code == 0, P.output_is_valid_json),
            Implies(P.pipeline_exit_code == 0, P.schema_is_correct),
            # Results exist and everything passes (proves the tool works end-to-end)
            Implies(P.pipeline_exit_code == 0, P.results_total >= 1),
            Implies(P.results_total >= 1, P.results_score >= 1.0),
            # Must have evaluated at least one person across at least one scenario
            Implies(P.pipeline_exit_code == 0, P.person_count >= 1),
            Implies(P.pipeline_exit_code == 0, P.scenario_count >= 1),

            # ── Init scaffold must produce something runnable ─────────────
            Implies(P.init_exit_code >= 0, P.init_exit_code == 0),
            Implies(P.init_exit_code == 0, P.config_created),
            Implies(P.init_exit_code == 0, P.yaml_parseable),
            # Scaffold should have enough files to not feel empty
            Implies(P.init_exit_code == 0, P.scaffold_file_count >= 3),

            # ── Report must be openable in a browser ──────────────────────
            Implies(P.report_exit_code >= 0, P.report_exit_code == 0),
            Implies(P.report_exit_code == 0, P.report_file_created),
            Implies(P.report_file_created, P.report_has_doctype),
            # Report must have real content, not a stub
            Implies(P.report_file_created, P.report_file_size_bytes >= 5000),
            # Must work offline — no external stylesheet or script deps
            Implies(P.report_file_created, P.report_is_self_contained),
        ]
