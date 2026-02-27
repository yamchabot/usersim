from usersim.judgement.person import Person


class BloatHater(Person):
    name    = "Bloat-Hater"
    role    = "Minimalist power user"
    goal    = "A notes tool that does exactly what it says and nothing else"
    pronoun = "they"

    def constraints(self, P):
        return [
            P.arrival_friction_total    == 0,
            P.new_note_step_count       <= 2,
            P.vendor_surface            == 0,
            P.external_dependency_count == 0,
            P.load_request_count        == 0,
            P.interactive_element_count <= 15,
        ]
