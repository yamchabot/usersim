"""
search_quality_user.py — persona that cares about search correctness.

Uses the pre-built search constraint library with custom thresholds
appropriate for a small in-memory search over 20 documents.
"""
from usersim import Person
from usersim.constraints.search import result_count, precision, recall
from usersim.constraints.cli import timing
from usersim.judgement.z3_compat import And, Implies, named


class SearchQualityUser(Person):
    name    = "search_quality_user"
    role    = "Search Quality Analyst"
    goal    = "Ensure search results are relevant, bounded by top-k, and fast"
    pronoun = "they"

    def constraints(self, P):
        return [
            # Result count: must respect top_k, must return something
            *result_count(P, min_results=1, max_results=10),

            # Precision: at least 80% of returned results should be relevant
            *precision(P, min_pct=80),

            # Recall: find at least 60% of known relevant items
            *recall(P, min_pct=60),

            # top_k must be respected: results_returned <= top_k
            named("search/top-k-respected",
                  Implies(And(P.top_k >= 1, P.results_returned >= 0),
                          P.results_returned <= P.top_k)),

            # Timing: search should complete in under 100ms
            named("search/fast-enough",
                  Implies(P.query_time_ms >= 0, P.query_time_ms <= 100)),

            # Elapsed must be positive (search actually ran)
            named("search/elapsed-positive",
                  Implies(P.results_returned >= 1, P.elapsed_ms >= 1)),
        ]
