#!/usr/bin/env python3
"""
run_agent.py — agent convergence demo.

Demonstrates an AI agent iteratively fixing search.py guided by usersim
constraint violations. After each attempt the agent receives:
  - Which constraints failed
  - The current violation count
  - The current implementation

It continues until all constraints pass or max_iterations is reached.

Usage:
    python3 run_agent.py                          # default: qwen2.5-coder:14b
    python3 run_agent.py --model codestral:22b
    python3 run_agent.py --max-iterations 5
    python3 run_agent.py --dry-run               # show prompt without calling model
"""
import argparse
import json
import shutil
import subprocess
import sys
import textwrap
import time
from pathlib import Path

HERE     = Path(__file__).parent
APP_FILE = HERE / "app" / "search.py"
USERSIM  = shutil.which("usersim") or str(
    next((p for p in [
        Path(sys.executable).parent / "usersim",
        Path.home() / ".local" / "bin" / "usersim",
        Path("/workspace/.local/bin/usersim"),
    ] if p.exists()), "usersim")
)

OLLAMA_HOST = "http://host.docker.internal:11434"
DEFAULT_MODEL = "qwen2.5-coder:14b"

SYSTEM_PROMPT = """\
You are a Python code fixer. You receive a broken Python implementation and a
list of failing constraints describing what's wrong. Your job is to return a
corrected version of the file that satisfies all the constraints.

Rules:
- Return ONLY the complete corrected Python file (no markdown, no explanation)
- Do not change the function signature: def search(query, corpus, top_k=10)
- Do not add external dependencies
- The function must return a dict with keys: results, total_found, elapsed_ms
"""

FIXING_PROMPT = """\
The following Python file has {violation_count} failing constraints:

=== FAILING CONSTRAINTS ===
{violations}

=== CURRENT FILE ({filename}) ===
{code}

=== WHAT THE CONSTRAINTS MEAN ===
{constraint_descriptions}

Return the complete corrected file with all constraints passing.
"""

CONSTRAINT_DESCRIPTIONS = {
    "search/non-empty-result-set":          "Must return at least 1 result when corpus is non-empty",
    "search/results-never-exceed-top-k":    "Number of results must not exceed the top_k parameter",
    "search/results-never-exceed-corpus":   "Can't return more results than the corpus has items",
    "search/results-under-ceiling":         "Hard ceiling of 100 results",
    "search/relevant-never-exceed-returned":"Can't have more relevant results than total results",
    "search/precision-above-floor":         "At least 80% of returned results must be relevant (precise)",
    "search/recall-above-floor":            "Must find at least 60% of known relevant items",
    "search/total-relevant-non-negative":   "The total_relevant count must be >= 0",
    "search/total-relevant-lte-corpus":     "Can't have more relevant items than corpus size",
    "search/precision-recall-f1-floor":     "Combined precision and recall must exceed F1=0.60 floor",
    "search/top-k-respected":              "results_returned must be <= top_k (hard limit)",
    "search/fast-enough":                  "Query must complete in under 100ms",
    "search/elapsed-positive":             "elapsed_ms must be >= 1 when results are returned",
}


def _run_usersim() -> dict:
    """Run usersim and return parsed results dict."""
    result = subprocess.run(
        [USERSIM, "run", "--config", str(HERE / "usersim.yaml")],
        cwd=str(HERE),
        capture_output=True,
        text=True,
    )
    results_file = HERE / "usersim" / "results.json"
    if results_file.exists():
        return json.loads(results_file.read_text())
    return {}


def _count_violations(results: dict) -> tuple[int, list[str]]:
    """Return (total_violations, [violation_label, ...])."""
    violations = []
    for r in results.get("results", []):
        violations.extend(r.get("violations", []))
    # Deduplicate, preserve order
    seen = set()
    unique = []
    for v in violations:
        if v not in seen:
            seen.add(v)
            unique.append(v)
    return len(violations), unique


def _ask_model(model: str, violations: list[str], code: str) -> str:
    """Send the fixing prompt to Ollama and return the raw response text."""
    violation_list = "\n".join(f"  - {v}" for v in violations)
    descriptions = "\n".join(
        f"  {v}: {CONSTRAINT_DESCRIPTIONS.get(v, '(see constraint definition)')}"
        for v in violations
        if v in CONSTRAINT_DESCRIPTIONS
    )

    prompt = FIXING_PROMPT.format(
        violation_count=len(violations),
        violations=violation_list,
        filename=APP_FILE.name,
        code=code,
        constraint_descriptions=descriptions or "(see constraints in usersim/users/)",
    )

    payload = {
        "model": model,
        "system": SYSTEM_PROMPT,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 2048},
    }

    import urllib.request
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/generate",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())["response"]


def _extract_code(response: str) -> str:
    """Extract Python code from model response, stripping markdown fences."""
    # Strip ```python ... ``` blocks
    if "```" in response:
        parts = response.split("```")
        for i, part in enumerate(parts):
            if i % 2 == 1:  # inside a fence
                code = part.lstrip("python").lstrip("\n")
                if "def search" in code or "import" in code:
                    return code.strip()
    # No fences — assume raw code
    if "def search" in response:
        return response.strip()
    return response.strip()


def main():
    parser = argparse.ArgumentParser(description="Agent convergence demo")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"Ollama model to use (default: {DEFAULT_MODEL})")
    parser.add_argument("--max-iterations", type=int, default=8,
                        help="Max fix attempts (default: 8)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print prompt without calling model")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  usersim agent-convergence demo")
    print(f"  model: {args.model}")
    print(f"  max iterations: {args.max_iterations}")
    print(f"{'='*60}\n")

    # Save original implementation for restore on failure
    original_code = APP_FILE.read_text()
    history = []

    for iteration in range(1, args.max_iterations + 1):
        print(f"── Iteration {iteration} ──────────────────────────────────────")

        # Run usersim
        print("  Running usersim...", end="", flush=True)
        t0 = time.perf_counter()
        results = _run_usersim()
        elapsed = time.perf_counter() - t0
        print(f" done ({elapsed:.1f}s)")

        total_violations, unique_violations = _count_violations(results)
        summary = results.get("summary", {})
        satisfied = summary.get("satisfied", 0)
        total = summary.get("total", 0)
        score = summary.get("score", 0.0)

        print(f"  Score: {satisfied}/{total} ({score:.0%}) — {total_violations} violations")
        history.append({
            "iteration": iteration,
            "violations": total_violations,
            "score": score,
        })

        if total_violations == 0:
            print(f"\n✅ ALL CONSTRAINTS PASSING after {iteration - 1} fix(es)!\n")
            break

        for v in unique_violations:
            desc = CONSTRAINT_DESCRIPTIONS.get(v, "")
            print(f"    ❌ {v}" + (f" — {desc}" for _ in [1]).__next__() if desc else f"    ❌ {v}")

        if iteration == args.max_iterations:
            print(f"\n⚠️  Reached max iterations ({args.max_iterations}). Stopping.")
            break

        # Ask model to fix it
        current_code = APP_FILE.read_text()
        print(f"  Asking {args.model} to fix {len(unique_violations)} violation(s)...", end="", flush=True)

        if args.dry_run:
            violation_list = "\n".join(f"  - {v}" for v in unique_violations)
            descriptions = "\n".join(
                f"  {v}: {CONSTRAINT_DESCRIPTIONS.get(v, '')}"
                for v in unique_violations if v in CONSTRAINT_DESCRIPTIONS
            )
            print(f"\n\n--- DRY RUN PROMPT ---")
            print(FIXING_PROMPT.format(
                violation_count=len(unique_violations),
                violations=violation_list,
                filename=APP_FILE.name,
                code=current_code,
                constraint_descriptions=descriptions,
            ))
            print("--- END PROMPT ---\n")
            break

        try:
            t0 = time.perf_counter()
            response = _ask_model(args.model, unique_violations, current_code)
            elapsed = time.perf_counter() - t0
            print(f" done ({elapsed:.1f}s)")

            fixed_code = _extract_code(response)
            if len(fixed_code) < 50:
                print(f"  ⚠️  Model returned very short response, skipping")
                continue

            APP_FILE.write_text(fixed_code)
            print(f"  ✏️  Updated {APP_FILE.name} ({len(fixed_code)} chars)")

        except Exception as e:
            print(f"\n  ⚠️  Model call failed: {e}")
            if iteration == 1:
                print("  Restoring original implementation.")
                APP_FILE.write_text(original_code)
            break

    # Summary
    print(f"\n{'='*60}")
    print(f"  Convergence summary")
    print(f"{'='*60}")
    print(f"  {'Iteration':<12} {'Violations':<12} {'Score'}")
    print(f"  {'-'*36}")
    for h in history:
        arrow = " ✅" if h["violations"] == 0 else ""
        print(f"  {h['iteration']:<12} {h['violations']:<12} {h['score']:.0%}{arrow}")

    final_violations = history[-1]["violations"] if history else "?"
    if final_violations == 0:
        print(f"\n  Result: CONVERGED 🎯")
    else:
        print(f"\n  Result: {final_violations} violations remaining after {len(history)} iteration(s)")
    print()


if __name__ == "__main__":
    main()
