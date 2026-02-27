from usersim.judgement.person import Person


class SensitiveWorkProfessional(Person):
    name    = "Sensitive-Work Professional"
    role    = "Lawyer / doctor / journalist"
    goal    = "Notes that stay on-device, isolated per client, with no vendor involvement"
    pronoun = "they"

    def constraints(self, P):
        return [
            P.total_request_count       == 0,
            P.typing_request_count      == 0,
            P.trust_signal_violations   == 0,
            P.auth_prompt_count         == 0,
            P.account_prompt_count      == 0,
            P.shared_notebook_key_count == 0,
            P.notebook_isolation_ratio  >= 1.0,
            P.storage_error_count       == 0,
            P.reload_loss_count         == 0,
        ]
