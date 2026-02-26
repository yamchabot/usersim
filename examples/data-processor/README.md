# data-processor example

A complete usersim setup for a simple in-memory data processor.

## Layout

```
data-processor/
├── processor.py        ← the application being tested
├── usersim.yaml        ← pipeline config (run usersim run from here)
└── usersim/            ← all simulation files in one place
    ├── instrumentation.py
    ├── perceptions.py
    └── users.py        ← all three personas in one file
```

## What's here

| File | Purpose |
|---|---|
| `processor.py` | The application — sort, search, summarise records |
| `usersim/instrumentation.py` | Runs the processor and records real wall-clock timing |
| `usersim/perceptions.py` | Translates timing into numeric domain observations |
| `usersim/users.py` | All personas: Developer, Analyst, OpsEngineer |
| `usersim.yaml` | Pipeline config — scenarios, commands, output paths |

## Run it

```bash
usersim run
```

Three scenarios (`small`, `medium`, `large`) × three users. All measurements are real — instrumentation.py calls processor.py and records actual timing.

## Test the pipeline manually

```bash
python3 usersim/instrumentation.py | python3 usersim/perceptions.py | python3 -m json.tool
```

## Scenarios

| Scenario | Dataset size | Expected experience |
|---|---|---|
| `small`  | 500 records     | Instant for everyone |
| `medium` | 10 000 records  | Acceptable for all |
| `large`  | 100 000 records | Batch territory; ops and analyst are fine |

## What to change

- **`processor.py`** — replace with your own application code
- **`usersim/instrumentation.py`** — measure the operations your users actually run
- **`usersim/perceptions.py`** — extract numeric domain observations
- **`usersim/users/*.py`** — express what each persona actually needs with Z3 constraints
