"""
instrumentation.py — measures real performance of processor.py.

Generates test data matching the current scenario, runs each operation
several times, and reports real timing measurements to stdout.

USERSIM_SCENARIO controls dataset size:
  small   — 500 records   (interactive use, should feel instant)
  medium  — 10 000 records (analyst workload, seconds are acceptable)
  large   — 100 000 records (batch job, must finish within a time budget)
"""
import json
import os
import random
import statistics
import sys
import time

# Add the project root to sys.path so processor.py is importable
# whether this script is run by usersim (via PYTHONPATH) or directly.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from processor import sort_records, search_records, summarise

# ── Dataset sizes per scenario ────────────────────────────────────────────────

SCENARIO = os.environ.get("USERSIM_SCENARIO", "small")

SIZES = {
    "small":  500,
    "medium": 10_000,
    "large":  100_000,
}

N = SIZES.get(SCENARIO, SIZES["small"])
random.seed(42)   # reproducible timing

# ── Generate test records ─────────────────────────────────────────────────────

CATEGORIES = ["alpha", "beta", "gamma", "delta"]

records = [
    {
        "id":       i,
        "name":     f"record_{i:06d}",
        "score":    round(random.uniform(0, 100), 2),
        "category": random.choice(CATEGORIES),
        "active":   random.random() > 0.3,
    }
    for i in range(N)
]


def bench(fn, *args, runs: int = 3) -> float:
    """Return mean wall-clock time in ms over `runs` calls."""
    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        fn(*args)
        times.append((time.perf_counter() - t0) * 1000)
    return round(statistics.mean(times), 2)


# ── Measure each operation ────────────────────────────────────────────────────

sort_ms    = bench(sort_records, records, "score")
search_ms  = bench(search_records, records, "record_0001")
summary_ms = bench(summarise, records, "score")

# Search returns the actual results so we can report hit count
search_hits = len(search_records(records, "record_0001"))

print(
    f"[instrumentation] scenario={SCENARIO} n={N:,} "
    f"sort={sort_ms}ms search={search_ms}ms summary={summary_ms}ms",
    file=sys.stderr,
)

# ── Output metrics JSON to stdout ─────────────────────────────────────────────

json.dump(
    {
        "schema":   "usersim.metrics.v1",
        "scenario": SCENARIO,
        "metrics": {
            "record_count": N,
            "sort_ms":      sort_ms,
            "search_ms":    search_ms,
            "summary_ms":   summary_ms,
            "total_ms":     round(sort_ms + search_ms + summary_ms, 2),
            "search_hits":  search_hits,
            "error_count":  0,   # extend this if processor can raise errors
        },
    },
    sys.stdout,
)
