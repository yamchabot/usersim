from usersim.judgement.person import Person


class DeveloperScratchpad(Person):
    name    = "Developer Scratchpad"
    role    = "Software developer"
    goal    = "Safe, organised scratchpad for sensitive work content"
    pronoun = "they"

    def constraints(self, P):
        return [
            P.total_request_count        == 0,
            P.typing_request_count       == 0,
            P.shared_notebook_key_count  == 0,
            P.notebook_isolation_ratio   >= 1.0,
            P.recency_violation_count    == 0,
            P.reload_loss_count          == 0,
            P.offline_failure_count      == 0,
        ]
