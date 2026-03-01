"""
instrumentation.py — measures real performance of processor.py.

Scenarios:
  small      —   500 records, normal data
  medium     — 10 000 records, normal data
  large      — 100 000 records, normal data (batch territory)
  empty      —     0 records (edge case: empty input)
  errors     —   500 records, ~10% have null/missing fields
  concurrent —   500 records run sort+search+summary back-to-back 5 times
"""
import json
import os
import random
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from processor import sort_records, search_records, summarise

SCENARIO = os.environ.get("USERSIM_PATH", "small")
random.seed(42)

CATEGORIES = ["alpha", "beta", "gamma", "delta"]


def make_records(n, with_errors=False):
    records = []
    for i in range(n):
        r = {
            "id":       i,
            "name":     f"record_{i:06d}",
            "score":    round(random.uniform(0, 100), 2),
            "category": random.choice(CATEGORIES),
            "active":   random.random() > 0.3,
        }
        if with_errors and random.random() < 0.10:
            # ~10% of records are corrupted
            del r["score"]
        records.append(r)
    return records


SIZES = {
    "small":      500,
    "medium":  10_000,
    "large":  100_000,
    "empty":        0,
    "errors":     500,
    "concurrent":  500,
}

N = SIZES.get(SCENARIO, 500)
with_errors = SCENARIO == "errors"
records = make_records(N, with_errors=with_errors)


def bench(fn, *args, runs=3):
    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        fn(*args)
        times.append((time.perf_counter() - t0) * 1000)
    return round(statistics.mean(times), 2)


# ── Measure operations ────────────────────────────────────────────────────────

if SCENARIO == "concurrent":
    # Run the full pipeline 5 times back-to-back and report worst-case timing
    sort_times, search_times, summary_times = [], [], []
    for _ in range(5):
        sort_times.append(bench(sort_records, records, "score", runs=1))
        search_times.append(bench(search_records, records, "record_0001", runs=1))
        summary_times.append(bench(summarise, records, "score", runs=1))
    sort_ms    = round(max(sort_times), 2)
    search_ms  = round(max(search_times), 2)
    summary_ms = round(max(summary_times), 2)
    repetition_count = 5
else:
    sort_ms    = bench(sort_records, records, "score")   if N > 0 else 0.0
    search_ms  = bench(search_records, records, "record_0001") if N > 0 else 0.0
    summary_ms = bench(summarise, records, "score")      if N > 0 else 0.0
    repetition_count = 1

search_hits = len(search_records(records, "record_0001")) if N > 0 else 0
summary     = summarise(records, "score") if N > 0 else {"count": 0}

# Count records where "score" is missing (corrupted)
error_count  = sum(1 for r in records if "score" not in r)
summary_count = summary.get("count", 0)

print(
    f"[instrumentation] path={SCENARIO} n={N:,} errors={error_count} "
    f"sort={sort_ms}ms search={search_ms}ms summary={summary_ms}ms",
    file=sys.stderr,
)

json.dump(
    {
        "schema":   "usersim.metrics.v1",
        "path": SCENARIO,
        "metrics": {
            "record_count":    N,
            "sort_ms":         sort_ms,
            "search_ms":       search_ms,
            "summary_ms":      summary_ms,
            "total_ms":        round(sort_ms + search_ms + summary_ms, 2),
            "search_hits":     search_hits,
            "error_count":     error_count,
            "summary_count":   summary_count,   # records included in summary
            "repetition_count": repetition_count,
        },
    },
    sys.stdout,
)
