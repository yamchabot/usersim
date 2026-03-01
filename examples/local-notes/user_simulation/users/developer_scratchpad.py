from usersim.judgement.person import Person
from usersim.judgement.z3_compat import Implies


class DeveloperScratchpad(Person):
    name    = "Developer Scratchpad"
    role    = "Software developer"
    goal    = "Safe, organised scratchpad for sensitive work content"
    pronoun = "they"

    def constraints(self, P):
        return [
            # Always: no data leaves the device
            P.total_request_count        == 0,
            P.typing_request_count       == 0,
            P.shared_notebook_key_count  == 0,
            P.notebook_isolation_ratio   >= 1.0,
            P.recency_violation_count    == 0,
            P.reload_loss_count          == 0,
            P.offline_failure_count      == 0,

            # search_heavy: searching must not trigger any outbound requests
            Implies(P.search_hit_count + P.search_miss_count >= 1,
                    P.search_request_count == 0),

            # search_heavy: at least one query must return results (app actually searches)
            Implies(P.search_hit_count + P.search_miss_count >= 1,
                    P.search_hit_count >= 1),

            # bulk_import: no network activity during mass creation
            Implies(P.session_note_create_count >= 5,
                    P.outbound_request_count == 0),
        ]
