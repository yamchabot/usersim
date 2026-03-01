"""CI engineer integrating usersim into a build pipeline."""
from usersim import Person
from usersim.judgement.z3_compat import Implies, And


class CIEngineer(Person):
    name    = "ci_engineer"
    role    = "Build/CI engineer"
    goal    = "integrate usersim into CI with confidence in exit codes and performance"
    pronoun = "they"

    def constraints(self, P):
        return [
            # ── Pipeline success path ─────────────────────────────────────
            # Must exit 0 on success
            Implies(P.pipeline_exit_code >= 0, P.pipeline_exit_code == 0),
            # Must complete within 60-second CI budget
            Implies(P.pipeline_wall_clock_ms > 0, P.pipeline_wall_clock_ms <= 60000),
            # Stdout must be machine-parseable JSON (so CI can pipe it)
            Implies(P.pipeline_exit_code == 0, P.output_is_valid_json),
            # Exit 0 means results exist — not an empty run
            Implies(P.pipeline_exit_code == 0, P.results_total >= 1),

            # ── Error cases: all three must exit non-zero ─────────────────
            Implies(P.missing_config_exit_code >= 0, P.missing_config_exit_code >= 1),
            Implies(P.bad_yaml_exit_code >= 0, P.bad_yaml_exit_code >= 1),
            Implies(P.missing_users_exit_code >= 0, P.missing_users_exit_code >= 1),
            # CI convention: failures should be exit 1, not arbitrary codes
            Implies(P.missing_config_exit_code >= 1, P.missing_config_exit_code == 1),
            Implies(P.bad_yaml_exit_code >= 1, P.bad_yaml_exit_code == 1),

            # ── Error output hygiene ──────────────────────────────────────
            # Errors go to stderr so stdout JSON piping is never polluted
            Implies(P.missing_config_exit_code >= 1, P.errors_use_stderr),
            Implies(P.bad_yaml_exit_code >= 1, P.errors_use_stderr),
            Implies(P.missing_users_exit_code >= 1, P.errors_use_stderr),
            # No raw tracebacks — CI logs must be readable
            Implies(P.missing_config_exit_code >= 1, P.errors_are_clean),
            Implies(P.bad_yaml_exit_code >= 1, P.errors_are_clean),
            # Errors must not land on stdout (would corrupt JSON consumers)
            Implies(P.missing_config_exit_code >= 1, P.errors_not_on_stdout),

            # ── Judge standalone ──────────────────────────────────────────
            # Judge must succeed and produce valid, schema-correct JSON
            Implies(P.judge_exit_code >= 0, P.judge_exit_code == 0),
            Implies(P.judge_exit_code == 0, P.judge_output_valid),
            Implies(P.judge_exit_code == 0, P.judge_schema_correct),
            Implies(P.judge_exit_code == 0, P.judge_has_results),
            # Judge must actually evaluate something
            Implies(P.judge_exit_code == 0, P.judge_total_count >= 1),
        ]
