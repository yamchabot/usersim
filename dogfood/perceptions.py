"""
perceptions.py — translate raw instrumentation metrics into domain observations.

Returns ALL facts for every scenario with safe defaults so that persona
constraints using Implies() have false antecedents for irrelevant scenarios
rather than raising AttributeError.

Default strategy:
  - Exit codes default to -1 (no real exit code is negative)
  - Counts default to 0
  - Booleans default to False
  - Timing defaults to 99999 (clearly not a real measurement)
"""
from usersim.perceptions.library import run_perceptions


def compute(metrics: dict, **_) -> dict:
    def num(key, default=0.0):
        v = metrics.get(key)
        if v is None:
            return default
        return float(v)

    def flag(key, default=False):
        return bool(metrics.get(key, default))

    return {
        # ── Pipeline execution (data_processor_example) ──────────────────
        "pipeline_exit_code":       num("exit_code", -1),
        "pipeline_wall_clock_ms":   num("wall_clock_ms", 0),
        "results_total":            num("results_total", 0),
        "results_satisfied":        num("results_satisfied", 0),
        # results_score intentionally omitted — Z3 computes pass-rate
        # relationships from results_satisfied and results_total directly
        "person_count":             num("person_count", 0),
        "scenario_count":           num("scenario_count", 0),
        "output_is_valid_json":     flag("stdout_valid_json"),
        "schema_is_correct":        flag("results_schema_valid"),
        "all_constraints_present":  flag("all_constraints_present"),

        # ── Scaffold (scaffold_and_validate) ─────────────────────────────
        "init_exit_code":           num("init_exit_code", -1),
        "scaffold_file_count":      num("scaffold_file_count", 0),
        "config_created":           flag("config_created"),
        "instrumentation_created":  flag("instrumentation_created"),
        "perceptions_created":      flag("perceptions_created"),
        "user_file_created":        flag("user_file_created"),
        "yaml_parseable":           flag("yaml_parseable"),

        # ── Error handling (bad_config) ──────────────────────────────────
        "missing_config_exit_code": num("missing_config_exit_code", -1),
        "bad_yaml_exit_code":       num("bad_yaml_exit_code", -1),
        "missing_users_exit_code":  num("missing_users_exit_code", -1),
        "errors_use_stderr":        flag("error_has_stderr"),
        "errors_are_clean":         flag("error_not_traceback"),
        "errors_not_on_stdout":     flag("error_not_on_stdout"),

        # ── Judge standalone (judge_standalone) ──────────────────────────
        "judge_exit_code":          num("judge_exit_code", -1),
        "judge_output_valid":       flag("judge_output_valid_json"),
        "judge_has_results":        flag("judge_has_results"),
        "judge_schema_correct":     flag("judge_schema_correct"),
        "judge_satisfied_count":    num("judge_satisfied_count", 0),
        "judge_total_count":        num("judge_total_count", 0),

        # ── Report (report_generation) ───────────────────────────────────
        "report_exit_code":         num("report_exit_code", -1),
        "report_file_created":      flag("report_file_created"),
        "report_file_size_bytes":   num("report_file_size_bytes", 0),
        "report_has_doctype":       flag("report_has_doctype"),
        "report_has_cards":         flag("report_has_cards"),
        "report_is_self_contained": flag("report_is_self_contained"),
    }


if __name__ == "__main__":
    run_perceptions(compute)
