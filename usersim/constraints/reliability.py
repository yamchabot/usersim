"""
usersim.constraints.reliability — error rate, latency, and availability.

Perceptions contract:
  error_total       (int >= 0)   — number of errors observed
  request_total     (int >= 1)   — total requests / operations
  p50_ms            (int >= 0)   — median latency in milliseconds
  p95_ms            (int >= 0)   — 95th-percentile latency
  p99_ms            (int >= 0)   — 99th-percentile latency
  uptime_pct        (int 0-100)  — availability as integer percentage (e.g. 99)
  consecutive_errors (int >= 0)  — longest error streak

All thresholds are overridable. Constraints are gated with Implies so they
are vacuous when the relevant perceptions return the sentinel -1.
"""
from usersim.judgement.z3_compat import And, Implies, Not, named


def error_rate(P, *, max_pct: int = 1):
    """Error count bounded as a fraction of total requests.

    Uses integer arithmetic to avoid floats in Z3:
      error_total * 100 <= request_total * max_pct

    Args:
        P:       FactNamespace from the persona constraint method.
        max_pct: Maximum acceptable error percentage (default 1%).
    """
    return [
        named("reliability/error-rate-bounded",
              Implies(P.request_total >= 1,
                      P.error_total * 100 <= P.request_total * max_pct)),
        named("reliability/errors-never-exceed-requests",
              Implies(P.request_total >= 1,
                      P.error_total <= P.request_total)),
        named("reliability/no-errors-on-zero-requests",
              Implies(P.request_total == 0, P.error_total == 0)),
        named("reliability/requests-positive-when-errors-observed",
              Implies(P.error_total >= 1, P.request_total >= 1)),
    ]


def latency(P, *, p50_ms: int = 200, p95_ms: int = 500, p99_ms: int = 1000):
    """Latency percentiles bounded and internally consistent.

    Args:
        P:      FactNamespace.
        p50_ms: Median latency ceiling (default 200ms).
        p95_ms: 95th-percentile ceiling (default 500ms).
        p99_ms: 99th-percentile ceiling (default 1000ms).
    """
    return [
        named("reliability/p50-under-threshold",
              Implies(P.p50_ms >= 0, P.p50_ms <= p50_ms)),
        named("reliability/p95-under-threshold",
              Implies(P.p95_ms >= 0, P.p95_ms <= p95_ms)),
        named("reliability/p99-under-threshold",
              Implies(P.p99_ms >= 0, P.p99_ms <= p99_ms)),
        # Monotonicity: p50 ≤ p95 ≤ p99
        named("reliability/p50-lte-p95",
              Implies(And(P.p50_ms >= 0, P.p95_ms >= 0),
                      P.p50_ms <= P.p95_ms)),
        named("reliability/p95-lte-p99",
              Implies(And(P.p95_ms >= 0, P.p99_ms >= 0),
                      P.p95_ms <= P.p99_ms)),
        named("reliability/p50-lte-p99",
              Implies(And(P.p50_ms >= 0, P.p99_ms >= 0),
                      P.p50_ms <= P.p99_ms)),
    ]


def availability(P, *, min_uptime_pct: int = 99):
    """Uptime percentage and consecutive-error-streak constraints.

    Args:
        P:               FactNamespace.
        min_uptime_pct:  Minimum availability as integer percent (default 99).
    """
    return [
        named("reliability/uptime-above-floor",
              Implies(P.uptime_pct >= 0, P.uptime_pct >= min_uptime_pct)),
        named("reliability/uptime-is-valid-percentage",
              Implies(P.uptime_pct >= 0,
                      And(P.uptime_pct >= 0, P.uptime_pct <= 100))),
        named("reliability/no-long-error-streaks",
              Implies(P.consecutive_errors >= 0, P.consecutive_errors <= 5)),
        # High uptime implies short streaks
        named("reliability/high-uptime-limits-streak",
              Implies(And(P.uptime_pct >= min_uptime_pct, P.consecutive_errors >= 0),
                      P.consecutive_errors <= 3)),
    ]
