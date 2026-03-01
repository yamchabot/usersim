"""
usersim.constraints.retention — session depth and return-rate quality.

Perceptions contract:
  session_actions       (int >= 0)  — actions taken in current session
  sessions_total        (int >= 0)  — total sessions observed
  sessions_returned     (int >= 0)  — sessions that came back (D1/D7/D30)
  task_completion_pct   (int 0-100) — percentage of started tasks completed
  bounce_count          (int >= 0)  — single-action (bounced) sessions
  depth_p50             (int >= 0)  — median session depth (actions)
  depth_p90             (int >= 0)  — 90th-percentile session depth
"""
from usersim.judgement.z3_compat import And, Implies, Not, named


def session_depth(P, *, min_p50: int = 3, min_p90: int = 8, max_bounce_pct: int = 30):
    """Session depth and bounce rate constraints.

    Args:
        P:             FactNamespace.
        min_p50:       Minimum median session depth (default 3 actions).
        min_p90:       Minimum 90th-pct session depth (default 8 actions).
        max_bounce_pct: Maximum single-action bounce rate as integer % (default 30%).
    """
    return [
        named("retention/median-depth-above-floor",
              Implies(P.depth_p50 >= 0, P.depth_p50 >= min_p50)),
        named("retention/p90-depth-above-floor",
              Implies(P.depth_p90 >= 0, P.depth_p90 >= min_p90)),
        named("retention/p50-lte-p90",
              Implies(And(P.depth_p50 >= 0, P.depth_p90 >= 0),
                      P.depth_p50 <= P.depth_p90)),
        named("retention/bounce-rate-under-ceiling",
              Implies(And(P.sessions_total >= 1, P.bounce_count >= 0),
                      P.bounce_count * 100 <= P.sessions_total * max_bounce_pct)),
        named("retention/bounce-never-exceeds-sessions",
              Implies(P.sessions_total >= 0,
                      P.bounce_count <= P.sessions_total)),
        named("retention/task-completion-is-percentage",
              Implies(P.task_completion_pct >= 0,
                      And(P.task_completion_pct >= 0, P.task_completion_pct <= 100))),
    ]


def return_rate(P, *, min_return_pct: int = 20):
    """Return visit rate: sessions_returned / sessions_total >= min_return_pct/100.

    Integer form: sessions_returned * 100 >= sessions_total * min_return_pct

    Args:
        P:               FactNamespace.
        min_return_pct:  Minimum return rate as integer percent (default 20%).
    """
    return [
        named("retention/return-rate-above-floor",
              Implies(P.sessions_total >= 1,
                      P.sessions_returned * 100 >= P.sessions_total * min_return_pct)),
        named("retention/returned-never-exceeds-total",
              Implies(P.sessions_total >= 0,
                      P.sessions_returned <= P.sessions_total)),
        named("retention/no-returns-without-sessions",
              Implies(P.sessions_total == 0, P.sessions_returned == 0)),
        # Deep sessions correlate with returns: high p90 depth → expect some returns
        named("retention/deep-sessions-imply-some-returns",
              Implies(And(P.depth_p90 >= 10, P.sessions_total >= 5),
                      P.sessions_returned >= 1)),
    ]
