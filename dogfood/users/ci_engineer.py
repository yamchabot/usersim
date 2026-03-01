"""CI engineer integrating usersim into a build pipeline."""
from usersim import Person
from usersim.judgement.z3_compat import Implies, And, Not


class CIEngineer(Person):
    name    = "ci_engineer"
    role    = "Build/CI engineer"
    goal    = "integrate usersim into CI with confidence in exit codes and performance"
    pronoun = "they"

    def constraints(self, P):
        return [
            # ── Pipeline: structural invariants ───────────────────────────
            # Exit 0 with zero results is a silent corruption — impossible
            Not(And(P.pipeline_exit_code == 0, P.results_total == 0)),
            # Exit 0 means the full example passed — satisfied must equal total
            Implies(P.pipeline_exit_code == 0, P.results_satisfied == P.results_total),
            # Output must be machine-parseable JSON for CI consumers
            Implies(P.pipeline_exit_code == 0, P.output_is_valid_json),

            # ── Pipeline: matrix completeness ─────────────────────────────
            # Total results must equal persons × scenarios — the matrix must be full
            Implies(
                P.results_total >= 1,
                P.results_total == P.person_count * P.scenario_count,
            ),

            # ── Pipeline: timing budget scales with work ──────────────────
            # Allow up to 3 seconds per result — total budget is proportional
            Implies(
                P.pipeline_wall_clock_ms > 0,
                P.pipeline_wall_clock_ms <= P.results_total * 3000,
            ),
            # Hard ceiling: never more than 60 seconds total
            Implies(P.pipeline_wall_clock_ms > 0, P.pipeline_wall_clock_ms <= 60000),

            # ── Error handling: all three error modes must exit exactly 1 ──
            Implies(P.missing_config_exit_code >= 0, P.missing_config_exit_code == 1),
            Implies(P.bad_yaml_exit_code >= 0, P.bad_yaml_exit_code == 1),
            Implies(P.missing_users_exit_code >= 0, P.missing_users_exit_code == 1),
            # All errors must use stderr (stdout must stay clean for piping)
            Implies(P.missing_config_exit_code == 1, P.errors_use_stderr),
            Implies(P.bad_yaml_exit_code == 1, P.errors_use_stderr),
            Implies(P.missing_users_exit_code == 1, P.errors_use_stderr),
            # No raw tracebacks on any error path
            Implies(P.missing_config_exit_code == 1, P.errors_are_clean),
            Implies(P.bad_yaml_exit_code == 1, P.errors_are_clean),
            # Errors must not land on stdout
            Implies(P.missing_config_exit_code == 1, P.errors_not_on_stdout),
            Implies(P.bad_yaml_exit_code == 1, P.errors_not_on_stdout),

            # ── Judge standalone: structural invariants ───────────────────
            # Exit 0 with zero evaluations is a silent failure
            Not(And(P.judge_exit_code == 0, P.judge_total_count == 0)),
            # Satisfied count can never exceed total — arithmetic consistency
            Implies(P.judge_total_count >= 1, P.judge_satisfied_count <= P.judge_total_count),
            Implies(P.judge_exit_code == 0, P.judge_output_valid),
            Implies(P.judge_exit_code == 0, P.judge_schema_correct),
        ]
