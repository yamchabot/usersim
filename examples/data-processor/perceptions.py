"""
perceptions.py — what can a domain expert observe about this processor?

Returns numeric values wherever possible.  Thresholds ("is this fast enough?")
belong in user constraint files — different users have different tolerances.
"""
from usersim.perceptions.library import throughput, run_perceptions


def compute(metrics: dict, **_) -> dict:
    n      = max(metrics.get("record_count", 1), 1)
    errors = metrics.get("error_count", 0)

    return {
        # ── Timing (ms) — users apply their own thresholds ────────────────
        "sort_ms":    metrics.get("sort_ms",    0.0),
        "search_ms":  metrics.get("search_ms",  0.0),
        "summary_ms": metrics.get("summary_ms", 0.0),
        "total_ms":   metrics.get("total_ms",   0.0),

        # ── Dataset size ──────────────────────────────────────────────────
        "record_count": n,

        # ── Derived rates ─────────────────────────────────────────────────
        "error_rate":       errors / n,                       # fraction of records with errors
        "sort_throughput":  n / max(metrics.get("sort_ms", 1.0), 0.001),  # records per ms

        # ── Definitional boolean: did the search find anything? ───────────
        # This is categorical — the search either returned results or it didn't.
        "search_returned_results": metrics.get("search_hits", 0) > 0,
    }


if __name__ == "__main__":
    run_perceptions(compute)
