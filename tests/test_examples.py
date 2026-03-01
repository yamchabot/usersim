"""
Integration tests: run `usersim run` end-to-end for each bundled example project.

These tests exercise the full pipeline (instrumentation → perceptions → judgement
→ report) against real example configs, so they catch regressions that unit tests
can't — e.g. broken instrumentation scripts, yaml config changes, report generation.

Each test:
  1. Runs `usersim run` in the example directory (with the right PATH for Node)
  2. Asserts it exits cleanly (all checks passed)
  3. Validates the results.json structure and scores
  4. Confirms report.html was written and is non-empty
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"

# Node.js locations to try (sandbox may have it in a non-standard place)
_NODE_PATHS = [
    "/workspace/workspace/node-v22.13.0-linux-arm64/bin",
    "/workspace/workspace/.nvm/versions/node/v22.22.0/bin",
    "/usr/local/bin",
    "/usr/bin",
]

# usersim binary: prefer the one co-installed with our Python package,
# then fall back to PATH search.
def _find_usersim_bin() -> str:
    import shutil
    candidates = [
        # same dir as pip-installed scripts (e.g. ~/.local/bin)
        Path(sys.executable).parent / "usersim",
        # common user-install locations
        Path.home() / ".local" / "bin" / "usersim",
        Path("/workspace/.local/bin/usersim"),
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    found = shutil.which("usersim")
    if found:
        return found
    raise FileNotFoundError(
        "usersim binary not found. Tried: "
        + ", ".join(str(c) for c in candidates)
        + ". Make sure usersim is installed."
    )

USERSIM_BIN = _find_usersim_bin()


def _env_with_node() -> dict:
    """Return an env dict that has Node on PATH."""
    extra = ":".join(p for p in _NODE_PATHS if Path(p).is_dir())
    base  = os.environ.copy()
    base["PATH"] = f"{extra}:{base.get('PATH', '')}"
    return base


def _run_usersim(example_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [USERSIM_BIN, "run", "--verbose"],
        cwd=str(example_dir),
        capture_output=True,
        text=True,
        env=_env_with_node(),
    )


def _load_results(example_dir: Path, config_results_path: str) -> dict:
    return json.loads((example_dir / config_results_path).read_text())


# ── local-notes ───────────────────────────────────────────────────────────────

class TestLocalNotesExample:
    EXAMPLE  = EXAMPLES_DIR / "local-notes"
    RESULTS  = "user_simulation/results.json"
    REPORT   = "user_simulation/report.html"
    SCENARIOS = ["baseline", "capture_path", "persistence",
                 "isolation", "sort_order", "offline", "context_switch"]
    PERSONAS  = 5   # number of user files in users/

    @pytest.fixture(scope="class")
    def run_result(self):
        return _run_usersim(self.EXAMPLE)

    @pytest.fixture(scope="class")
    def results(self, run_result):
        return _load_results(self.EXAMPLE, self.RESULTS)

    def test_exits_cleanly(self, run_result):
        assert run_result.returncode == 0, (
            f"usersim run failed:\n{run_result.stderr}"
        )

    def test_all_checks_passed_message(self, run_result):
        assert "ALL CHECKS PASSED" in run_result.stdout or \
               "ALL CHECKS PASSED" in run_result.stderr

    def test_results_schema(self, results):
        assert results.get("schema") == "usersim.matrix.v1"

    def test_summary_structure(self, results):
        s = results["summary"]
        assert {"total", "satisfied", "score"} <= s.keys()
        assert s["score"] == 1.0
        assert s["satisfied"] == s["total"]

    def test_all_scenarios_present(self, results):
        found = {r["scenario"] for r in results["results"]}
        assert set(self.SCENARIOS) == found

    def test_all_personas_present(self, results):
        persons = {r["person"] for r in results["results"]}
        assert len(persons) == self.PERSONAS

    def test_every_result_satisfied(self, results):
        failures = [r for r in results["results"] if not r["satisfied"]]
        assert failures == [], \
            f"Unsatisfied results: {[(r['person'], r['scenario']) for r in failures]}"

    def test_every_result_has_constraints(self, results):
        for r in results["results"]:
            assert isinstance(r.get("constraints"), list)
            assert len(r["constraints"]) > 0, \
                f"No constraints for {r['person']} / {r['scenario']}"

    def test_report_html_written(self):
        report = self.EXAMPLE / self.REPORT
        assert report.exists(), "report.html was not written"
        assert report.stat().st_size > 1000, "report.html looks suspiciously small"

    def test_report_html_has_scenario_data(self):
        """Regression: balls must carry data-constraints for click-to-detail."""
        html = (self.EXAMPLE / self.REPORT).read_text()
        assert 'data-constraints=' in html
        assert 'data-scenario-name=' in html


# ── data-processor ────────────────────────────────────────────────────────────

class TestDataProcessorExample:
    EXAMPLE   = EXAMPLES_DIR / "data-processor"
    RESULTS   = "usersim/results.json"
    REPORT    = "usersim/report.html"
    SCENARIOS = ["small", "medium", "large"]

    @pytest.fixture(scope="class")
    def run_result(self):
        return _run_usersim(self.EXAMPLE)

    @pytest.fixture(scope="class")
    def results(self, run_result):
        return _load_results(self.EXAMPLE, self.RESULTS)

    def test_exits_cleanly(self, run_result):
        assert run_result.returncode == 0, (
            f"usersim run failed:\n{run_result.stderr}"
        )

    def test_all_checks_passed_message(self, run_result):
        assert "ALL CHECKS PASSED" in run_result.stdout or \
               "ALL CHECKS PASSED" in run_result.stderr

    def test_results_schema(self, results):
        assert results.get("schema") == "usersim.matrix.v1"

    def test_summary_structure(self, results):
        s = results["summary"]
        assert {"total", "satisfied", "score"} <= s.keys()
        assert s["score"] == 1.0
        assert s["satisfied"] == s["total"]

    def test_all_scenarios_present(self, results):
        found = {r["scenario"] for r in results["results"]}
        assert set(self.SCENARIOS) == found

    def test_every_result_satisfied(self, results):
        failures = [r for r in results["results"] if not r["satisfied"]]
        assert failures == [], \
            f"Unsatisfied results: {[(r['person'], r['scenario']) for r in failures]}"

    def test_every_result_has_constraints(self, results):
        for r in results["results"]:
            assert isinstance(r.get("constraints"), list)
            assert len(r["constraints"]) > 0, \
                f"No constraints for {r['person']} / {r['scenario']}"

    def test_report_html_written(self):
        report = self.EXAMPLE / self.REPORT
        assert report.exists(), "report.html was not written"
        assert report.stat().st_size > 1000, "report.html looks suspiciously small"

    def test_report_html_has_scenario_data(self):
        html = (self.EXAMPLE / self.REPORT).read_text()
        assert 'data-constraints=' in html
        assert 'data-scenario-name=' in html
