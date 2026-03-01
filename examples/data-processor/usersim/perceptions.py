"""
perceptions.py — what can a domain expert observe about this processor?

Returns numeric values; thresholds belong in user constraint files.
"""
from usersim.perceptions.library import throughput, run_perceptions


def compute(metrics: dict, **_) -> dict:
    n      = max(metrics.get("record_count", 0), 1)
    errors = metrics.get("error_count", 0)
    reps   = max(metrics.get("repetition_count", 1), 1)

    return {
        # Timing (ms)
        "sort_ms":         metrics.get("sort_ms",    0.0),
        "search_ms":       metrics.get("search_ms",  0.0),
        "summary_ms":      metrics.get("summary_ms", 0.0),
        "total_ms":        metrics.get("total_ms",   0.0),

        # Dataset properties
        "record_count":    metrics.get("record_count", 0),
        "summary_count":   metrics.get("summary_count", 0),
        "search_hits":     metrics.get("search_hits", 0),
        "repetition_count": reps,

        # Error rates
        "error_count":     errors,
        "error_rate":      errors / n,

        # Throughput
        "sort_throughput": throughput(metrics, "record_count", "sort_ms"),

        # Search correctness
        "search_returned_results": metrics.get("search_hits", 0) > 0,

        # Summary coverage: what fraction of records were included in the summary?
        # < 1.0 means some records had missing/corrupt fields (dropped from aggregation)
        "summary_coverage": metrics.get("summary_count", 0) / n,
    }


if __name__ == "__main__":
    run_perceptions(compute)
