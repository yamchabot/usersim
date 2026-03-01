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
DOGFOOD_DIR  = Path(__file__).parent.parent / "dogfood"

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
                 "isolation", "sort_order", "offline", "context_switch",
                 "search_heavy", "bulk_import"]
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
    SCENARIOS = ["small", "medium", "large", "empty", "errors", "concurrent"]

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


# ── dogfood ───────────────────────────────────────────────────────────────────

class TestDogfood:
    """usersim testing itself — usersim.yaml is at project root."""

    EXAMPLE   = DOGFOOD_DIR          # where results/report land
    ROOT      = DOGFOOD_DIR.parent   # where usersim.yaml lives
    RESULTS   = "results.json"
    REPORT    = "report.html"
    SCENARIOS = [
        "data_processor_example",
        "scaffold_and_validate",
        "bad_config",
        "judge_standalone",
        "report_generation",
        "full_integration",
        "violation_health",
        "broken_example",
    ]
    PERSONAS  = 16
    # constraint_health_auditor intentionally has known failing constraints
    # (health/some-violations-occur, health/antecedents-fire-meaningfully,
    #  health/broken-does-not-crash-usersim) — these surface real gaps in
    # usersim itself and should remain failing until the gaps are fixed.
    KNOWN_FAILING_PERSONAS = {"constraint_health_auditor"}

    @pytest.fixture(scope="class")
    def run_result(self):
        return _run_usersim(self.ROOT)

    @pytest.fixture(scope="class")
    def results(self, run_result):
        return _load_results(self.EXAMPLE, self.RESULTS)

    def test_exits_cleanly(self, run_result):
        # Exit code 2 = some personas unsatisfied (expected: only KNOWN_FAILING_PERSONAS)
        assert run_result.returncode in (0, 2), (
            f"usersim run crashed unexpectedly:\n{run_result.stderr}"
        )

    def test_all_checks_passed_or_only_known_failures(self, run_result):
        output = run_result.stdout + run_result.stderr
        if "ALL CHECKS PASSED" in output:
            return
        # Otherwise verify only known-failing personas appear in the output
        for line in output.splitlines():
            if line.startswith("❌"):
                persona = line.split("(")[0].replace("❌", "").strip()
                assert persona in self.KNOWN_FAILING_PERSONAS, \
                    f"Unexpected failing persona: {persona!r}"

    def test_results_schema(self, results):
        assert results.get("schema") == "usersim.matrix.v1"

    def test_summary_structure(self, results):
        s = results["summary"]
        assert {"total", "satisfied", "score"} <= s.keys()

    def test_all_scenarios_present(self, results):
        found = {r["scenario"] for r in results["results"]}
        assert set(self.SCENARIOS) == found

    def test_all_personas_present(self, results):
        persons = {r["person"] for r in results["results"]}
        assert len(persons) == self.PERSONAS, \
            f"Expected {self.PERSONAS} personas, got {len(persons)}: {sorted(persons)}"

    def test_every_result_satisfied_except_known(self, results):
        failures = [
            r for r in results["results"]
            if not r["satisfied"] and r["person"] not in self.KNOWN_FAILING_PERSONAS
        ]
        assert failures == [], \
            f"Unexpected failures: {[(r['person'], r['scenario']) for r in failures]}"

    def test_every_result_has_constraints(self, results):
        for r in results["results"]:
            assert isinstance(r.get("constraints"), list)
            assert len(r["constraints"]) > 0, \
                f"No constraints for {r['person']} / {r['scenario']}"

    def test_zero_vacuous_constraints(self, results):
        """full_integration scenario must fire every antecedent (except known-failing personas)."""
        vacuous = [
            (r["person"], c["label"])
            for r in results["results"]
            if r["scenario"] == "full_integration"
            and r["person"] not in self.KNOWN_FAILING_PERSONAS
            for c in r.get("constraints", [])
            if c.get("antecedent_fired") is False
        ]
        assert vacuous == [], \
            f"Vacuous constraints in full_integration: {vacuous}"

    def test_effective_tests_floor(self, results):
        """Regression guard: effective test count must not fall below 50k."""
        eff = results["summary"].get("effective_tests", 0)
        assert eff >= 50_000, f"Effective tests dropped to {eff:,} — constraint coverage regressed"

    def test_report_html_written(self):
        report = self.EXAMPLE / self.REPORT
        assert report.exists(), "report.html was not written"
        assert report.stat().st_size > 1000, "report.html is suspiciously small"

    def test_report_html_has_scenario_data(self):
        html = (self.EXAMPLE / self.REPORT).read_text()
        assert 'data-constraints=' in html
        assert 'data-scenario-name=' in html
