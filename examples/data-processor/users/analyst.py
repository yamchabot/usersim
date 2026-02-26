"""
Analyst running ad-hoc queries on medium-to-large datasets.
Doesn't need instant responses — they fire off a query and context-switch.
But the full pipeline must finish within 30 seconds, and results must
be correct.  Tolerates a tiny error rate.
"""
from usersim import Person
from usersim.judgement.z3_compat import Implies


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
