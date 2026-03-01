"""User who demands low error rate, fast responses, and no data loss."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from usersim import Person
from usersim.judgement.z3_compat import Implies, named

class ReliabilityUser(Person):
    name    = "reliability_user"
    role    = "End User"
    goal    = "app must be reliable — low errors, fast, no data loss"
    pronoun = "they"

    def constraints(self, P):
        return [
            named("reliability/error-rate-under-10pct",
                  Implies(P.request_count >= 1,
                          P.error_count * 10 <= P.request_count)),
            named("reliability/p99-under-1s",
                  Implies(P.request_count >= 1,
                          P.p99_latency_ms <= 1000)),
            named("reliability/no-data-loss",
                  P.data_loss_count == 0),
            named("reliability/errors-bounded-by-requests",
                  P.error_count <= P.request_count),
        ]
