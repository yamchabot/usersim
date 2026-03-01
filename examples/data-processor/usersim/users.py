"""
Simulated users for the data-processor example.

Three personas with different concerns. Constraints use Implies() to scope
checks to relevant scenarios, creating genuine variation in coverage matrices.
"""
from usersim import Person
from usersim.judgement.z3_compat import Implies, And


class Developer(Person):
    name        = "developer"
    description = "Interactive use; needs operations to feel responsive."

    def constraints(self, P):
        return [
            # Clean data: zero errors and search finds results
            # (errors scenario has intentionally dirty input — skip error_rate there)
            Implies(And(P.record_count >= 1, P.error_count == 0), P.error_rate <= 0.0),
            Implies(P.record_count >= 1, P.search_returned_results),

            # Always: interactive timing (0 records → 0ms, trivially satisfied)
            P.sort_ms    <= 1_000,
            P.search_ms  <= 2_000,
            P.summary_ms <= 5_000,

            # Empty input: all operations complete near-instantly
            Implies(P.record_count == 0, P.total_ms <= 5),

            # Errors scenario: summary gracefully drops corrupt records
            # summary_count + error_count should equal record_count
            Implies(
                P.error_count >= 1,
                P.summary_count + P.error_count >= P.record_count - 1
            ),

            # Concurrent: worst-case sort still inside interactive budget
            Implies(P.repetition_count >= 3, P.sort_ms <= 2_000),
        ]


class Analyst(Person):
    name        = "analyst"
    description = "Batch queries; tolerates latency, cares about correctness and coverage."

    def constraints(self, P):
        return [
            # Clean data: tolerable error rate
            Implies(And(P.record_count >= 1, P.error_count == 0), P.error_rate <= 0.01),

            # Always: total wall time within batch window
            P.total_ms <= 30_000,

            # Normal data: search must find results
            Implies(P.record_count >= 1, P.search_returned_results),

            # If sort finishes quickly, summary should too
            Implies(P.sort_ms <= 10_000, P.summary_ms <= 5_000),

            # Errors scenario: coverage accurately reported
            Implies(
                P.error_count >= 1,
                P.summary_count + P.error_count >= P.record_count - 1
            ),

            # Empty scenario: summary returns count=0, not an error
            Implies(P.record_count == 0, P.summary_count == 0),

            # Large scenario: throughput at useful batch rate
            Implies(P.record_count >= 50_000, P.sort_throughput >= 50),
        ]


class OpsEngineer(Person):
    name        = "ops_engineer"
    description = "Batch jobs; cares about SLOs and throughput under load."

    def constraints(self, P):
        return [
            # Clean data: tight error budget
            Implies(And(P.record_count >= 1, P.error_count == 0), P.error_rate <= 0.001),

            # Always: pipeline within job window
            P.total_ms <= 30_000,

            # Clean non-empty data: minimum throughput
            Implies(And(P.record_count >= 1, P.error_count == 0), P.sort_throughput >= 100),

            # Concurrent: worst-case timing fits 2x budget
            Implies(
                P.repetition_count >= 3,
                P.total_ms <= 60_000
            ),

            # Large: throughput doesn't collapse at scale
            Implies(
                P.record_count >= 50_000,
                P.sort_throughput >= 50
            ),

            # Errors: corrupt records don't disproportionately extend processing
            Implies(
                And(P.error_count >= 1, P.record_count >= 100),
                P.total_ms <= P.record_count * 0.5
            ),
        ]
