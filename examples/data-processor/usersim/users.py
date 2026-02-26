"""
Simulated users for the data-processor example.

Three personas with different latency tolerances and correctness requirements.
All share the same numeric perceptions (sort_ms, search_ms, etc.) but apply
their own thresholds via Z3 constraints.
"""
from usersim import Person
from usersim.judgement.z3_compat import Implies


class Developer(Person):
    name        = "developer"
    description = "Interactive use; needs operations to feel responsive."

    def constraints(self, P):
        return [
            P.error_rate  <= 0.0,       # any error is a blocker
            P.sort_ms     <= 1_000,     # sort should finish in under a second
            P.search_ms   <= 2_000,     # search can be a little slower
            P.summary_ms  <= 5_000,     # aggregation has most slack
            P.search_returned_results,  # search must actually find things
        ]


class Analyst(Person):
    name        = "analyst"
    description = "Batch queries; tolerates latency, needs correctness and completion."

    def constraints(self, P):
        return [
            P.error_rate  <= 0.01,      # tolerates up to 1% errors
            P.total_ms    <= 30_000,    # full pipeline must finish in 30s
            P.search_returned_results,  # correctness: search must find results
            # If sort completes in time, summary should too (paired operations)
            Implies(P.sort_ms <= 10_000, P.summary_ms <= 5_000),
        ]


class OpsEngineer(Person):
    name        = "ops_engineer"
    description = "Batch jobs; needs pipeline to finish on time with high throughput."

    def constraints(self, P):
        return [
            P.error_rate      <= 0.001,     # pages at 0.1% error rate
            P.total_ms        <= 30_000,    # job window is 30s
            P.sort_throughput >= 100,       # at least 100 records/ms sorted
        ]
