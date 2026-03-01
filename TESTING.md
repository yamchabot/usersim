# Testing

## Install dependencies

```bash
pip install -e ".[dev]"
```

This installs usersim in editable mode plus `pytest` and `z3-solver`.

## Run all tests

```bash
pytest
```

71 tests. Takes ~25 seconds (integration tests run real pipelines).

## Test structure

```
tests/
  test_core.py      — unit tests for the framework internals
  test_examples.py  — end-to-end integration tests
```

### test_core.py — unit tests

Tests the core pipeline components in isolation:
- Perceptions loading and computation
- Judgement engine (Z3 constraint evaluation)
- Named constraints and `_expr_repr` propagation
- Results JSON schema and structure
- CLI subcommands (`run`, `judge`, `report`, `audit`, `calibrate`)
- Runner config loading and path resolution

### test_examples.py — integration tests

Runs `usersim run` end-to-end against each bundled project and the dogfood config.
Verifies the full pipeline: instrumentation → perceptions → judgement → report.

**TestLocalNotesExample** — `examples/local-notes/`
- 5 personas × 7 scenarios
- Checks: clean exit, all checks passed, schema, all scenarios/personas present,
  every result satisfied, every result has constraints, report written and valid

**TestDataProcessorExample** — `examples/data-processor/`
- 3 personas × 3 scenarios
- Same checks as above

**TestDogfood** — `dogfood/` (usersim testing itself)
- 15 personas × 6 scenarios = 90 checks
- Additional checks:
  - Zero vacuous constraints in `full_integration` scenario
  - Effective test count ≥ 50,000 (regression guard on constraint coverage)

## Run a specific test file or class

```bash
pytest tests/test_core.py
pytest tests/test_examples.py::TestDogfood
pytest tests/test_examples.py::TestDogfood::test_zero_vacuous_constraints
```

## Verbose output

```bash
pytest -v
```

## usersim's own self-check

```bash
cd dogfood && usersim audit
```

Runs the dogfood pipeline and analyses the results for constraint health:
vacuous constraints, always-passing constraints, dead perceptions, constraint
count per persona, and variable density. Exits 1 if vacuous constraints are found.

## CI

```yaml
- run: pip install -e ".[dev]"
- run: pytest
```

To also run the self-check:

```yaml
- run: pip install -e ".[dev]"
- run: pytest
- run: cd dogfood && usersim audit
```
