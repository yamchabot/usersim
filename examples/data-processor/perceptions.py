"""
perceptions.py — what does a human perceive about this processor?

Translates raw timing numbers into meaningful facts about the experience.
Thresholds are based on common UX research guidelines:
  <100ms  → feels instant
  <1000ms → noticeable but acceptable for most tasks
  <10s    → tolerable for batch operations
"""
from usersim.perceptions.library import threshold


def compute(metrics: dict, **_) -> dict:
    return {
        # Sort speed — sorting is the most common operation
        "sort_feels_instant":    threshold(metrics, "sort_ms",    max=100),
        "sort_is_acceptable":    threshold(metrics, "sort_ms",    max=1_000),
        "sort_finishes_in_time": threshold(metrics, "sort_ms",    max=10_000),

        # Search speed — interactive queries need a fast response
        "search_feels_instant":  threshold(metrics, "search_ms",  max=100),
        "search_is_acceptable":  threshold(metrics, "search_ms",  max=2_000),

        # Summary/aggregate speed — typically less latency-sensitive
        "summary_is_fast":       threshold(metrics, "summary_ms", max=500),
        "summary_is_acceptable": threshold(metrics, "summary_ms", max=5_000),

        # End-to-end: full pipeline within a time budget
        "pipeline_under_1s":     threshold(metrics, "total_ms",   max=1_000),
        "pipeline_under_30s":    threshold(metrics, "total_ms",   max=30_000),

        # Correctness: search must return results when they exist
        "search_returns_results": metrics.get("search_hits", 0) > 0,

        # Reliability
        "no_errors": metrics.get("error_count", 0) == 0,
    }
