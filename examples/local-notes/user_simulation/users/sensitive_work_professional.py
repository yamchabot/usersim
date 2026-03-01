from usersim.judgement.person import Person
from usersim.judgement.z3_compat import Implies


class SensitiveWorkProfessional(Person):
    name    = "Sensitive-Work Professional"
    role    = "Lawyer / doctor / journalist"
    goal    = "Notes that stay on-device, isolated per client, with no vendor involvement"
    pronoun = "they"

    def constraints(self, P):
        return [
            # Always: total isolation, nothing leaves the device
            P.total_request_count       == 0,
            P.typing_request_count      == 0,
            P.trust_signal_violations   == 0,
            P.auth_prompt_count         == 0,
            P.account_prompt_count      == 0,
            P.shared_notebook_key_count == 0,
            P.notebook_isolation_ratio  >= 1.0,
            P.storage_error_count       == 0,
            P.reload_loss_count         == 0,
            P.vendor_surface            == 0,

            # search_heavy: search is local-only — no queries leave the device
            Implies(P.search_hit_count + P.search_miss_count >= 1,
                    P.search_request_count == 0),

            # search_heavy: must return results for known queries
            Implies(P.search_hit_count + P.search_miss_count >= 1,
                    P.search_hit_count >= 1),

            # bulk_import: client notes must not intermix across notebooks
            Implies(P.session_note_create_count >= 5,
                    P.shared_notebook_key_count == 0),

            # bulk_import: all notes must persist correctly
            Implies(P.session_note_create_count >= 5,
                    P.data_integrity_rate >= 1.0),
        ]
