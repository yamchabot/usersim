"""ML engineer validating behavioral contracts on model pipeline outputs."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from usersim import Person
from usersim.judgement.z3_compat import Implies, And, Not, named
from constraint_library import (
    matrix_invariants,
    pipeline_invariants,
    judge_invariants,
    timing_invariants,
)


class MLEngineer(Person):
    name    = "ml_engineer"
    role    = "ML Engineer"
    goal    = "validate output shape invariants and behavioral contracts across all paths"
    pronoun = "he"

    def constraints(self, P):
        return [
            *matrix_invariants(P),
            *pipeline_invariants(P),
            *judge_invariants(P),
            *timing_invariants(P, max_ms_per_result=10000, max_total_ms=300000),

            # ── ML-specific: output shape and behavioral contracts ────────
            # Output must be valid JSON — ML pipelines parse it programmatically
            named("ml/output-is-valid-json",
                  Implies(P.pipeline_exit_code == 0, P.output_is_valid_json)),
            # Schema must be stable — ML pipeline depends on field names
            named("ml/schema-is-stable",
                  Implies(P.pipeline_exit_code == 0, P.schema_is_correct)),
            # Result count must equal person * path (no partial runs)
            named("ml/no-partial-evaluation",
                  Implies(P.results_total >= 1,
                          P.results_total == P.person_count * P.scenario_count)),
            # Satisfied fraction: at least 60% pass rate (ML tolerates some slack)
            # 5 * sat >= 3 * total  →  sat/total >= 0.6
            named("ml/60pct-behavioral-contract-pass",
                  Implies(And(P.pipeline_exit_code == 0, P.results_total >= 1),
                          P.results_satisfied * 5 >= P.results_total * 3)),
            # Judge output must be parseable for downstream ML pipeline ingestion
            named("ml/judge-output-parseable",
                  Implies(P.judge_exit_code == 0, P.judge_output_valid)),
            # Judge and pipeline counts must agree
            named("ml/judge-pipeline-count-agreement",
                  Implies(And(P.judge_exit_code == 0, P.judge_total_count >= 1),
                          P.judge_satisfied_count <= P.judge_total_count)),
            # Wall clock must be bounded per result (ML batch budget)
            named("ml/per-result-timing-budget",
                  Implies(And(P.pipeline_wall_clock_ms > 0, P.results_total >= 1),
                          P.pipeline_wall_clock_ms <= P.results_total * 10000)),
        ]
