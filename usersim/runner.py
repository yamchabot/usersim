"""
Pipeline runner.

Two modes:

1. Config-driven (recommended):
       usersim run                    # reads usersim.yaml
       usersim run --config ci.yaml   # explicit config
   usersim reads the config, runs instrumentation → perceptions → judgement
   for each declared path, then outputs results.  No shell piping needed.

2. Programmatic (for library use or advanced scripting):
       run_pipeline(perceptions_script, user_files, metrics=<dict>)

Config file schema (usersim.yaml):

    version: 1
    instrumentation: "node instrumentation.js"
    perceptions: "python3 perceptions.py"
    users:
      - users/*.py
    paths:
      - default
      # or with descriptions (shown in HTML report when clicking a path ball):
      # - name: baseline
      #   description: "Fresh install, no existing data"
      # - name: offline
      #   description: "Network unavailable throughout session"
    output:
      results: results.json
      report:  report.html
"""
from __future__ import annotations

import glob
import json
import os
import subprocess
import sys
from pathlib import Path

from usersim.schema import validate_metrics, validate_perceptions, PERCEPTIONS_SCHEMA


# ── Config loading ─────────────────────────────────────────────────────────────

def load_config(path: "str | Path | None" = None) -> dict:
    """
    Load and normalise a usersim.yaml config file.

    Searches the current directory by default.  Raises FileNotFoundError
    if not found.  Returns a normalised dict with resolved glob patterns.
    """
    import yaml

    candidates = [path] if path else ["usersim.yaml", ".usersim.yaml", "usersim.yml"]
    config_path = None
    for c in candidates:
        if Path(c).exists():
            config_path = Path(c)
            break

    if config_path is None:
        searched = ", ".join(str(c) for c in candidates)
        raise FileNotFoundError(
            f"No usersim config found.  Searched: {searched}\n"
            f"Run `usersim init` to create one."
        )

    with open(config_path) as f:
        raw = yaml.safe_load(f)

    return _normalise_config(raw, config_path.parent)


def _normalise_config(raw: dict, base_dir: Path) -> dict:
    """Resolve globs, apply defaults, validate required fields."""
    cfg = dict(raw)

    # Required: how to run each stage
    for key in ("instrumentation", "perceptions"):
        if key not in cfg:
            raise ValueError(f"Config is missing required key: '{key}'")

    # Users: expand globs relative to config file location
    raw_users = cfg.get("users", [])
    if isinstance(raw_users, str):
        raw_users = [raw_users]
    user_files = []
    for pattern in raw_users:
        matches = sorted(glob.glob(str(base_dir / pattern)))
        if not matches:
            # Try as literal path
            p = base_dir / pattern
            if p.exists():
                matches = [str(p)]
        user_files.extend(matches)
    if not user_files:
        raise ValueError("No user files found.  Check 'users:' patterns in config.")
    cfg["_user_files"] = user_files

    # Scenarios: list of names (strings) or objects with name + description
    raw_scenarios = cfg.get("paths", ["default"])
    if isinstance(raw_scenarios, str):
        raw_scenarios = [raw_scenarios]
    cfg["_scenarios"] = [
        s if isinstance(s, str) else s.get("name", str(s))
        for s in raw_scenarios
    ]
    # Optional descriptions keyed by path name
    cfg["_scenario_descriptions"] = {
        s["name"]: s.get("description", "")
        for s in raw_scenarios
        if isinstance(s, dict) and "name" in s and s.get("description")
    }
    # Optional tags keyed by path name (default: all tags / untagged)
    cfg["_scenario_tags"] = {
        s["name"]: s.get("tags", [])
        for s in raw_scenarios
        if isinstance(s, dict) and "name" in s
    }

    cfg["_base_dir"] = base_dir
    return cfg


# ── Config-driven pipeline ─────────────────────────────────────────────────────

def _resolve_output_path(path: "str | Path | None", base_dir: Path) -> "str | None":
    """Resolve an output path relative to the config's base directory.

    Absolute paths and None are returned as-is.  Relative paths (e.g. from
    the yaml ``output:`` block) are joined against base_dir so that
    ``usersim run`` works regardless of the working directory.
    """
    if not path:
        return None
    p = Path(path)
    if p.is_absolute():
        return str(p)
    return str(base_dir / p)


def run_from_config(
    config: "dict | str | Path | None" = None,
    scenario_override: "str | None" = None,
    output_path: "str | Path | None" = None,
    verbose: bool = False,
    tags: "list[str] | None" = None,
) -> dict:
    """
    Run the full pipeline as declared in a usersim.yaml config file.

    - Runs instrumentation once per path (USERSIM_SCENARIO env var set)
    - Pipes metrics → perceptions → judgement for each path
    - Returns a single results dict or a matrix dict (multiple paths)

    Args:
        config:            path to config file, or already-loaded dict, or None (auto-discover)
        scenario_override: run only this path (ignores config paths list)
        output_path:       write results JSON here; None → stdout
        verbose:           print stage info to stderr
        tags:              if provided, only run paths whose tags overlap with this list;
                           untagged paths are included unless tags is non-empty
    """
    from usersim.judgement.engine import _write_output

    if not isinstance(config, dict):
        cfg = load_config(config)
    else:
        cfg = config

    base_dir   = cfg["_base_dir"]
    user_files = cfg["_user_files"]
    paths  = [scenario_override] if scenario_override else cfg["_scenarios"]

    # Tags that never run unless explicitly requested
    _OPT_IN_TAGS = {"expensive"}

    # Filter paths by tag
    if not scenario_override:
        scenario_tags = cfg.get("_scenario_tags", {})
        tag_set = set(tags) if tags else set()

        def _should_run(s):
            s_tags = set(scenario_tags.get(s, []))
            opt_in = s_tags & _OPT_IN_TAGS
            if opt_in:
                # Opt-in tags: only run when explicitly requested
                return bool(opt_in & tag_set)
            if tag_set:
                # Normal tag filter: untagged paths always pass
                return not s_tags or bool(s_tags & tag_set)
            return True

        paths = [s for s in paths if _should_run(s)]
        if verbose and (tags or any(
            _OPT_IN_TAGS & set(scenario_tags.get(s, []))
            for s in cfg["_scenarios"]
        )):
            print(f"[usersim] tag filter {tags or []!r}: running {len(paths)} path(s)", file=sys.stderr)

    instr_cmd = cfg["instrumentation"]
    perc_cmd  = cfg["perceptions"]
    out_cfg   = cfg.get("output", {})

    all_results = []

    for path in paths:
        if verbose:
            print(f"[usersim] path: {path}", file=sys.stderr)

        try:
            # Step 1: run instrumentation
            metrics_doc = _run_command(instr_cmd, stdin_data=None, path=path,
                                       base_dir=base_dir, label="instrumentation", verbose=verbose)
            validate_metrics(metrics_doc)

            # Step 2: run perceptions
            perc_doc = _run_perceptions_cmd(perc_cmd, metrics_doc, path=path,
                                            base_dir=base_dir, verbose=verbose)
            validate_perceptions(perc_doc)

            if verbose:
                print(f"[usersim]   {len(perc_doc['facts'])} facts → judgement", file=sys.stderr)

            # Step 3: judgement (in-process, no output yet — collect all first)
            from usersim.judgement.engine import _evaluate
            result = _evaluate(perc_doc, user_files)

        except (RuntimeError, ValueError) as exc:
            # Instrumentation or perceptions failed — record error result and continue
            print(f"[usersim] path {path!r} error: {exc}", file=sys.stderr)
            result = {
                "results": [],
                "error": str(exc),
                "path": path,
            }

        # Inject path description (if declared in config) into each result entry
        sc_desc = cfg.get("_scenario_descriptions", {}).get(path, "")
        if sc_desc:
            for r in result.get("results", []):
                r["description"] = sc_desc

        all_results.append((path, result))

    # ── Assemble final output (always matrix format) ──────────────────────────
    if False:
        pass  # placeholder — single-path fast path removed to keep schema consistent
    if True:
        # Matrix: flatten all path results into one doc
        flat = []
        for path, result in all_results:
            for r in result["results"]:
                r["path"] = path
                flat.append(r)
        satisfied = sum(1 for r in flat if r["satisfied"])

        # ── Effective test count ────────────────────────────────────────────
        # Each constraint with k distinct variables is simultaneously verified
        # over all value combinations (domain size 4 per variable).
        # effective_tests = sum(4^k) across all constraint evaluations.
        import re as _re_eff
        _Z3K = {"If","then","And","Or","Not","Implies","True","False",
                "true","false","and","or","not"}
        _VRE = _re_eff.compile(r'\b([a-z][a-z0-9_]*)\b')
        def _eff(expr: str) -> int:
            k = len({m for m in _VRE.findall(expr) if m not in _Z3K and len(m) > 2})
            return 4 ** min(max(k, 1), 8)

        raw_evals = sum(len(r.get("constraints", [])) for r in flat)
        effective_tests = sum(
            _eff(c.get("expr") or "")
            for r in flat
            for c in r.get("constraints", [])
            if isinstance(c, dict)
        )

        # ── Constraint violation frequency ─────────────────────────────────
        # For each named constraint: how many times did it fire (antecedent
        # was true) and how many times did it fail? Used to identify which
        # constraints are actively steering vs. never exercised.
        freq: dict[str, dict] = {}
        for r in flat:
            for c in r.get("constraints", []):
                if not isinstance(c, dict):
                    continue
                label = c.get("label") or c.get("expr") or "unnamed"
                if label not in freq:
                    freq[label] = {"fired": 0, "failed": 0, "total": 0}
                freq[label]["total"] += 1
                if c.get("antecedent_fired", True):
                    freq[label]["fired"] += 1
                if not c.get("passed", True):
                    freq[label]["failed"] += 1

        output = {
            "schema":  "usersim.matrix.v1",
            "results": flat,
            "summary": {
                "total":            len(flat),
                "satisfied":        satisfied,
                "score":            round(satisfied / max(len(flat), 1), 4),
                "constraint_evals": raw_evals,
                "effective_tests":  effective_tests,
                "constraint_freq":  freq,
            },
        }
        raw_out = output_path or out_cfg.get("results")
        eff_output_path = _resolve_output_path(raw_out, base_dir)
        _write_output(output, eff_output_path)

    # ── HTML report ────────────────────────────────────────────────────────────
    report_path_raw = out_cfg.get("report")
    report_path     = _resolve_output_path(report_path_raw, base_dir) if report_path_raw else None
    if report_path:
        try:
            from usersim.report.html import generate_report
            generate_report(output, report_path)
            if verbose:
                print(f"[usersim] report: {report_path}", file=sys.stderr)
        except Exception as e:
            print(f"[usersim] report skipped: {e}", file=sys.stderr)

    return output


# ── Stage runners ──────────────────────────────────────────────────────────────

def _run_command(
    cmd: str,
    stdin_data: "str | None",
    path: str,
    base_dir: Path,
    label: str,
    verbose: bool,
) -> dict:
    """
    Run a shell command, passing stdin_data (if any) on stdin.
    Expects JSON on stdout.  Raises on non-zero exit.
    """
    # Add base_dir to PYTHONPATH so subprocess scripts can import app code
    # that lives in the project root (e.g. instrumentation.py imports processor.py)
    existing_pythonpath = os.environ.get("PYTHONPATH", "")
    pythonpath = str(base_dir) if not existing_pythonpath else f"{base_dir}:{existing_pythonpath}"

    env = {
        **os.environ,
        "USERSIM_PATH": path,
        "USERSIM_SCENARIO": path,  # deprecated alias — kept for backward compat
        "PYTHONPATH": pythonpath,
    }
    result = subprocess.run(
        cmd,
        shell=True,
        input=stdin_data,
        capture_output=True,
        text=True,
        cwd=str(base_dir),
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"{label} command failed (exit {result.returncode}):\n"
            f"  cmd: {cmd}\n"
            f"  stderr: {result.stderr.strip()}"
        )
    if verbose and result.stderr.strip():
        print(f"[{label}] {result.stderr.strip()}", file=sys.stderr)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"{label} command produced invalid JSON:\n"
            f"  cmd: {cmd}\n"
            f"  output: {result.stdout[:200]!r}\n"
            f"  error: {e}"
        )


def _run_perceptions_cmd(
    cmd: str,
    metrics_doc: dict,
    path: str,
    base_dir: Path,
    verbose: bool,
) -> dict:
    """
    Run the perceptions stage.

    If cmd is a path to a .py file with a compute() function, call it
    in-process (no subprocess overhead, better tracebacks).
    Otherwise spawn a subprocess and pipe metrics JSON on stdin.
    """
    script_path = base_dir / cmd.strip().split()[-1]  # last token = script file

    if script_path.suffix == ".py" and script_path.exists():
        return _call_python_perceptions(script_path, metrics_doc, path, verbose)

    # Generic subprocess: pipe metrics JSON to stdin
    metrics_json = json.dumps(metrics_doc)
    return _run_command(cmd, stdin_data=metrics_json, path=path,
                        base_dir=base_dir, label="perceptions", verbose=verbose)


def _call_python_perceptions(
    script: Path,
    metrics_doc: dict,
    path: str,
    verbose: bool,
) -> dict:
    """Import a Python perceptions.py and call compute(metrics, path=...)."""
    import importlib.util

    import sys as _sys
    # Add the script's directory to sys.path so it can import sibling modules
    # (e.g. z3_compat, users) without being a package.
    script_dir = str(script.parent)
    if script_dir not in _sys.path:
        _sys.path.insert(0, script_dir)

    spec = importlib.util.spec_from_file_location("_usersim_perceptions", script)
    mod  = importlib.util.module_from_spec(spec)
    # Register in sys.modules before exec so @dataclass and type annotations
    # that look up cls.__module__ can find their own module namespace.
    _sys.modules["_usersim_perceptions"] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        del _sys.modules["_usersim_perceptions"]
        raise

    if not hasattr(mod, "compute"):
        raise RuntimeError(
            f"Perceptions file {script} has no compute() function.\n"
            "Either add a compute(metrics, **kwargs) function or use a "
            "command that reads stdin and writes JSON to stdout."
        )

    result = mod.compute(metrics_doc["metrics"], path=path)
    if isinstance(result, dict) and "facts" not in result:
        result = {
            "schema":   PERCEPTIONS_SCHEMA,
            "path": path,
            "person":   "all",
            "facts":    result,
        }
    return result


# ── Programmatic pipeline (for library use) ────────────────────────────────────

def run_pipeline(
    perceptions_script: "str | Path",
    user_files: list,
    metrics: "dict | None" = None,
    output_path: "str | Path | None" = None,
    path: str = "default",
    person: "str | None" = None,
    verbose: bool = False,
) -> dict:
    """
    Run perceptions → judgement programmatically (no config file).

    Reads metrics from stdin if metrics=None.  Useful for library use
    or advanced scripting where the caller manages instrumentation.
    """
    from usersim.judgement.engine import run_judgement

    if metrics is None:
        if verbose:
            print("[usersim] reading metrics from stdin …", file=sys.stderr)
        metrics_doc = json.load(sys.stdin)
    else:
        metrics_doc = metrics

    validate_metrics(metrics_doc)

    perc_doc = _run_perceptions_cmd(
        cmd=str(perceptions_script),
        metrics_doc=metrics_doc,
        path=path,
        base_dir=Path("."),
        verbose=verbose,
    )
    validate_perceptions(perc_doc)

    return run_judgement(
        perceptions=perc_doc,
        user_files=user_files,
        output_path=output_path,
    )
