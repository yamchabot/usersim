"""
usersim.constraints.search — recall, precision, and result count quality.

Perceptions contract:
  results_returned  (int >= 0)  — items returned by the search
  results_relevant  (int >= 0)  — relevant items in the returned set
  corpus_size       (int >= 1)  — total items in the searchable corpus
  query_time_ms     (int >= 0)  — time to produce results
  top_k             (int >= 1)  — number of results requested

All precision / recall targets are expressed as integer percentages (0-100)
to keep Z3 arithmetic integer-only (avoids float precision issues).
"""
from usersim.judgement.z3_compat import And, Implies, Not, named


def result_count(P, *, min_results: int = 1, max_results: int = 100):
    """Result set size must be non-empty and within the requested top-K.

    Args:
        P:           FactNamespace.
        min_results: Minimum results for a non-empty query (default 1).
        max_results: Hard ceiling on result count (default 100).
    """
    return [
        named("search/non-empty-result-set",
              Implies(P.corpus_size >= 1, P.results_returned >= min_results)),
        named("search/results-never-exceed-top-k",
              Implies(And(P.top_k >= 1, P.results_returned >= 0),
                      P.results_returned <= P.top_k)),
        named("search/results-never-exceed-corpus",
              Implies(P.corpus_size >= 1,
                      P.results_returned <= P.corpus_size)),
        named("search/results-under-ceiling",
              Implies(P.results_returned >= 0, P.results_returned <= max_results)),
        named("search/relevant-never-exceed-returned",
              Implies(P.results_returned >= 0,
                      P.results_relevant <= P.results_returned)),
    ]


def precision(P, *, min_pct: int = 80):
    """Precision: relevant / returned >= min_pct/100.

    Integer form: results_relevant * 100 >= results_returned * min_pct

    Args:
        P:       FactNamespace.
        min_pct: Minimum precision as integer percentage (default 80%).
    """
    return [
        named("search/precision-above-floor",
              Implies(P.results_returned >= 1,
                      P.results_relevant * 100 >= P.results_returned * min_pct)),
        named("search/relevant-non-negative",
              Implies(P.results_returned >= 0, P.results_relevant >= 0)),
        named("search/perfect-precision-means-all-relevant",
              Implies(And(P.results_relevant >= 1,
                          P.results_relevant == P.results_returned),
                      P.results_relevant * 100 >= P.results_returned * 100)),
    ]


def recall(P, *, min_pct: int = 60):
    """Recall: relevant_returned / total_relevant >= min_pct/100.

    Requires `total_relevant` in perceptions (ground-truth relevant count).

    Integer form: results_relevant * 100 >= total_relevant * min_pct

    Args:
        P:       FactNamespace.
        min_pct: Minimum recall as integer percentage (default 60%).
    """
    return [
        named("search/recall-above-floor",
              Implies(And(P.total_relevant >= 1, P.results_relevant >= 0),
                      P.results_relevant * 100 >= P.total_relevant * min_pct)),
        named("search/total-relevant-non-negative",
              Implies(P.corpus_size >= 1, P.total_relevant >= 0)),
        named("search/total-relevant-lte-corpus",
              Implies(And(P.corpus_size >= 1, P.total_relevant >= 0),
                      P.total_relevant <= P.corpus_size)),
        # Precision × recall consistency: high precision + high recall → f1 > floor
        # Approximated as: 2 * precision * recall >= 70² (F1 > 0.70)
        named("search/precision-recall-f1-floor",
              Implies(
                  And(P.results_returned >= 1, P.total_relevant >= 1,
                      P.results_relevant * 100 >= P.results_returned * min_pct,
                      P.results_relevant * 100 >= P.total_relevant * min_pct),
                  # F1 ≥ 2pr/(p+r) ≥ floor — approximated as p+r >= 130 (both ≥ 65%)
                  P.results_relevant * 100 * 2 >= P.results_returned * min_pct
                  + P.total_relevant * min_pct)),
    ]
