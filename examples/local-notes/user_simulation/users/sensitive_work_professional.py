from usersim.judgement.person import Person
from usersim.judgement.z3_compat import Implies, named


class SensitiveWorkProfessional(Person):
    name    = "Sensitive-Work Professional"
    role    = "Lawyer / doctor / journalist"
    goal    = "Notes that stay on-device, isolated per client, with no vendor involvement"
    pronoun = "they"

    def constraints(self, P):
        return [
            # privacy
            named("privacy/no-outbound-requests",  P.total_request_count == 0),
            named("privacy/no-typing-telemetry",   P.typing_request_count == 0),
            named("privacy/zero-trust-violations", P.trust_signal_violations == 0),
            named("privacy/no-auth-prompts",       P.auth_prompt_count == 0),
            named("privacy/no-account-prompts",    P.account_prompt_count == 0),
            named("privacy/no-vendor-code",        P.vendor_surface == 0),
            named("privacy/search-stays-local",
                  Implies(P.search_hit_count + P.search_miss_count >= 1,
                          P.search_request_count == 0)),

            # isolation
            named("isolation/no-shared-keys",        P.shared_notebook_key_count == 0),
            named("isolation/notebook-ratio-correct", P.notebook_isolation_ratio >= 1.0),
            named("isolation/bulk-no-cross-contamination",
                  Implies(P.session_note_create_count >= 5, P.shared_notebook_key_count == 0)),

            # persistence
            named("persistence/no-storage-errors", P.storage_error_count == 0),
            named("persistence/no-reload-loss",    P.reload_loss_count == 0),
            named("persistence/search-finds-client-notes",
                  Implies(P.search_hit_count + P.search_miss_count >= 1,
                          P.search_hit_count >= 1)),
            named("persistence/bulk-data-integrity",
                  Implies(P.session_note_create_count >= 5, P.data_integrity_rate >= 1.0)),
        ]
