"""
Analyst running ad-hoc queries on medium-sized datasets.
Doesn't need instant responses, but the full pipeline must finish
within 30 seconds — they're watching it run and will give up otherwise.
Correctness is non-negotiable.
"""
from usersim import Person
from usersim.judgement.z3_compat import Implies


class Analyst(Person):
    name        = "analyst"
    description = "Runs queries on datasets; tolerates some latency but needs correctness."

    def constraints(self, P):
        return [
            P.no_errors,
            P.pipeline_under_30s,      # full pipeline must finish
            P.search_returns_results,  # correctness: search must work
            # For large datasets, at least summarise should still be reasonable
            Implies(P.sort_finishes_in_time, P.summary_is_acceptable),
        ]
