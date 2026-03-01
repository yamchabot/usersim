"""
Perception library.

Use these in perceptions.py to derive human-meaningful observations from
raw instrumentation metrics.

DESIGN PRINCIPLE
────────────────
Perceptions answer: "What can a domain expert observe about the system?"
They should mostly be *numeric* — pass the measured values through, possibly
transformed into more meaningful units (rate, throughput, normalised score).

Thresholds — "is this fast enough?" "is the error rate acceptable?" — are
judgements that belong in user constraint files, not here.  Different users
have different tolerances.  Let Z3 enforce those in users/*.py:

    # perceptions.py — ✓ correct
    def compute(metrics, **_):
        return {
            "response_ms": metrics["response_ms"],   # numeric
            "error_rate":  metrics["error_count"] / metrics["total"],
        }

    # users/power_user.py — thresholds live here
    def constraints(self, P):
        return [
            P.response_ms <= 100,   # power user wants instant
            P.error_rate  <= 0.001,
        ]

    # users/casual_user.py — different thresholds
    def constraints(self, P):
        return [
            P.response_ms <= 2000,  # casual user barely notices 2s
            P.error_rate  <= 0.05,
        ]

Boolean perceptions are fine for *definitional* facts — things that are
categorically true or false regardless of who is asking:

    "has_results":    search_hits > 0          # either found something or didn't
    "is_multi_node":  node_count > 1           # objective topology fact

Avoid booleans for continuous values where people disagree on the cutoff.
"""
from __future__ import annotations
import math


# ── Numeric passthrough & derivation ──────────────────────────────────────────
# These are the primary helpers.  Perceptions should mostly use these.

def get(metrics: dict, key: str, default: float = 0.0):
    """Return metrics[key] unchanged.  Use for raw passthrough."""
    return metrics.get(key, default)


def rate(metrics: dict, count_key: str, total_key: str, default: float = 0.0) -> float:
    """Fraction: metrics[count_key] / metrics[total_key].  Safe division."""
    n = metrics.get(count_key, 0)
    d = metrics.get(total_key, 0)
    return n / d if d else default


def ratio(metrics: dict, numerator: str, denominator: str, default: float = 0.0) -> float:
    """Ratio of two metric values.  Safe division."""
    n = metrics.get(numerator, 0)
    d = metrics.get(denominator, 0)
    return n / d if d else default


def throughput(metrics: dict, count_key: str, time_key: str, default: float = 0.0) -> float:
    """Items per unit time: metrics[count_key] / metrics[time_key]."""
    n = metrics.get(count_key, 0)
    t = metrics.get(time_key, 0)
    return n / t if t else default


def normalise(metrics: dict, key: str, lo: float, hi: float, default: float = 0.5) -> float:
    """Map metrics[key] from [lo, hi] to [0.0, 1.0], clamped."""
    val = metrics.get(key)
    if val is None:
        return default
    if hi == lo:
        return 0.5
    return max(0.0, min(1.0, (val - lo) / (hi - lo)))


def delta(metrics: dict, key: str, baseline: float, default: float = 0.0) -> float:
    """Signed difference: metrics[key] - baseline."""
    val = metrics.get(key)
    return (val - baseline) if val is not None else default


def change_pct(metrics: dict, key: str, baseline: float, default: float = 0.0) -> float:
    """Percentage change relative to baseline: (val - baseline) / baseline * 100."""
    val = metrics.get(key)
    if val is None or baseline == 0:
        return default
    return (val - baseline) / baseline * 100.0


def log_scale(metrics: dict, key: str, base: float = 10.0, default: float = 0.0) -> float:
    """log_base(metrics[key]).  Useful for highly skewed distributions."""
    val = metrics.get(key)
    if val is None or val <= 0:
        return default
    return math.log(val, base)


# ── Statistical helpers ────────────────────────────────────────────────────────

def z_score(value: float, mean: float, std: float) -> float:
    """Standard score.  Returns 0.0 when std == 0."""
    return (value - mean) / std if std else 0.0


def percentile_rank(value: float, population: list[float]) -> float:
    """Fraction of population values ≤ value.  Returns 0.0–1.0."""
    if not population:
        return 0.0
    return sum(1 for v in population if v <= value) / len(population)


def moving_average(values: list[float], window: int = 5) -> float:
    """Mean of the last `window` values."""
    if not values:
        return 0.0
    return sum(values[-window:]) / min(len(values), window)


# ── Definitional booleans ──────────────────────────────────────────────────────
# Use these only for facts that are categorically true/false for everyone.
# If different users could reasonably disagree, use a numeric value instead
# and let them apply their own threshold in constraints().

def flag(metrics: dict, key: str, default: bool = False) -> bool:
    """
    True if metrics[key] is truthy.

    Use for categorical facts: a feature is enabled or it isn't,
    a job completed or it didn't, a connection exists or it doesn't.
    """
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


def equals(metrics: dict, key: str, value, default: bool = False) -> bool:
    """True if metrics[key] == value.  Use for exact categorical matches."""
    val = metrics.get(key)
    return (val == value) if val is not None else default


# ── Compatibility — threshold helpers ─────────────────────────────────────────
# Kept for cases where a boolean perception is definitionally obvious
# (e.g. module_count >= 2 → is_multi_module).  Avoid using these to encode
# performance thresholds — those belong in user constraint files.

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

    Appropriate for definitionally-boolean facts:
        "is_multi_module": threshold(m, "module_count", min=2)

    NOT appropriate for performance judgements like "is_fast" or "has_low_errors"
    — those thresholds differ per user and belong in user constraint files.
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
    """True if lo ≤ metrics[key] ≤ hi.  Same caveats as threshold()."""
    val = metrics.get(key)
    if val is None:
        return default
    return lo <= val <= hi


# ── Standalone runner ──────────────────────────────────────────────────────────

def run_perceptions(compute_fn) -> None:
    """
    Run `compute_fn` as a stdin → stdout perceptions script.

    Reads metrics JSON from stdin, calls compute_fn(metrics, path=...),
    and writes the perceptions JSON document to stdout.

    Call this from your perceptions.py __main__ block so the file works
    both ways: called in-process by `usersim run` (via compute()), and as
    a standalone script in a shell pipe or for manual testing.

    Example
    -------
    def compute(metrics, **_):
        return { "response_ms": metrics["response_ms"] }

    if __name__ == "__main__":
        run_perceptions(compute)

    Usage
    -----
    python3 perceptions.py < metrics.json          # manual test
    cat metrics.json | python3 perceptions.py      # shell pipe
    """
    import json
    import sys

    doc      = json.load(sys.stdin)
    metrics  = doc.get("metrics", {})
    path = doc.get("path", "default")

    result = compute_fn(metrics, path=path)

    # If compute_fn returned just the facts dict, wrap it in the full schema
    if "facts" not in result:
        result = {
            "schema":   "usersim.perceptions.v1",
            "path": path,
            "person":   "all",
            "facts":    result,
        }

    json.dump(result, sys.stdout)
    sys.stdout.write("\n")
