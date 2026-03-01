"""User who demands low error rate, fast responses, and no data loss."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from usersim import Person
from usersim.judgement.z3_compat import Implies, And, named

class ReliabilityUser(Person):
    name    = "reliability_user"
    role    = "End User"
    goal    = "app must be reliable — low errors, fast, no data loss"
    pronoun = "they"

    def constraints(self, P):
        return [
            # Error rate: errors must be < 10% of requests
            named("reliability/error-rate-under-10pct",
                  Implies(P.request_count >= 1,
                          P.error_count * 10 <= P.request_count)),
            # Latency: p99 must be under 1000ms
            named("reliability/p99-under-1s",
                  Implies(P.request_count >= 1,
                          P.p99_latency_ms <= 1000)),
            # Data integrity: no data loss ever
            named("reliability/no-data-loss",
                  P.data_loss_count == 0),
            # Conservation: can't have more errors than requests
            named("reliability/errors-bounded-by-requests",
                  P.error_count <= P.request_count),
        ]
