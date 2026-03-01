"""
instrumentation.py — measure usersim itself.

Runs usersim CLI commands as subprocesses against the bundled examples
and edge cases, collecting metrics about exit codes, output validity,
timing, error handling, and report quality.

USERSIM_PATH controls which measurement function runs.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCENARIO = os.environ.get("USERSIM_PATH", "data_processor_example")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
USERSIM = shutil.which("usersim") or "usersim"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _run(args, *, stdin_data=None, cwd=None, timeout=120):
    """Run a subprocess and return the CompletedProcess."""
    return subprocess.run(
        args,
        input=stdin_data,
        capture_output=True,
        text=True,
        cwd=cwd or str(PROJECT_ROOT),
        timeout=timeout,
    )


def _is_valid_json(text):
    """Try to parse text as JSON, return (parsed, True) or (None, False)."""
    try:
        return json.loads(text), True
    except (json.JSONDecodeError, TypeError):
        return None, False


def _looks_like_traceback(text):
    """Return True if text looks like a raw Python traceback."""
    return "Traceback (most recent call last)" in text


# ── Scenario: data_processor_example ─────────────────────────────────────────

def measure_data_processor_example():
    """Run the full pipeline on examples/data-processor and measure everything."""
    dp_dir = PROJECT_ROOT / "examples" / "data-processor"
    out_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    out_file.close()

    try:
        t0 = time.perf_counter()
        result = _run(
            [USERSIM, "run",
             "--config", str(dp_dir / "usersim.yaml"),
             "--out", out_file.name],
            cwd=str(dp_dir),
        )
        wall_clock_ms = (time.perf_counter() - t0) * 1000

        parsed, valid_json = _is_valid_json(result.stdout)

        # Parse the output file too (--out writes there)
        file_parsed = None
        try:
            with open(out_file.name) as f:
                file_parsed = json.load(f)
        except Exception:
            pass

        # Use whichever source has results
        data = file_parsed or parsed or {}
        results = data.get("results", [])
        summary = data.get("summary", {})

        persons = set()
        paths = set()
        all_have_constraints = True
        for r in results:
            persons.add(r.get("person", ""))
            paths.add(r.get("path", ""))
            if "constraints" not in r:
                all_have_constraints = False

        return {
            "exit_code": result.returncode,
            "wall_clock_ms": round(wall_clock_ms, 1),
            "stdout_valid_json": valid_json or file_parsed is not None,
            "results_schema_valid": data.get("schema", "") in (
                "usersim.results.v1", "usersim.matrix.v1"
            ),
            "results_total": summary.get("total", 0),
            "results_satisfied": summary.get("satisfied", 0),
            "results_score": summary.get("score", 0.0),
            "person_count": len(persons),
            "scenario_count": len(paths),
            "all_constraints_present": all_have_constraints and len(results) > 0,
            "stderr_output": len(result.stderr.strip()) > 0,
        }
    finally:
        os.unlink(out_file.name)


# ── Scenario: scaffold_and_validate ──────────────────────────────────────────

def measure_scaffold_and_validate():
    """Run usersim init in a temp dir and verify the scaffolded structure."""
    with tempfile.TemporaryDirectory(prefix="usersim_dogfood_") as tmp:
        result = _run([USERSIM, "init", tmp])

        tmp_path = Path(tmp)
        config_path = tmp_path / "usersim.yaml"
        instr_path = tmp_path / "instrumentation.py"
        perc_path = tmp_path / "usersim" / "perceptions.py"
        user_path = tmp_path / "usersim" / "users" / "example_user.py"

        yaml_parseable = False
        if config_path.exists():
            try:
                import yaml
                with open(config_path) as f:
                    yaml.safe_load(f)
                yaml_parseable = True
            except Exception:
                pass

        all_files = list(tmp_path.rglob("*"))
        file_count = sum(1 for f in all_files if f.is_file())

        return {
            "init_exit_code": result.returncode,
            "config_created": config_path.exists(),
            "instrumentation_created": instr_path.exists(),
            "perceptions_created": perc_path.exists(),
            "user_file_created": user_path.exists(),
            "yaml_parseable": yaml_parseable,
            "scaffold_file_count": file_count,
        }


# ── Scenario: bad_config ────────────────────────────────────────────────────

def measure_bad_config():
    """Run usersim with intentionally broken inputs and verify graceful errors."""
    with tempfile.TemporaryDirectory(prefix="usersim_dogfood_bad_") as tmp:
        # 1. Missing config file
        r_missing = _run(
            [USERSIM, "run", "--config", "/nonexistent/usersim.yaml"],
        )

        # 2. Bad YAML content
        bad_yaml_path = Path(tmp) / "bad.yaml"
        bad_yaml_path.write_text(":::not valid yaml{{{\n")
        r_bad_yaml = _run(
            [USERSIM, "run", "--config", str(bad_yaml_path)],
        )

        # 3. Valid YAML but users glob matches nothing
        empty_users_path = Path(tmp) / "empty_users.yaml"
        empty_users_path.write_text(
            'version: 1\n'
            'instrumentation: "echo {}"\n'
            'perceptions: "echo {}"\n'
            'users:\n'
            '  - nonexistent_dir/*.py\n'
            'paths:\n'
            '  - default\n'
        )
        r_no_users = _run(
            [USERSIM, "run", "--config", str(empty_users_path)],
        )

        # Check error quality
        all_stderr = r_missing.stderr + r_bad_yaml.stderr + r_no_users.stderr
        all_stdout = r_missing.stdout + r_bad_yaml.stdout + r_no_users.stdout

        return {
            "missing_config_exit_code": r_missing.returncode,
            "bad_yaml_exit_code": r_bad_yaml.returncode,
            "missing_users_exit_code": r_no_users.returncode,
            "error_has_stderr": len(all_stderr.strip()) > 0,
            "error_not_traceback": not _looks_like_traceback(all_stderr),
            "error_not_on_stdout": not _looks_like_traceback(all_stdout),
        }


# ── Scenario: judge_standalone ───────────────────────────────────────────────

def measure_judge_standalone():
    """Run usersim judge directly with synthetic perceptions and a minimal user file."""
    with tempfile.TemporaryDirectory(prefix="usersim_dogfood_judge_") as tmp:
        tmp_path = Path(tmp)

        # Create a synthetic perceptions JSON
        perc = {
            "schema": "usersim.perceptions.v1",
            "path": "test",
            "person": "all",
            "facts": {
                "response_ms": 50.0,
                "error_rate": 0.0,
            },
        }
        perc_path = tmp_path / "perceptions.json"
        perc_path.write_text(json.dumps(perc))

        # Create a minimal user file
        user_code = (
            "from usersim import Person\n"
            "\n"
            "class TestUser(Person):\n"
            "    name = 'test_user'\n"
            "    def constraints(self, P):\n"
            "        return [\n"
            "            P.response_ms <= 100,\n"
            "            P.error_rate <= 0.01,\n"
            "        ]\n"
        )
        user_path = tmp_path / "test_user.py"
        user_path.write_text(user_code)

        result = _run([
            USERSIM, "judge",
            "--perceptions", str(perc_path),
            "--users", str(user_path),
            "--quiet",
        ])

        parsed, valid_json = _is_valid_json(result.stdout)
        data = parsed or {}

        return {
            "judge_exit_code": result.returncode,
            "judge_output_valid_json": valid_json,
            "judge_has_results": "results" in data,
            "judge_schema_correct": data.get("schema", "") == "usersim.results.v1",
            "judge_satisfied_count": data.get("summary", {}).get("satisfied", 0),
            "judge_total_count": data.get("summary", {}).get("total", 0),
        }


# ── Scenario: report_generation ──────────────────────────────────────────────

def measure_report_generation():
    """Generate an HTML report from known results and verify it's valid."""
    with tempfile.TemporaryDirectory(prefix="usersim_dogfood_report_") as tmp:
        tmp_path = Path(tmp)

        # Create a known-good results JSON (matrix format — each result has "path")
        results_data = {
            "schema": "usersim.matrix.v1",
            "results": [
                {
                    "person": "happy_user",
                    "path": "normal",
                    "role": "Tester",
                    "goal": "Verify report generation",
                    "pronoun": "they",
                    "satisfied": True,
                    "score": 1.0,
                    "constraints": [
                        {"label": "response_ms <= 100", "passed": True, "antecedent_fired": None},
                    ],
                    "violations": [],
                },
                {
                    "person": "sad_user",
                    "path": "normal",
                    "role": "Tester",
                    "goal": "Verify failure reporting",
                    "pronoun": "they",
                    "satisfied": False,
                    "score": 0.5,
                    "constraints": [
                        {"label": "response_ms <= 50", "passed": False, "antecedent_fired": None},
                        {"label": "error_rate <= 0.01", "passed": True, "antecedent_fired": None},
                    ],
                    "violations": ["response_ms <= 50"],
                },
            ],
            "summary": {"total": 2, "satisfied": 1, "score": 0.5},
        }
        results_path = tmp_path / "results.json"
        results_path.write_text(json.dumps(results_data))

        report_path = tmp_path / "report.html"
        result = _run([
            USERSIM, "report",
            "--results", str(results_path),
            "--out", str(report_path),
        ])

        html = ""
        if report_path.exists():
            html = report_path.read_text()

        return {
            "report_exit_code": result.returncode,
            "report_file_created": report_path.exists(),
            "report_file_size_bytes": len(html),
            "report_has_doctype": html.lstrip().startswith("<!DOCTYPE") or html.lstrip().startswith("<!doctype"),
            "report_has_cards": 'class="card ' in html or 'class="card"' in html,
            "report_is_self_contained": (
                '<link rel="stylesheet"' not in html
                and '<script src=' not in html
            ) if html else False,
        }


# ── Scenario: full_integration ───────────────────────────────────────────────

def measure_full_integration():
    """
    Run all subsystems in a single pass and return a complete metric set.

    This path exists to ensure every persona constraint has a real value
    to evaluate against — no vacuous antecedents from missing metrics.

    It combines: pipeline run + init scaffold + error handling +
                 judge standalone + report generation.
    """
    metrics = {}

    # 1. Pipeline (data-processor example) ─────────────────────────────────
    dp_metrics = measure_data_processor_example()
    metrics.update({
        "exit_code":              dp_metrics["exit_code"],
        "wall_clock_ms":         dp_metrics["wall_clock_ms"],
        "stdout_valid_json":     dp_metrics["stdout_valid_json"],
        "results_schema_valid":  dp_metrics["results_schema_valid"],
        "results_total":         dp_metrics["results_total"],
        "results_satisfied":     dp_metrics["results_satisfied"],
        "results_score":         dp_metrics["results_score"],
        "person_count":          dp_metrics["person_count"],
        "scenario_count":        dp_metrics["scenario_count"],
        "all_constraints_present": dp_metrics["all_constraints_present"],
        "stderr_output":         dp_metrics["stderr_output"],
    })

    # 2. Scaffold (init) ────────────────────────────────────────────────────
    init_metrics = measure_scaffold_and_validate()
    metrics.update({
        "init_exit_code":        init_metrics["init_exit_code"],
        "config_created":        init_metrics["config_created"],
        "instrumentation_created": init_metrics["instrumentation_created"],
        "perceptions_created":   init_metrics["perceptions_created"],
        "user_file_created":     init_metrics["user_file_created"],
        "yaml_parseable":        init_metrics["yaml_parseable"],
        "scaffold_file_count":   init_metrics["scaffold_file_count"],
    })

    # 3. Error handling ─────────────────────────────────────────────────────
    bad_metrics = measure_bad_config()
    metrics.update({
        "missing_config_exit_code": bad_metrics["missing_config_exit_code"],
        "bad_yaml_exit_code":       bad_metrics["bad_yaml_exit_code"],
        "missing_users_exit_code":  bad_metrics["missing_users_exit_code"],
        "error_has_stderr":         bad_metrics["error_has_stderr"],
        "error_not_traceback":      bad_metrics["error_not_traceback"],
        "error_not_on_stdout":      bad_metrics["error_not_on_stdout"],
    })

    # 4. Judge standalone ───────────────────────────────────────────────────
    judge_metrics = measure_judge_standalone()
    metrics.update({
        "judge_exit_code":          judge_metrics["judge_exit_code"],
        "judge_output_valid_json":  judge_metrics["judge_output_valid_json"],
        "judge_has_results":        judge_metrics["judge_has_results"],
        "judge_schema_correct":     judge_metrics["judge_schema_correct"],
        "judge_satisfied_count":    judge_metrics["judge_satisfied_count"],
        "judge_total_count":        judge_metrics["judge_total_count"],
    })

    # 5. Report generation ──────────────────────────────────────────────────
    report_metrics = measure_report_generation()
    metrics.update({
        "report_exit_code":         report_metrics["report_exit_code"],
        "report_file_created":      report_metrics["report_file_created"],
        "report_file_size_bytes":   report_metrics["report_file_size_bytes"],
        "report_has_doctype":       report_metrics["report_has_doctype"],
        "report_has_cards":         report_metrics["report_has_cards"],
        "report_is_self_contained": report_metrics["report_is_self_contained"],
    })

    # 6. Violation health ───────────────────────────────────────────────────
    vh_metrics = measure_violation_health()
    metrics.update(vh_metrics)

    # 7. Broken example ─────────────────────────────────────────────────────
    broken_metrics = measure_broken_example()
    metrics.update(broken_metrics)

    return metrics


# ── Scenario: violation_health ────────────────────────────────────────────────

def measure_violation_health():
    """
    Run data-processor and introspect the results to measure constraint health.

    A useful constraint system should have *some* violations — constraints that
    never fire across all runs are either too loose or testing the wrong thing.
    This path measures the violation rate of usersim against itself.
    """
    dp_dir = PROJECT_ROOT / "examples" / "data-processor"
    out_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    out_file.close()

    try:
        _run(
            [USERSIM, "run",
             "--config", str(dp_dir / "usersim.yaml"),
             "--out", out_file.name],
            cwd=str(dp_dir),
        )

        try:
            with open(out_file.name) as f:
                data = json.load(f)
        except Exception:
            return {
                "vh_total_constraint_evals": 0,
                "vh_total_violations": 0,
                "vh_unique_constraints": 0,
                "vh_violated_constraints": 0,
                "vh_antecedent_fired_count": 0,
            }

        # Walk every persona × path result and count constraint outcomes
        # Results are flat: one dict per persona×path combination
        total_evals = 0
        total_violations = 0
        antecedent_fired = 0
        all_constraints = set()
        violated_constraints = set()

        for row in data.get("results", []):
            for c in row.get("constraints", []):
                label = c.get("label", "")
                all_constraints.add(label)
                total_evals += 1
                if c.get("antecedent_fired", True):
                    antecedent_fired += 1
                if not c.get("passed", True):
                    total_violations += 1
                    violated_constraints.add(label)

        return {
            "vh_total_constraint_evals": total_evals,
            "vh_total_violations": total_violations,
            "vh_unique_constraints": len(all_constraints),
            "vh_violated_constraints": len(violated_constraints),
            "vh_antecedent_fired_count": antecedent_fired,
        }
    finally:
        try:
            os.unlink(out_file.name)
        except OSError:
            pass


# ── Scenario: broken_example ──────────────────────────────────────────────────

def measure_broken_example():
    """
    Run usersim with an intentionally broken instrumentation script that exits
    non-zero and emits no valid JSON.  Measures that usersim detects and
    surfaces the failure rather than silently producing empty results.
    """
    import textwrap

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Write a deliberately broken instrumentation script
        broken_script = tmpdir / "broken_instr.py"
        broken_script.write_text(textwrap.dedent("""\
            import sys, json
            # Emit partial metrics then exit 1 — simulates a crash mid-run
            print(json.dumps({
                "schema": "usersim.metrics.v1",
                "path": "broken",
                "metrics": {
                    "exit_code": 1,
                    "wall_clock_ms": 50,
                }
            }))
            sys.exit(1)
        """))

        # Minimal user file
        user_file = tmpdir / "broken_user.py"
        user_file.write_text(textwrap.dedent("""\
            import sys, os
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'usersim'))
            from usersim import Person
            class BrokenUser(Person):
                name = "broken_user"
                role = "tester"
                goal = "detect instrumentation failures"
                pronoun = "they"
                def constraints(self, P):
                    return []
        """))

        # Config pointing at the broken script
        config = tmpdir / "broken.yaml"
        config.write_text(textwrap.dedent(f"""\
            instrumentation: "python3 {broken_script}"
            paths:
              - broken
            users:
              - {user_file}
            output: "{tmpdir}/broken_results.json"
        """))

        result = _run(
            [USERSIM, "run", "--config", str(config)],
            cwd=str(tmpdir),
        )

        # Read output if it exists
        out_path = tmpdir / "broken_results.json"
        ran_ok = False
        caught_failure = False
        try:
            with open(out_path) as f:
                out = json.load(f)
            ran_ok = True
            # usersim should report a non-zero exit in summary or an error field
            summary = out.get("summary", {})
            caught_failure = (
                summary.get("exit_code", 0) != 0
                or out.get("error") is not None
                or summary.get("passed", 1) == 0
            )
        except Exception:
            # If usersim itself exited non-zero that's also a valid failure detection
            caught_failure = result.returncode != 0

        return {
            "broken_instr_exit_code": result.returncode,
            "broken_ran_to_completion": ran_ok,
            "broken_failure_detected": caught_failure,
        }


# ── Dispatch ─────────────────────────────────────────────────────────────────

DISPATCH = {
    "data_processor_example": measure_data_processor_example,
    "scaffold_and_validate": measure_scaffold_and_validate,
    "bad_config": measure_bad_config,
    "judge_standalone": measure_judge_standalone,
    "report_generation": measure_report_generation,
    "full_integration": measure_full_integration,
    "violation_health": measure_violation_health,
    "broken_example": measure_broken_example,
}

if __name__ == "__main__":
    fn = DISPATCH.get(SCENARIO)
    if fn is None:
        print(f"Unknown path: {SCENARIO}", file=sys.stderr)
        sys.exit(1)

    print(f"[instrumentation] path={SCENARIO}", file=sys.stderr)
    metrics = fn()
    print(f"[instrumentation] collected {len(metrics)} metrics", file=sys.stderr)

    json.dump({
        "schema": "usersim.metrics.v1",
        "path": SCENARIO,
        "metrics": metrics,
    }, sys.stdout)
