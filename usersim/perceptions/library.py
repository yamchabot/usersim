"""
Default perception library.

These are pure functions: (metrics_dict → bool/float).
Use them in your perceptions.py to turn raw metrics into human-meaningful facts.

All functions take the 'metrics' dict from metrics.json as their first argument.
They are intentionally simple — most are just named thresholds so that your
perceptions.py reads like a specification, not an algorithm.

Example
-------
from usersim.perceptions.library import threshold, ratio, in_range

facts = {
    "loads_fast":        threshold(m, "load_time_ms", max=500),
    "low_error_rate":    threshold(m, "error_rate",   max=0.01),
    "good_cache_hit":    threshold(m, "cache_hit_pct", min=0.80),
    "acceptable_size":   in_range(m,  "bundle_kb",    0, 250),
    "cpu_utilisation":   ratio(m,     "cpu_used", "cpu_total"),
}
"""
from __future__ import annotations


# ── Boolean thresholds ─────────────────────────────────────────────────────────

def threshold(
    metrics: dict,
    key: str,
    *,
    min: float | None = None,
    max: float | None = None,
    default: bool = False,
) -> bool:
    """
    True if metrics[key] satisfies the min/max bounds.

    threshold(m, "load_ms", max=500)   → True when load_ms ≤ 500
    threshold(m, "score",   min=0.7)   → True when score ≥ 0.7
    """
    val = metrics.get(key)
    if val is None:
        return default
    if min is not None and val < min:
        return False
    if max is not None and val > max:
        return False
    return True


def in_range(metrics: dict, key: str, lo: float, hi: float, default: bool = False) -> bool:
    """True if lo ≤ metrics[key] ≤ hi."""
    val = metrics.get(key)
    if val is None:
        return default
    return lo <= val <= hi


def equals(metrics: dict, key: str, value, default: bool = False) -> bool:
    """True if metrics[key] == value."""
    val = metrics.get(key)
    if val is None:
        return default
    return val == value


def flag(metrics: dict, key: str, default: bool = False) -> bool:
    """True if metrics[key] is truthy."""
    val = metrics.get(key)
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    if isinstance(val, str):
        return val.lower() in ("true", "yes", "1")
    return bool(val)


# ── Numeric extractions ────────────────────────────────────────────────────────

def ratio(metrics: dict, numerator: str, denominator: str, default: float = 0.0) -> float:
    """metrics[numerator] / metrics[denominator], or default if denominator is 0."""
    n = metrics.get(numerator, 0)
    d = metrics.get(denominator, 0)
    if not d:
        return default
    return n / d


def normalise(metrics: dict, key: str, lo: float, hi: float, default: float = 0.5) -> float:
    """Map metrics[key] from [lo, hi] to [0.0, 1.0], clamped."""
    val = metrics.get(key)
    if val is None:
        return default
    if hi == lo:
        return 0.5
    return max(0.0, min(1.0, (val - lo) / (hi - lo)))


def get(metrics: dict, key: str, default=None):
    """Plain passthrough — for when you just want the raw metric value."""
    return metrics.get(key, default)


# ── Statistical helpers ────────────────────────────────────────────────────────

def percentile_rank(value: float, population: list[float]) -> float:
    """Fraction of population values ≤ value.  Returns 0.0–1.0."""
    if not population:
        return 0.0
    return sum(1 for v in population if v <= value) / len(population)


def z_score(value: float, mean: float, std: float) -> float:
    """Standard score.  Returns 0.0 when std==0."""
    if std == 0:
        return 0.0
    return (value - mean) / std


def moving_average(values: list[float], window: int = 5) -> float:
    """Mean of the last `window` values."""
    if not values:
        return 0.0
    return sum(values[-window:]) / min(len(values), window)


# ── Convenience wrappers for common patterns ───────────────────────────────────

def is_fast(metrics: dict, key: str, *, excellent_ms=100, acceptable_ms=500) -> bool:
    """True if metrics[key] (ms) is within acceptable_ms."""
    return threshold(metrics, key, max=acceptable_ms)


def is_small(metrics: dict, key: str, *, max_kb=500) -> bool:
    """True if metrics[key] (kb) is within max_kb."""
    return threshold(metrics, key, max=max_kb)


def has_no_errors(metrics: dict, key: str = "error_count") -> bool:
    """True if error count is 0."""
    return metrics.get(key, 0) == 0


def above_threshold(metrics: dict, key: str, pct: float) -> bool:
    """True if metrics[key] ≥ pct (for rates / percentages expressed as 0–1)."""
    return threshold(metrics, key, min=pct)
