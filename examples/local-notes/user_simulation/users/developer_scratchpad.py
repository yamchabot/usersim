from usersim.judgement.person import Person
from usersim.judgement.z3_compat import Implies, named


class DeveloperScratchpad(Person):
    name    = "Developer Scratchpad"
    role    = "Software developer"
    goal    = "Safe, organised scratchpad for sensitive work content"
    pronoun = "they"

    def constraints(self, P):
        return [
            # privacy
            named("privacy/no-outbound-requests",  P.total_request_count == 0),
            named("privacy/no-typing-telemetry",   P.typing_request_count == 0),
            named("privacy/search-stays-local",
                  Implies(P.search_hit_count + P.search_miss_count >= 1,
                          P.search_request_count == 0)),
            named("privacy/bulk-stays-local",
                  Implies(P.session_note_create_count >= 5, P.outbound_request_count == 0)),

            # isolation
            named("isolation/no-shared-keys",        P.shared_notebook_key_count == 0),
            named("isolation/notebook-ratio-correct", P.notebook_isolation_ratio >= 1.0),

            # correctness
            named("correctness/recency-order",    P.recency_violation_count == 0),
            named("correctness/no-reload-loss",   P.reload_loss_count == 0),
            named("correctness/offline-resilient", P.offline_failure_count == 0),
            named("correctness/search-finds-results",
                  Implies(P.search_hit_count + P.search_miss_count >= 1,
                          P.search_hit_count >= 1)),
        ]
