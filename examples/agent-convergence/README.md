# agent-convergence

Demonstrates an AI agent iteratively fixing a broken implementation guided by
usersim constraint violations.

## What it does

1. Runs `usersim` against `app/search.py` — a deliberately broken search function
2. Collects failing constraints and violation counts
3. Sends the violations + current code to a local Ollama model
4. Applies the model's fix, runs usersim again
5. Repeats until all constraints pass (or `--max-iterations` reached)
6. Prints a convergence table showing violations per iteration

## Prerequisites

- [Ollama](https://ollama.ai) running locally with a code model:
  ```
  ollama pull qwen2.5-coder:14b   # recommended
  ollama pull codestral:22b        # alternative
  ```
- usersim installed: `pip install usersim` (or from repo: `pip install -e .`)

## Run it

```bash
cd examples/agent-convergence

# Default model (qwen2.5-coder:14b)
python3 run_agent.py

# Different model
python3 run_agent.py --model codestral:22b

# Preview the prompt without calling the model
python3 run_agent.py --dry-run

# More iterations
python3 run_agent.py --max-iterations 10
```

## The broken implementation

`app/search.py` has four intentional bugs:

1. **Case sensitivity** — queries are lowercased but corpus items are not checked case-insensitively
2. **top_k ignored** — returns all matches regardless of the `top_k` parameter
3. **No ranking** — returns items in insertion order, not by relevance
4. **elapsed_ms hardcoded** — always returns 0 instead of measuring actual time

## The constraints

`usersim/users/search_quality_user.py` defines what a search quality analyst wants:

- **result_count**: non-empty results, never exceed `top_k` or corpus size
- **precision ≥ 80%**: at least 80% of returned results must be relevant
- **recall ≥ 60%**: must find at least 60% of known relevant items
- **top-k respected**: `results_returned <= top_k`
- **fast enough**: `query_time_ms <= 100ms`
- **elapsed positive**: `elapsed_ms >= 1` when results returned

## Expected convergence

With `qwen2.5-coder:14b`:

| Iteration | Violations | Score |
|-----------|-----------|-------|
| 1 (broken) | 5-8 | ~20% |
| 2 | 2-3 | ~60% |
| 3 | 0 | 100% ✅ |

The key insight: **usersim violations are a GPS signal, not a pass/fail report**.
The agent doesn't need to understand the constraint system — it just needs
to read plain-English violation descriptions and fix the code.
