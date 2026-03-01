"""First-time user evaluating usersim — does this thing actually work?"""
from usersim import Person
from usersim.judgement.z3_compat import Implies, And, Not


class FirstTimeUser(Person):
    name    = "first_time_user"
    role    = "Developer evaluating usersim"
    goal    = "get a working simulation running quickly and understand the output"
    pronoun = "they"

    def constraints(self, P):
        return [
            # ── The example must fully pass ───────────────────────────────
            Implies(P.pipeline_exit_code >= 0, P.pipeline_exit_code == 0),
            # Can't succeed with zero results — would look like success but prove nothing
            Not(And(P.pipeline_exit_code == 0, P.results_total == 0)),
            # The example must fully pass: satisfied == total (proves the tool works)
            Implies(P.results_total >= 1, P.results_satisfied == P.results_total),
            # Output must be readable JSON
            Implies(P.pipeline_exit_code == 0, P.output_is_valid_json),
            Implies(P.pipeline_exit_code == 0, P.schema_is_correct),
            # Must have evaluated at least one person in at least one scenario
            Implies(P.pipeline_exit_code == 0, P.person_count >= 1),
            Implies(P.pipeline_exit_code == 0, P.scenario_count >= 1),

            # ── Timing must feel reasonable ───────────────────────────────
            # A first-time user gives up if it hangs — budget: 5s per result
            Implies(
                P.pipeline_wall_clock_ms > 0,
                P.pipeline_wall_clock_ms <= P.results_total * 5000,
            ),

            # ── Init scaffold must produce something runnable ─────────────
            Implies(P.init_exit_code >= 0, P.init_exit_code == 0),
            Implies(P.init_exit_code == 0, P.config_created),
            Implies(P.init_exit_code == 0, P.yaml_parseable),
            Implies(P.init_exit_code == 0, P.scaffold_file_count >= 3),

            # ── Report must open in a browser and have real content ────────
            Implies(P.report_exit_code >= 0, P.report_exit_code == 0),
            Implies(P.report_exit_code == 0, P.report_file_created),
            Implies(P.report_file_created, P.report_has_doctype),
            Implies(P.report_file_created, P.report_is_self_contained),
            # Report size must scale with results — a 9-result report can't be 1KB
            Implies(
                And(P.report_file_created, P.results_total >= 1),
                P.report_file_size_bytes >= P.results_total * 200,
            ),
        ]
