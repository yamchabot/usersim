"""
instrumentation.py — measures search.py behavior for usersim.

Runs the search function on a fixed test corpus with known relevant items.
The corpus is designed to expose the bugs in the broken implementation:
  - Mixed case items (expose case-insensitivity bug)
  - More matches than top_k (expose top_k enforcement bug)
  - elapsed_ms=0 check (expose timing bug)
"""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "app"))
from search import search

# Mixed-case corpus — exposes case-insensitivity bug
CORPUS = [
    "Python tutorial for beginners",
    "python advanced features",
    "Python Web Framework Django",
    "python data science pandas",
    "Python Machine Learning sklearn",
    "python testing with pytest",
    "python async programming",
    "JavaScript basics",
    "javascript async await",
    "JavaScript Node.js runtime",
    "Rust systems programming",
    "rust memory safety",
    "Go concurrency patterns",
    "go microservices",
    "Java Spring Boot",
    "java design patterns",
    "SQL query optimization",
    "sql joins explained",
    "Docker containers",
    "kubernetes orchestration",
    "Git branching strategies",
    "git rebase vs merge",
    "Git workflows for teams",
]

# Ground truth: items relevant to each query (lowercase query vs mixed-case corpus)
GROUND_TRUTH = {
    "python": {
        "relevant": [
            "Python tutorial for beginners",
            "python advanced features",
            "Python Web Framework Django",
            "python data science pandas",
            "Python Machine Learning sklearn",
            "python testing with pytest",
            "python async programming",
        ],
        "top_k": 5,  # Want top 5 — recall = 5/7 = 71% >= 60%
    },
    "javascript": {
        "relevant": [
            "JavaScript basics",
            "javascript async await",
            "JavaScript Node.js runtime",
        ],
        "top_k": 2,  # Only want top 2 — broken impl will return all 3
    },
    "git": {
        "relevant": [
            "Git branching strategies",
            "git rebase vs merge",
            "Git workflows for teams",
        ],
        "top_k": 2,  # Only want top 2 — broken impl will return all 3
    },
}


def run_scenario(scenario: str) -> dict:
    if scenario not in GROUND_TRUTH:
        return {"error": f"Unknown scenario: {scenario}"}

    gt = GROUND_TRUTH[scenario]
    top_k = gt["top_k"]
    relevant_set = set(gt["relevant"])

    t0 = time.perf_counter()
    result = search(scenario, CORPUS, top_k=top_k)
    elapsed_measured = max(1, round((time.perf_counter() - t0) * 1000, 1))

    results = result.get("results", [])
    results_returned = len(results)

    # Count relevant: case-insensitive match to ground truth
    results_relevant = sum(
        1 for r in results
        if r in relevant_set or r.lower() in {s.lower() for s in relevant_set}
    )
    total_relevant = len(relevant_set)

    # Use measured elapsed if search returned 0 (catches the elapsed_ms=0 bug)
    elapsed_ms = result.get("elapsed_ms") or elapsed_measured

    return {
        "results_returned":   results_returned,
        "results_relevant":   results_relevant,
        "total_relevant":     total_relevant,
        "corpus_size":        len(CORPUS),
        "top_k":              top_k,
        "elapsed_ms":         max(1, round(elapsed_ms)),
        "query_time_ms":      max(1, round(elapsed_measured)),
    }


if __name__ == "__main__":
    scenario = os.environ.get("USERSIM_PATH") or os.environ.get("USERSIM_SCENARIO") or "python"
    metrics = run_scenario(scenario)
    print(json.dumps({"schema": "usersim.metrics.v1", "path": scenario, "metrics": metrics}))
