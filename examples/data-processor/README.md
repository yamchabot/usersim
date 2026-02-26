# data-processor example

A complete usersim setup for a simple in-memory data processor.

## What's here

| File | Purpose |
|---|---|
| `processor.py` | The application being tested — sort, search, summarise |
| `instrumentation.py` | Runs the processor and records real wall-clock timing |
| `perceptions.py` | Translates timing into human-meaningful facts |
| `users/developer.py` | Interactive user; needs operations to feel responsive |
| `users/analyst.py` | Runs ad-hoc queries; tolerates latency, needs correctness |
| `users/ops_engineer.py` | Batch jobs; needs the pipeline to finish within SLA |
| `usersim.yaml` | Pipeline config — scenarios, commands, output paths |

## Run it

```bash
usersim run
```

Three scenarios (`small`, `medium`, `large`) × three users. All measurements are real — instrumentation.py calls processor.py and records actual timing.

## Scenarios

| Scenario | Dataset size | Expected experience |
|---|---|---|
| `small`  | 500 records    | Instant for everyone |
| `medium` | 10 000 records | Acceptable for all; fast for ops/analyst |
| `large`  | 100 000 records | Slow for interactive use; fine for batch |

## What to change

- **`processor.py`** — replace with your own application code
- **`instrumentation.py`** — measure the operations your users actually run
- **`perceptions.py`** — tune thresholds to match your users' expectations
- **`users/*.py`** — express what each persona actually needs
