"""
Pipeline runner.

Orchestrates: instrumentation → perceptions → judgement.

All inter-layer communication is JSON on stdout/stdin.
No temp files.  Each layer can be in any language.

Typical shell usage:
    python3 instrumentation.py | python3 perceptions.py | usersim judge --users users/*.py

Or driven by the `usersim run` command:
    python3 instrumentation.py | usersim run --perceptions perceptions.py --users users/*.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from usersim.schema import validate_metrics, validate_perceptions, PERCEPTIONS_SCHEMA


def run_pipeline(
    perceptions_script: "str | Path",
    user_files: list,
    metrics: "dict | None" = None,
    output_path: "str | Path | None" = None,
    scenario: str = "default",
    person: "str | None" = None,
    verbose: bool = False,
) -> dict:
    """
    Run the perceptions → judgement portion of the pipeline.

    Args:
        perceptions_script: path to the perceptions script
        user_files:         list of paths to user Python files
        metrics:            metrics dict (already loaded); if None, reads from stdin
        output_path:        write results JSON here; None → write to stdout
        scenario:           scenario name tag
        person:             evaluate specific person only (None = all)
        verbose:            print debug info to stderr
    """
    from usersim.judgement.engine import run_judgement

    # ── Step 1: get metrics ───────────────────────────────────────────────────
    if metrics is None:
        if verbose:
            print("[usersim] reading metrics from stdin …", file=sys.stderr)
        metrics_doc = json.load(sys.stdin)
    else:
        metrics_doc = metrics

    validate_metrics(metrics_doc)
    if verbose:
        print(f"[usersim] {len(metrics_doc['metrics'])} metrics loaded", file=sys.stderr)

    # ── Step 2: run perceptions script → get perceptions dict ────────────────
    perceptions_doc = _run_perceptions(
        metrics_doc,
        Path(perceptions_script),
        scenario=scenario,
        person=person,
        verbose=verbose,
    )
    validate_perceptions(perceptions_doc)
    if verbose:
        print(f"[usersim] {len(perceptions_doc['facts'])} facts produced", file=sys.stderr)

    # ── Step 3: judgement (in-process, no temp file) ──────────────────────────
    return run_judgement(
        perceptions=perceptions_doc,   # pass dict directly — no file needed
        user_files=user_files,
        output_path=output_path,
    )


def _run_perceptions(
    metrics_doc: dict,
    script: Path,
    scenario: str,
    person: "str | None",
    verbose: bool,
) -> dict:
    """
    Call the perceptions script.

    Protocol:
      stdin  → metrics JSON
      stdout ← perceptions JSON

    If the script is a .py with a compute() function, call it in-process.
    Otherwise spawn a subprocess (works for Node, Ruby, Go binaries, etc.).
    """
    if script.suffix == ".py":
        return _call_python_perceptions(script, metrics_doc, scenario, person, verbose)

    env = {**os.environ, "USERSIM_SCENARIO": scenario, "USERSIM_PERSON": person or ""}
    result = subprocess.run(
        [str(script)],
        input=json.dumps(metrics_doc),
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Perceptions script exited {result.returncode}:\n{result.stderr}"
        )
    if verbose and result.stderr:
        print("[perceptions]", result.stderr, file=sys.stderr)
    return json.loads(result.stdout)


def _call_python_perceptions(
    script: Path,
    metrics_doc: dict,
    scenario: str,
    person: "str | None",
    verbose: bool,
) -> dict:
    """
    Import a Python perceptions.py and call compute(metrics, scenario, person).
    Falls back to subprocess if no compute() function found.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location("_usersim_perceptions", script)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    if hasattr(mod, "compute"):
        result = mod.compute(metrics_doc["metrics"], scenario=scenario, person=person)
        # If compute() returns just the facts dict, wrap it in the full schema
        if isinstance(result, dict) and "facts" not in result:
            result = {
                "schema":   PERCEPTIONS_SCHEMA,
                "scenario": scenario,
                "person":   person or "all",
                "facts":    result,
            }
        return result

    # No compute() — run as script via subprocess (reads stdin, writes stdout)
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
            f"Perceptions script exited {result.returncode}:\n{result.stderr}"
        )
    return json.loads(result.stdout)
