from usersim.judgement.person import Person
from usersim.judgement.z3_compat import Implies, named


class PrivacyFirstUser(Person):
    name    = "Privacy-First User"
    role    = "Privacy-conscious individual"
    goal    = "Use a notes app that never transmits data externally"
    pronoun = "they"

    def constraints(self, P):
        return [
            # privacy
            named("privacy/no-outbound-requests",  P.total_request_count == 0),
            named("privacy/no-typing-telemetry",   P.typing_request_count == 0),
            named("privacy/zero-trust-violations", P.trust_signal_violations == 0),
            named("privacy/no-vendor-code",        P.vendor_surface == 0),
            named("privacy/no-auth-prompts",       P.auth_prompt_count == 0),
            named("privacy/no-account-prompts",    P.account_prompt_count == 0),
            named("privacy/search-stays-local",
                  Implies(P.search_hit_count + P.search_miss_count >= 1,
                          P.search_request_count == 0)),
            named("privacy/bulk-stays-local",
                  Implies(P.session_note_create_count >= 5, P.outbound_request_count == 0)),

            # persistence
            named("persistence/no-storage-errors", P.storage_error_count == 0),
            named("persistence/data-integrity",    P.data_integrity_rate >= 1.0),
            named("persistence/bulk-no-data-loss",
                  Implies(P.session_note_create_count >= 5, P.data_integrity_rate >= 1.0)),
        ]
