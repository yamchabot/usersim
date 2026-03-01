"""
constraint_library.py — reusable, named constraint groups for usersim dogfood.

Constraint groups are plain functions that accept a FactNamespace (P) and return
a list of named Z3 expressions. Personas import groups and compose them with
their own persona-specific constraints.

Naming convention: "group/check-name"
  group = the subsystem or category (matrix, pipeline, timing, errors, report,
          scaffold, judge)
  check = what specifically is being verified

Usage in a persona:
    from constraint_library import matrix_invariants, report_invariants

    def constraints(self, P):
        return [
            *matrix_invariants(P),
            *report_invariants(P),
            named("my-persona/custom-check", P.something >= 1),
        ]
"""
from usersim.judgement.z3_compat import Implies, And, Not, named


# ── Matrix ────────────────────────────────────────────────────────────────────

def matrix_invariants(P):
    """Structural invariants for the person × scenario result matrix."""
    return [
        named("matrix/total-equals-persons-times-scenarios",
              Implies(P.results_total >= 1,
                      P.results_total == P.person_count * P.scenario_count)),
        named("matrix/no-results-without-persons",
              Not(And(P.results_total >= 1, P.person_count == 0))),
        named("matrix/no-results-without-scenarios",
              Not(And(P.results_total >= 1, P.scenario_count == 0))),
        named("matrix/total-implies-at-least-one-person",
              Implies(P.results_total >= 1, P.person_count >= 1)),
        named("matrix/total-implies-at-least-one-scenario",
              Implies(P.results_total >= 1, P.scenario_count >= 1)),
        named("matrix/satisfied-never-exceeds-total",
              Implies(P.results_total >= 1, P.results_satisfied <= P.results_total)),
        named("matrix/satisfied-consistent-with-dimensions",
              Implies(And(P.results_total >= 1, P.results_satisfied >= 1),
                      P.results_satisfied <= P.person_count * P.scenario_count)),
    ]


# ── Pipeline ──────────────────────────────────────────────────────────────────

def pipeline_invariants(P):
    """Structural invariants for the full pipeline run."""
    return [
        named("pipeline/exit-0-implies-results-exist",
              Not(And(P.pipeline_exit_code == 0, P.results_total == 0))),
        named("pipeline/exit-0-implies-valid-json",
              Implies(P.pipeline_exit_code == 0, P.output_is_valid_json)),
        named("pipeline/exit-0-implies-correct-schema",
              Implies(P.pipeline_exit_code == 0, P.schema_is_correct)),
        named("pipeline/valid-json-and-schema-implies-results",
              Implies(And(P.output_is_valid_json, P.schema_is_correct),
                      P.results_total >= 1)),
        named("pipeline/valid-json-implies-satisfied-lte-total",
              Implies(And(P.output_is_valid_json, P.results_total >= 1),
                      P.results_satisfied <= P.results_total)),
        named("pipeline/exit-0-implies-constraints-present",
              Implies(P.pipeline_exit_code == 0, P.all_constraints_present)),
    ]


# ── Timing ────────────────────────────────────────────────────────────────────

def timing_invariants(P, max_ms_per_result=3000, max_total_ms=60000):
    """Timing budget constraints: proportional to work, bounded above and below."""
    return [
        named("timing/budget-scales-with-result-count",
              Implies(P.pipeline_wall_clock_ms > 0,
                      P.pipeline_wall_clock_ms <= P.results_total * max_ms_per_result)),
        named("timing/budget-scales-with-matrix-dimensions",
              Implies(P.pipeline_wall_clock_ms > 0,
                      P.pipeline_wall_clock_ms
                      <= P.person_count * P.scenario_count * max_ms_per_result)),
        named("timing/hard-ceiling",
              Implies(P.pipeline_wall_clock_ms > 0,
                      P.pipeline_wall_clock_ms <= max_total_ms)),
        named("timing/floor-at-least-10ms-per-scenario",
              Implies(P.pipeline_wall_clock_ms > 0,
                      P.pipeline_wall_clock_ms >= P.scenario_count * 10)),
        named("timing/non-zero-when-results-exist",
              Implies(P.results_total >= 1, P.pipeline_wall_clock_ms >= 1)),
    ]


# ── Error handling ────────────────────────────────────────────────────────────

def error_handling_invariants(P):
    """All error modes must exit exactly 1, use stderr, and be clean."""
    return [
        # Exit codes
        named("errors/missing-config-exits-1",
              Implies(P.missing_config_exit_code >= 0, P.missing_config_exit_code == 1)),
        named("errors/bad-yaml-exits-1",
              Implies(P.bad_yaml_exit_code >= 0, P.bad_yaml_exit_code == 1)),
        named("errors/missing-users-exits-1",
              Implies(P.missing_users_exit_code >= 0, P.missing_users_exit_code == 1)),
        # Sum invariant: all three exit codes must sum to exactly 3
        named("errors/all-three-exit-codes-sum-to-3",
              Implies(
                  And(P.missing_config_exit_code >= 0,
                      P.bad_yaml_exit_code >= 0,
                      P.missing_users_exit_code >= 0),
                  P.missing_config_exit_code
                  + P.bad_yaml_exit_code
                  + P.missing_users_exit_code == 3)),
        # Stderr routing — each mode independently and all together
        named("errors/missing-config-uses-stderr",
              Implies(P.missing_config_exit_code == 1, P.errors_use_stderr)),
        named("errors/bad-yaml-uses-stderr",
              Implies(P.bad_yaml_exit_code == 1, P.errors_use_stderr)),
        named("errors/missing-users-uses-stderr",
              Implies(P.missing_users_exit_code == 1, P.errors_use_stderr)),
        named("errors/all-modes-agree-on-stderr",
              Implies(And(P.missing_config_exit_code == 1, P.bad_yaml_exit_code == 1),
                      P.errors_use_stderr)),
        # Clean messages (no tracebacks)
        named("errors/missing-config-clean-message",
              Implies(P.missing_config_exit_code == 1, P.errors_are_clean)),
        named("errors/bad-yaml-clean-message",
              Implies(P.bad_yaml_exit_code == 1, P.errors_are_clean)),
        named("errors/missing-users-clean-message",
              Implies(P.missing_users_exit_code == 1, P.errors_are_clean)),
        # Stdout must not be polluted
        named("errors/missing-config-not-on-stdout",
              Implies(P.missing_config_exit_code == 1, P.errors_not_on_stdout)),
        named("errors/bad-yaml-not-on-stdout",
              Implies(P.bad_yaml_exit_code == 1, P.errors_not_on_stdout)),
    ]


# ── Report ────────────────────────────────────────────────────────────────────

def report_invariants(P):
    """HTML report quality and size invariants."""
    return [
        # Structural presence
        named("report/created-when-exit-0",
              Implies(P.report_exit_code == 0, P.report_file_created)),
        named("report/has-doctype",
              Implies(P.report_file_created, P.report_has_doctype)),
        named("report/is-self-contained",
              Implies(P.report_file_created, P.report_is_self_contained)),
        named("report/has-person-cards",
              Implies(P.report_file_created, P.report_has_cards)),
        # Majority-vote quality: all 3 structural signals must hold
        named("report/all-quality-signals-present",
              Implies(P.report_file_created,
                      P.report_has_cards + P.report_is_self_contained
                      + P.report_has_doctype >= 3)),
        # Not empty
        named("report/non-empty",
              Not(And(P.report_file_created, P.report_file_size_bytes == 0))),
        # Size scales with result count
        named("report/size-scales-with-total-results",
              Implies(And(P.report_file_created, P.results_total >= 1),
                      P.report_file_size_bytes >= P.results_total * 200)),
        # Size scales with both result count and persona count
        named("report/size-scales-with-matrix-dimensions",
              Implies(And(P.report_file_created, P.results_total >= 1,
                          P.person_count >= 1),
                      P.report_file_size_bytes >= P.results_total * P.person_count * 50)),
        # Full quality → larger size floor
        named("report/full-quality-implies-larger-size",
              Implies(And(P.report_has_doctype, P.report_is_self_contained,
                          P.report_has_cards),
                      P.report_file_size_bytes >= 8000)),
        # Cross-system coherence: pipeline results → report must reflect them
        named("report/pipeline-results-reflected-in-size",
              Implies(And(P.pipeline_exit_code == 0, P.report_file_created,
                          P.results_total >= 1),
                      P.report_file_size_bytes >= P.results_total * 200)),
    ]


# ── Scaffold ──────────────────────────────────────────────────────────────────

def scaffold_invariants(P):
    """Init scaffold completeness and internal consistency."""
    return [
        # Exit code
        named("scaffold/exit-0",
              Implies(P.init_exit_code >= 0, P.init_exit_code == 0)),
        # Individual files
        named("scaffold/config-created",
              Implies(P.init_exit_code == 0, P.config_created)),
        named("scaffold/instrumentation-created",
              Implies(P.init_exit_code == 0, P.instrumentation_created)),
        named("scaffold/perceptions-created",
              Implies(P.init_exit_code == 0, P.perceptions_created)),
        named("scaffold/user-file-created",
              Implies(P.init_exit_code == 0, P.user_file_created)),
        named("scaffold/yaml-parseable",
              Implies(P.init_exit_code == 0, P.yaml_parseable)),
        # Logical dependency: can't parse a file that doesn't exist
        named("scaffold/yaml-parseable-implies-config-exists",
              Implies(P.yaml_parseable, P.config_created)),
        # Sum invariant: 4 boolean file flags must all be True
        named("scaffold/all-four-files-present-sum",
              Implies(P.init_exit_code == 0,
                      P.config_created + P.instrumentation_created
                      + P.perceptions_created + P.user_file_created == 4)),
        # File count lower bound from individual flags
        named("scaffold/file-count-gte-sum-of-flags",
              Implies(P.init_exit_code == 0,
                      P.scaffold_file_count >= P.config_created
                      + P.instrumentation_created + P.perceptions_created
                      + P.user_file_created)),
        # Hard minimum
        named("scaffold/file-count-at-least-4",
              Implies(P.init_exit_code == 0, P.scaffold_file_count >= 4)),
    ]


# ── Judge ─────────────────────────────────────────────────────────────────────

def judge_invariants(P):
    """Standalone judge subcommand structural invariants."""
    return [
        # Can't succeed with nothing evaluated
        named("judge/no-empty-success",
              Not(And(P.judge_exit_code == 0, P.judge_total_count == 0))),
        # Exact exit 0
        named("judge/exit-0",
              Implies(P.judge_exit_code >= 0, P.judge_exit_code == 0)),
        # Output quality
        named("judge/output-is-valid-json",
              Implies(P.judge_exit_code == 0, P.judge_output_valid)),
        named("judge/schema-correct",
              Implies(P.judge_exit_code == 0, P.judge_schema_correct)),
        named("judge/has-results",
              Implies(P.judge_exit_code == 0, P.judge_has_results)),
        # Count semantics
        named("judge/total-count-positive-on-success",
              Implies(P.judge_exit_code == 0, P.judge_total_count >= 1)),
        named("judge/satisfied-never-exceeds-total",
              Implies(P.judge_total_count >= 1,
                      P.judge_satisfied_count <= P.judge_total_count)),
        # At least one persona satisfied in a well-formed run
        named("judge/at-least-one-satisfied",
              Implies(And(P.judge_exit_code == 0, P.judge_total_count >= 1),
                      P.judge_satisfied_count >= 1)),
        # Pass rate: at least half must satisfy
        named("judge/at-least-50pct-satisfied",
              Implies(And(P.judge_exit_code == 0, P.judge_total_count >= 1),
                      P.judge_satisfied_count * 2 >= P.judge_total_count)),
    ]
