"""
Tests for usersim.constraints — the pre-built domain constraint library.

Each domain module is tested with:
  1. A "healthy" input set that should pass all constraints
  2. An "unhealthy" input set that should trigger specific failures
  3. Edge cases (zero values, boundary conditions, sentinel -1)
"""
import pytest
from usersim.judgement.engine import _make_fact_vars
from usersim.judgement.person import FactNamespace
from usersim.judgement.z3_compat import Solver, sat
from usersim.constraints.reliability import error_rate, latency, availability
from usersim.constraints.throughput  import throughput_floor, queue_depth
from usersim.constraints.search      import result_count, precision, recall
from usersim.constraints.retention   import session_depth, return_rate
from usersim.constraints.privacy     import data_exposure, consent, audit_trail
from usersim.constraints.cli         import exit_codes, output_format, timing


def _make_P(facts):
    return FactNamespace(_make_fact_vars(facts))


def _eval(constraints, facts):
    """Return (passed_labels, failed_labels) for a constraint list + facts."""
    P = _make_P(facts)
    passed, failed = [], []
    for c in constraints:
        s = Solver(); s.add(c)
        ok = s.check() == sat
        label = getattr(c, "_repr", repr(c))
        (passed if ok else failed).append(label)
    return passed, failed


def _all_pass(fn, facts, **kw):
    P = _make_P(facts)
    _, failed = _eval(fn(P, **kw), facts)
    assert failed == [], f"Expected all pass but failed: {failed}"


def _some_fail(fn, facts, expected_labels, **kw):
    P = _make_P(facts)
    _, failed = _eval(fn(P, **kw), facts)
    for label in expected_labels:
        assert any(label in f for f in failed), (
            f"Expected '{label}' to fail but it passed. All failures: {failed}"
        )


# ── reliability/error_rate ────────────────────────────────────────────────────

class TestErrorRate:
    HEALTHY   = {"request_total": 1000, "error_total": 5}    # 0.5% — under 1%
    UNHEALTHY = {"request_total": 100,  "error_total": 5}    # 5%   — over 1%

    def test_healthy_passes(self):
        _all_pass(error_rate, self.HEALTHY)

    def test_high_error_rate_fails(self):
        _some_fail(error_rate, self.UNHEALTHY, ["error-rate-bounded"])

    def test_custom_threshold_5pct(self):
        facts = {"request_total": 100, "error_total": 3}     # 3% — passes at max_pct=5
        _all_pass(error_rate, facts, max_pct=5)

    def test_zero_requests_no_errors(self):
        _all_pass(error_rate, {"request_total": 0, "error_total": 0})

    def test_errors_exceed_requests_fails(self):
        bad = {"request_total": 10, "error_total": 15}
        _some_fail(error_rate, bad, ["errors-never-exceed-requests"])

    def test_missing_facts_vacuous(self):
        # No error_total in facts → sentinel -1 → antecedents don't fire
        _all_pass(error_rate, {"request_total": 100})


# ── reliability/latency ───────────────────────────────────────────────────────

class TestLatency:
    HEALTHY   = {"p50_ms": 100, "p95_ms": 300, "p99_ms": 800}
    UNHEALTHY = {"p50_ms": 100, "p95_ms": 600, "p99_ms": 1500}

    def test_healthy_passes(self):
        _all_pass(latency, self.HEALTHY)

    def test_high_p95_p99_fails(self):
        _some_fail(latency, self.UNHEALTHY, ["p95-under-threshold", "p99-under-threshold"])

    def test_p50_exceeds_p95_fails(self):
        bad = {"p50_ms": 500, "p95_ms": 300, "p99_ms": 400}
        _some_fail(latency, bad, ["p50-lte-p95"])

    def test_sentinel_minus1_vacuous(self):
        _all_pass(latency, {"p50_ms": -1, "p95_ms": -1, "p99_ms": -1})

    def test_custom_thresholds(self):
        facts = {"p50_ms": 300, "p95_ms": 700, "p99_ms": 1800}
        _all_pass(latency, facts, p50_ms=400, p95_ms=800, p99_ms=2000)


# ── reliability/availability ──────────────────────────────────────────────────

class TestAvailability:
    HEALTHY   = {"uptime_pct": 99, "consecutive_errors": 2}
    UNHEALTHY = {"uptime_pct": 95, "consecutive_errors": 10}

    def test_healthy_passes(self):
        _all_pass(availability, self.HEALTHY)

    def test_low_uptime_fails(self):
        _some_fail(availability, self.UNHEALTHY, ["uptime-above-floor"])

    def test_long_streak_fails(self):
        _some_fail(availability, self.UNHEALTHY, ["no-long-error-streaks"])

    def test_custom_threshold(self):
        facts = {"uptime_pct": 95, "consecutive_errors": 1}
        _all_pass(availability, facts, min_uptime_pct=90)


# ── throughput ────────────────────────────────────────────────────────────────

class TestThroughput:
    HEALTHY = {
        "items_processed": 500, "items_total": 500,
        "elapsed_ms": 1000, "dropped_items": 0,
        "queue_depth": 50, "worker_count": 4,
    }

    def test_healthy_passes_floor(self):
        _all_pass(throughput_floor, self.HEALTHY)

    def test_healthy_passes_queue(self):
        _all_pass(queue_depth, self.HEALTHY)

    def test_slow_throughput_fails(self):
        # 50 items / 1000ms = 50/s < 100/s floor
        facts = {**self.HEALTHY, "items_processed": 50}
        _some_fail(throughput_floor, facts, ["floor-rate-met"])

    def test_drops_under_half_capacity_fails(self):
        facts = {**self.HEALTHY, "dropped_items": 5, "queue_depth": 10}
        _some_fail(queue_depth, facts, ["no-drops-under-half-capacity"])

    def test_queue_exceeds_per_worker_limit(self):
        facts = {**self.HEALTHY, "queue_depth": 1000, "worker_count": 2}
        _some_fail(queue_depth, facts, ["queue-scales-with-workers"])

    def test_processed_exceeds_total_fails(self):
        facts = {**self.HEALTHY, "items_processed": 600, "items_total": 500}
        _some_fail(throughput_floor, facts, ["processed-never-exceeds-total"])


# ── search ────────────────────────────────────────────────────────────────────

class TestSearch:
    HEALTHY = {
        "results_returned": 10, "results_relevant": 9,
        "total_relevant": 12, "corpus_size": 50, "top_k": 10,
    }

    def test_healthy_result_count_passes(self):
        _all_pass(result_count, self.HEALTHY)

    def test_healthy_precision_passes(self):
        _all_pass(precision, self.HEALTHY)

    def test_healthy_recall_passes(self):
        _all_pass(recall, self.HEALTHY)

    def test_low_precision_fails(self):
        # 5/10 = 50% — fails 80% default floor
        _some_fail(precision, {**self.HEALTHY, "results_relevant": 5}, ["precision-above-floor"])

    def test_low_recall_fails(self):
        # 3/12 = 25% — fails 60% default floor
        _some_fail(recall, {**self.HEALTHY, "results_relevant": 3}, ["recall-above-floor"])

    def test_results_exceed_top_k_fails(self):
        _some_fail(result_count, {**self.HEALTHY, "results_returned": 20, "top_k": 10},
                   ["results-never-exceed-top-k"])

    def test_relevant_exceed_returned_fails(self):
        _some_fail(result_count, {**self.HEALTHY, "results_relevant": 15},
                   ["relevant-never-exceed-returned"])


# ── retention ─────────────────────────────────────────────────────────────────

class TestRetention:
    HEALTHY = {
        "depth_p50": 5, "depth_p90": 12,
        "sessions_total": 100, "sessions_returned": 30,
        "bounce_count": 10, "task_completion_pct": 80,
    }

    def test_healthy_depth_passes(self):
        _all_pass(session_depth, self.HEALTHY)

    def test_healthy_return_rate_passes(self):
        _all_pass(return_rate, self.HEALTHY)

    def test_low_return_rate_fails(self):
        _some_fail(return_rate, {**self.HEALTHY, "sessions_returned": 5},
                   ["return-rate-above-floor"])

    def test_high_bounce_rate_fails(self):
        _some_fail(session_depth, {**self.HEALTHY, "bounce_count": 60},
                   ["bounce-rate-under-ceiling"])

    def test_p50_exceeds_p90_fails(self):
        _some_fail(session_depth, {**self.HEALTHY, "depth_p50": 15, "depth_p90": 8},
                   ["p50-lte-p90"])

    def test_no_returns_without_sessions(self):
        bad = {"sessions_total": 0, "sessions_returned": 5,
               "depth_p50": 5, "depth_p90": 12, "bounce_count": 0}
        _some_fail(return_rate, bad, ["no-returns-without-sessions"])


# ── privacy ───────────────────────────────────────────────────────────────────

class TestPrivacy:
    HEALTHY = {
        "pii_fields_exposed": 0, "pii_fields_total": 3,
        "anonymized": True, "consent_recorded": True,
        "audit_events_total": 5, "audit_events_expected": 5,
        "data_retention_days": 90,
    }

    def test_healthy_exposure_passes(self):
        _all_pass(data_exposure, self.HEALTHY)

    def test_healthy_consent_passes(self):
        _all_pass(consent, self.HEALTHY)

    def test_healthy_audit_passes(self):
        _all_pass(audit_trail, self.HEALTHY)

    def test_pii_exposure_fails(self):
        facts = {**self.HEALTHY, "pii_fields_exposed": 2, "anonymized": False}
        _some_fail(data_exposure, facts, ["no-pii-in-output"])

    def test_no_consent_fails(self):
        _some_fail(consent, {**self.HEALTHY, "consent_recorded": False},
                   ["consent-recorded-before-use"])

    def test_retention_exceeds_policy_fails(self):
        _some_fail(audit_trail, {**self.HEALTHY, "data_retention_days": 400},
                   ["retention-within-policy"])

    def test_missing_audit_events_fails(self):
        _some_fail(audit_trail, {**self.HEALTHY, "audit_events_total": 2},
                   ["audit-log-complete"])


# ── cli ───────────────────────────────────────────────────────────────────────

class TestCLI:
    HEALTHY = {
        "exit_code": 0, "stdout_bytes": 200, "stderr_bytes": 0,
        "wall_clock_ms": 500, "output_valid_json": True,
        "has_error_message": False, "traceback_present": False,
    }
    FAIL_PATH = {
        "exit_code": 1, "stdout_bytes": 0, "stderr_bytes": 80,
        "wall_clock_ms": 10, "output_valid_json": False,
        "has_error_message": True, "traceback_present": False,
    }

    def test_healthy_exit_codes_passes(self):
        _all_pass(exit_codes, self.HEALTHY)

    def test_healthy_output_format_passes(self):
        _all_pass(output_format, self.HEALTHY)

    def test_healthy_timing_passes(self):
        _all_pass(timing, self.HEALTHY)

    def test_error_path_exit_codes_passes(self):
        _all_pass(exit_codes, self.FAIL_PATH)

    def test_error_path_output_passes(self):
        _all_pass(output_format, self.FAIL_PATH)

    def test_traceback_fails(self):
        _some_fail(exit_codes, {**self.HEALTHY, "traceback_present": True},
                   ["no-traceback"])

    def test_error_message_on_success_fails(self):
        _some_fail(exit_codes, {**self.HEALTHY, "has_error_message": True},
                   ["exit-0-means-success"])

    def test_stderr_on_success_fails(self):
        _some_fail(exit_codes, {**self.HEALTHY, "stderr_bytes": 20},
                   ["stderr-not-polluted"])

    def test_timing_ceiling(self):
        _some_fail(timing, {**self.HEALTHY, "wall_clock_ms": 15000},
                   ["timing-under-ceiling"])

    def test_custom_timing_ceiling(self):
        facts = {**self.HEALTHY, "wall_clock_ms": 3000}
        _all_pass(timing, facts, max_ms=5000)


# ── composition ───────────────────────────────────────────────────────────────

class TestComposition:
    ALL_FACTS = {
        "request_total": 100, "error_total": 0,
        "p50_ms": 100, "p95_ms": 200, "p99_ms": 400,
        "uptime_pct": 99, "consecutive_errors": 1,
        "items_processed": 500, "items_total": 500,
        "elapsed_ms": 1000, "dropped_items": 0,
        "queue_depth": 10, "worker_count": 4,
        "results_returned": 10, "results_relevant": 9,
        "total_relevant": 12, "corpus_size": 50, "top_k": 10,
        "depth_p50": 5, "depth_p90": 12, "sessions_total": 20,
        "sessions_returned": 8, "bounce_count": 3, "task_completion_pct": 85,
        "pii_fields_exposed": 0, "pii_fields_total": 3, "anonymized": True,
        "consent_recorded": True, "audit_events_total": 5,
        "audit_events_expected": 5, "data_retention_days": 90,
        "exit_code": 0, "stdout_bytes": 100, "stderr_bytes": 0,
        "wall_clock_ms": 250, "output_valid_json": True,
        "has_error_message": False, "traceback_present": False,
    }

    def test_all_modules_healthy(self):
        P = _make_P(self.ALL_FACTS)
        all_c = (
            error_rate(P) + latency(P) + availability(P) +
            throughput_floor(P) + queue_depth(P) +
            result_count(P) + precision(P) + recall(P) +
            session_depth(P) + return_rate(P) +
            data_exposure(P) + consent(P) + audit_trail(P) +
            exit_codes(P) + output_format(P) + timing(P)
        )
        _, failed = _eval(all_c, self.ALL_FACTS)
        assert failed == [], f"Unexpected failures: {failed}"

    def test_library_has_at_least_60_constraints(self):
        facts = {"request_total": 1}
        P = _make_P(facts)
        total = sum(len(fn(P)) for fn in [
            error_rate, latency, availability,
            throughput_floor, queue_depth,
            result_count, precision, recall,
            session_depth, return_rate,
            data_exposure, consent, audit_trail,
            exit_codes, output_format, timing,
        ])
        assert total >= 60, f"Expected >= 60 library constraints, got {total}"

    def test_missing_facts_never_crash(self):
        """Constraint functions called with empty facts must not raise."""
        P = _make_P({})
        for fn in [error_rate, latency, availability, throughput_floor, queue_depth,
                   result_count, precision, recall, session_depth, return_rate,
                   data_exposure, consent, audit_trail, exit_codes, output_format, timing]:
            try:
                constraints = fn(P)
                assert isinstance(constraints, list)
            except Exception as e:
                pytest.fail(f"{fn.__name__}(P) raised with empty facts: {e}")
