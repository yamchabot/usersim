"""
perceptions.py — reshape search metrics into Z3-ready booleans/integers.

All values are passed through as integers. The sentinel convention: -1 means
the metric was not observed (perceptions that default to -1 will cause
Implies(P.x >= 0, ...) antecedents to be false → vacuous constraints).
"""
import json
import sys


def compute(metrics: dict, path: str = None, **_) -> dict:
    def num(key, default=-1):
        v = metrics.get(key, default)
        return int(v) if v is not None else default

    return {
        # Search quality
        "results_returned":  num("results_returned"),
        "results_relevant":  num("results_relevant"),
        "total_relevant":    num("total_relevant"),
        "corpus_size":       num("corpus_size"),
        "top_k":             num("top_k"),
        # Timing
        "query_time_ms":     num("query_time_ms"),
        "elapsed_ms":        num("elapsed_ms"),
    }


if __name__ == "__main__":
    from usersim.perceptions.library import run_perceptions
    run_perceptions(compute)
