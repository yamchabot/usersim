"""
Simulated users for the data-processor example.

Constraints use named("group/check", expr) so the Group × Scenario coverage
matrix in the HTML report is populated.

Groups:
  correctness  — data integrity and error handling
  timing       — latency SLOs for each operation
  throughput   — records-per-ms rates
  resilience   — behaviour under degraded or unusual input
"""
from usersim import Person
from usersim.judgement.z3_compat import Implies, And, named


class Developer(Person):
    name        = "developer"
    description = "Interactive use; needs operations to feel responsive."

    def constraints(self, P):
        return [
            # correctness
            named("correctness/zero-errors-on-clean-data",
                  Implies(And(P.record_count >= 1, P.error_count == 0),
                          P.error_rate <= 0.0)),
            named("correctness/search-returns-results",
                  Implies(P.record_count >= 1, P.search_returned_results)),
            named("correctness/corrupt-records-reported",
                  Implies(P.error_count >= 1,
                          P.summary_count + P.error_count >= P.record_count - 1)),

            # timing
            named("timing/sort-interactive",      P.sort_ms    <= 1_000),
            named("timing/search-interactive",    P.search_ms  <= 2_000),
            named("timing/summary-interactive",   P.summary_ms <= 5_000),

            # resilience
            named("resilience/empty-completes-instantly",
                  Implies(P.record_count == 0, P.total_ms <= 5)),
            named("resilience/concurrent-sort-budget",
                  Implies(P.repetition_count >= 3, P.sort_ms <= 2_000)),
        ]


class Analyst(Person):
    name        = "analyst"
    description = "Batch queries; tolerates latency, cares about correctness and coverage."

    def constraints(self, P):
        return [
            # correctness
            named("correctness/tolerable-error-rate",
                  Implies(And(P.record_count >= 1, P.error_count == 0),
                          P.error_rate <= 0.01)),
            named("correctness/search-returns-results",
                  Implies(P.record_count >= 1, P.search_returned_results)),
            named("correctness/coverage-reported-accurately",
                  Implies(P.error_count >= 1,
                          P.summary_count + P.error_count >= P.record_count - 1)),
            named("correctness/empty-summary-is-zero",
                  Implies(P.record_count == 0, P.summary_count == 0)),

            # timing
            named("timing/pipeline-within-batch-window", P.total_ms <= 30_000),
            named("timing/summary-follows-sort",
                  Implies(P.sort_ms <= 10_000, P.summary_ms <= 5_000)),

            # throughput
            named("throughput/adequate-at-scale",
                  Implies(P.record_count >= 50_000, P.sort_throughput >= 50)),
        ]


class OpsEngineer(Person):
    name        = "ops_engineer"
    description = "Batch jobs; cares about SLOs and throughput under load."

    def constraints(self, P):
        return [
            # correctness
            named("correctness/tight-error-budget",
                  Implies(And(P.record_count >= 1, P.error_count == 0),
                          P.error_rate <= 0.001)),

            # timing
            named("timing/pipeline-within-job-window",   P.total_ms <= 30_000),
            named("timing/concurrent-within-2x-budget",
                  Implies(P.repetition_count >= 3, P.total_ms <= 60_000)),

            # throughput
            named("throughput/minimum-on-clean-data",
                  Implies(And(P.record_count >= 1, P.error_count == 0),
                          P.sort_throughput >= 100)),
            named("throughput/no-collapse-at-scale",
                  Implies(P.record_count >= 50_000, P.sort_throughput >= 50)),

            # resilience
            named("resilience/errors-dont-extend-processing",
                  Implies(And(P.error_count >= 1, P.record_count >= 100),
                          P.total_ms <= P.record_count * 0.5)),
        ]
