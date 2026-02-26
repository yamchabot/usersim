"""
Pipeline runner.

Orchestrates: instrumentation → perceptions script → judgement engine.

Each layer communicates via JSON written to files (or stdout/stdin).
The layer boundary is just a JSON file — so each layer can be in any language.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from usersim.schema import validate_metrics, validate_perceptions, PERCEPTIONS_SCHEMA


def run_pipeline(
    metrics_path: str | Path,
    perceptions_script: str | Path,
    user_files: list[str | Path],
    output_path: str | Path | None = None,
    scenario: str = "default",
    person: str | None = None,
    verbose: bool = False,
) -> dict:
    """
    Run the full pipeline.

    1. Load & validate metrics.json
    2. Call perceptions script (any language) with metrics on stdin
    3. Collect perceptions.json from stdout
    4. Run Z3 judgement
    5. Return results dict
    """
    from usersim.judgement.engine import run_judgement

    # ── Step 1: load metrics ──────────────────────────────────────────────────
    metrics_path = Path(metrics_path)
    with open(metrics_path) as f:
        metrics_doc = json.load(f)
    validate_metrics(metrics_doc)
    if verbose:
        print(f"[usersim] Loaded {len(metrics_doc['metrics'])} metrics from {metrics_path}")

    # ── Step 2: run perceptions script ────────────────────────────────────────
    perceptions_script = Path(perceptions_script)
    perceptions_doc    = _run_perceptions(
        metrics_doc, perceptions_script, scenario=scenario, person=person, verbose=verbose
    )
    validate_perceptions(perceptions_doc)
    if verbose:
        print(f"[usersim] {len(perceptions_doc['facts'])} facts produced")

    # Write perceptions to a temp file so judgement can read it
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as tf:
        json.dump(perceptions_doc, tf)
        perc_path = tf.name

    # ── Step 3: judgement ─────────────────────────────────────────────────────
    results = run_judgement(
        perceptions_path=perc_path,
        user_files=user_files,
        output_path=output_path,
    )
    Path(perc_path).unlink(missing_ok=True)

    return results


def _run_perceptions(
    metrics_doc: dict,
    script: Path,
    scenario: str,
    person: str | None,
    verbose: bool,
) -> dict:
    """
    Call the perceptions script.

    Protocol:
      - stdin:  metrics.json content
      - stdout: perceptions.json content (or each person's perceptions as newline-delimited JSON)
      - env:    USERSIM_SCENARIO, USERSIM_PERSON

    Alternatively, if the script is a .py file, import and call it directly
    for speed (avoids a subprocess for Python perceptions).
    """
    metrics_json = json.dumps(metrics_doc)

    if script.suffix == ".py":
        return _call_python_perceptions(script, metrics_doc, scenario, person, verbose)

    # Generic subprocess path (works for Node, Ruby, Go, Rust binaries, etc.)
    import os
    env = {**os.environ, "USERSIM_SCENARIO": scenario, "USERSIM_PERSON": person or ""}
    result = subprocess.run(
        [str(script)],
        input=metrics_json,
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Perceptions script exited with code {result.returncode}:\n{result.stderr}"
        )
    if verbose and result.stderr:
        print("[perceptions]", result.stderr, file=sys.stderr)

    return json.loads(result.stdout)


def _call_python_perceptions(
    script: Path,
    metrics_doc: dict,
    scenario: str,
    person: str | None,
    verbose: bool,
) -> dict:
    """
    Import a Python perceptions.py and call its `compute(metrics, scenario, person)` function.
    Falls back to subprocess if no `compute` function is found.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location("_usersim_perceptions", script)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    if hasattr(mod, "compute"):
        result = mod.compute(metrics_doc["metrics"], scenario=scenario, person=person)
        # If compute() returns just the facts dict, wrap it
        if isinstance(result, dict) and "facts" not in result:
            result = {
                "schema":   PERCEPTIONS_SCHEMA,
                "scenario": scenario,
                "person":   person or "all",
                "facts":    result,
            }
        return result

    # No compute() function — try running as script via subprocess
    import os, sys
    env = {**os.environ, "USERSIM_SCENARIO": scenario, "USERSIM_PERSON": person or ""}
    result = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(metrics_doc),
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Perceptions script exited with code {result.returncode}:\n{result.stderr}"
        )
    return json.loads(result.stdout)
