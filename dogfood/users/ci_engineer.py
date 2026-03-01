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
            # ── Pipeline: structural ──────────────────────────────────────
            Not(And(P.pipeline_exit_code == 0, P.results_total == 0)),
            Implies(P.pipeline_exit_code == 0, P.results_satisfied == P.results_total),
            Implies(P.pipeline_exit_code == 0, P.output_is_valid_json),

            # ── Matrix: total must equal persons × scenarios ──────────────
            Implies(
                P.results_total >= 1,
                P.results_total == P.person_count * P.scenario_count,
            ),

            # ── Timing: budget scales with matrix dimensions ───────────────
            # Total time <= 3 seconds per cell in the matrix
            Implies(
                P.pipeline_wall_clock_ms > 0,
                P.pipeline_wall_clock_ms <= P.person_count * P.scenario_count * 3000,
            ),
            # Hard ceiling regardless of matrix size
            Implies(P.pipeline_wall_clock_ms > 0, P.pipeline_wall_clock_ms <= 60000),
            # Timing must be plausible — at least 10ms per scenario
            Implies(
                P.pipeline_wall_clock_ms > 0,
                P.pipeline_wall_clock_ms >= P.scenario_count * 10,
            ),

            # ── Error handling: all three modes must agree ─────────────────
            # All three error exits must be exactly 1 — they sum to 3
            Implies(
                And(P.missing_config_exit_code >= 0,
                    P.bad_yaml_exit_code >= 0,
                    P.missing_users_exit_code >= 0),
                P.missing_config_exit_code
                + P.bad_yaml_exit_code
                + P.missing_users_exit_code == 3,
            ),
            # All error modes must use stderr and be clean
            Implies(
                And(P.missing_config_exit_code == 1, P.bad_yaml_exit_code == 1),
                P.errors_use_stderr,
            ),
            Implies(
                And(P.missing_config_exit_code == 1, P.bad_yaml_exit_code == 1),
                P.errors_are_clean,
            ),
            Implies(
                And(P.missing_config_exit_code == 1, P.bad_yaml_exit_code == 1),
                P.errors_not_on_stdout,
            ),

            # ── JSON output: schema coherence chain ───────────────────────
            # Valid JSON + correct schema → results must exist
            Implies(
                And(P.output_is_valid_json, P.schema_is_correct),
                P.results_total >= 1,
            ),
            # Valid JSON + results → satisfied must be <= total
            Implies(
                And(P.output_is_valid_json, P.results_total >= 1),
                P.results_satisfied <= P.results_total,
            ),

            # ── Judge: structural + consistency ───────────────────────────
            Not(And(P.judge_exit_code == 0, P.judge_total_count == 0)),
            Implies(P.judge_total_count >= 1, P.judge_satisfied_count <= P.judge_total_count),
            Implies(P.judge_exit_code == 0, P.judge_output_valid),
            Implies(P.judge_exit_code == 0, P.judge_schema_correct),
            # Judge satisfied count must be plausible fraction of total
            Implies(
                And(P.judge_exit_code == 0, P.judge_total_count >= 1),
                P.judge_satisfied_count * 2 >= P.judge_total_count,
            ),
        ]
