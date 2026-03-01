from usersim.judgement.person import Person
from usersim.judgement.z3_compat import Implies


class PrivacyFirstUser(Person):
    name    = "Privacy-First User"
    role    = "Privacy-conscious individual"
    goal    = "Use a notes app that never transmits data externally"
    pronoun = "they"

    def constraints(self, P):
        return [
            # Always: zero network exposure
            P.total_request_count    == 0,
            P.typing_request_count   == 0,
            P.trust_signal_violations == 0,
            P.vendor_surface         == 0,
            P.auth_prompt_count      == 0,
            P.account_prompt_count   == 0,
            P.storage_error_count    == 0,
            P.data_integrity_rate    >= 1.0,

            # search_heavy: searching must not leak query text externally
            Implies(P.search_hit_count + P.search_miss_count >= 1,
                    P.search_request_count == 0),

            # bulk_import: mass creation must stay offline
            Implies(P.session_note_create_count >= 5,
                    P.outbound_request_count == 0),

            # bulk_import: all created notes survive (no silent data loss)
            Implies(P.session_note_create_count >= 5,
                    P.data_integrity_rate >= 1.0),
        ]
