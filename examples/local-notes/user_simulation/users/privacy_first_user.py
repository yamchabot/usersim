from usersim.judgement.person import Person


class PrivacyFirstUser(Person):
    name    = "Privacy-First User"
    role    = "Privacy-conscious individual"
    goal    = "Use a notes app that never transmits data externally"
    pronoun = "they"

    def constraints(self, P):
        return [
            P.total_request_count    == 0,
            P.typing_request_count   == 0,
            P.trust_signal_violations == 0,
            P.vendor_surface         == 0,
            P.auth_prompt_count      == 0,
            P.account_prompt_count   == 0,
            P.storage_error_count    == 0,
            P.data_integrity_rate    >= 1.0,
        ]
