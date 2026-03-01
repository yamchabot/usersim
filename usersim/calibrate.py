"""
usersim calibrate — print actual perception values per path.

Runs instrumentation for each path and feeds the output through perceptions,
printing the resulting dict so you can recalibrate constraint thresholds.

Usage:
    usersim calibrate                    # reads usersim.yaml
    usersim calibrate --config ci.yaml
    usersim calibrate --path normal_run
"""

import json
import os
import sys
from pathlib import Path


def run_calibrate(config: dict, scenario_override: str | None = None) -> int:
    """
    Run instrumentation + perceptions for each path and print perception values.
    Returns 0 on success, 1 on error.
    """
    import subprocess
    import importlib.util

    instr_cmd    = config.get("instrumentation", "")
    perc_path    = config.get("perceptions", "")
    paths    = config.get("paths", ["default"])
    base_dir     = config.get("_base_dir", Path("."))

    if not instr_cmd:
        print("error: no instrumentation command in config", file=sys.stderr)
        return 1
    if not perc_path:
        print("error: no perceptions path in config", file=sys.stderr)
        return 1

    perc_file = Path(perc_path) if Path(perc_path).is_absolute() else base_dir / perc_path
    if not perc_file.exists():
        print(f"error: perceptions file not found: {perc_file}", file=sys.stderr)
        return 1

    spec = importlib.util.spec_from_file_location("_usersim_perc_cal", perc_file)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # Normalise path list
    scenario_names = []
    for s in paths:
        if isinstance(s, dict):
            scenario_names.append(s["name"])
        else:
            scenario_names.append(str(s))

    if scenario_override:
        scenario_names = [scenario_override]

    errors = 0
    for path in scenario_names:
        env = {**os.environ, "USERSIM_PATH": path}
        try:
            r = subprocess.run(
                instr_cmd, shell=True, capture_output=True, text=True,
                env=env, cwd=str(base_dir)
            )
        except Exception as e:
            print(f"\n--- {path}: FAILED (could not run instrumentation: {e}) ---", file=sys.stderr)
            errors += 1
            continue

        if r.returncode != 0 or not r.stdout.strip():
            print(f"\n--- {path}: FAILED (exit {r.returncode}) ---", file=sys.stderr)
            if r.stderr.strip():
                print(r.stderr[:400], file=sys.stderr)
            errors += 1
            continue

        try:
            raw = json.loads(r.stdout)
        except json.JSONDecodeError as e:
            print(f"\n--- {path}: FAILED (bad JSON: {e}) ---", file=sys.stderr)
            errors += 1
            continue

        metrics = raw.get("metrics", raw)

        try:
            perc = mod.compute(metrics, path=path)
        except Exception as e:
            print(f"\n--- {path}: FAILED (perceptions error: {e}) ---", file=sys.stderr)
            errors += 1
            continue

        print(f"\n--- {path} ---")
        for k, v in sorted(perc.items()):
            print(f"  {k}: {v}")

    return 1 if errors else 0
