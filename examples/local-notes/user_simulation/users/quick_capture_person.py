from usersim.judgement.person import Person


class QuickCapturePerson(Person):
    name    = "Quick-Capture Person"
    role    = "Productivity-focused professional"
    goal    = "Capture thoughts instantly with zero friction"
    pronoun = "they"

    def constraints(self, P):
        return [
            P.arrival_friction_total  == 0,
            P.new_note_step_count     <= 2,
            P.reload_loss_count       == 0,
            P.data_integrity_rate     >= 1.0,
            P.total_note_count        >= 0,
        ]
