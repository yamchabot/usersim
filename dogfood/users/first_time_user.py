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
            # ── Pipeline: the example must fully pass ─────────────────────
            Implies(P.pipeline_exit_code >= 0, P.pipeline_exit_code == 0),
            Not(And(P.pipeline_exit_code == 0, P.results_total == 0)),
            # Full pass: satisfied == total (100% pass rate, no cross-multiply needed)
            Implies(P.results_total >= 1, P.results_satisfied == P.results_total),
            Implies(P.pipeline_exit_code == 0, P.output_is_valid_json),
            Implies(P.pipeline_exit_code == 0, P.schema_is_correct),

            # ── Pipeline: matrix must have multiple dimensions ─────────────
            Implies(P.pipeline_exit_code == 0, P.person_count >= 1),
            Implies(P.pipeline_exit_code == 0, P.scenario_count >= 1),
            # Total must reflect the matrix
            Implies(
                And(P.pipeline_exit_code == 0, P.person_count >= 1),
                P.results_total == P.person_count * P.scenario_count,
            ),

            # ── Timing: must feel snappy; scales with how much was evaluated ─
            Implies(
                P.pipeline_wall_clock_ms > 0,
                P.pipeline_wall_clock_ms <= P.results_total * 5000,
            ),
            # Also: time should scale with persons AND scenarios independently
            Implies(
                P.pipeline_wall_clock_ms > 0,
                P.pipeline_wall_clock_ms <= P.person_count * P.scenario_count * 5000,
            ),

            # ── Init: scaffold must be complete ───────────────────────────
            Implies(P.init_exit_code >= 0, P.init_exit_code == 0),
            Implies(P.init_exit_code == 0, P.config_created),
            Implies(P.init_exit_code == 0, P.yaml_parseable),
            Implies(P.init_exit_code == 0, P.scaffold_file_count >= 3),
            # yaml_parseable implies config exists — can't parse what isn't there
            Implies(P.yaml_parseable, P.config_created),

            # ── Report: must be viewable and proportional to results ───────
            Implies(P.report_exit_code >= 0, P.report_exit_code == 0),
            Implies(P.report_exit_code == 0, P.report_file_created),
            Implies(P.report_file_created, P.report_has_doctype),
            Implies(P.report_file_created, P.report_is_self_contained),
            # Report size must grow with matrix: bytes >= total * person_count * 50
            Implies(
                And(P.report_file_created, P.results_total >= 1, P.person_count >= 1),
                P.report_file_size_bytes >= P.results_total * P.person_count * 50,
            ),
        ]
