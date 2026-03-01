from usersim.judgement.person import Person
from usersim.judgement.z3_compat import Implies


class BloatHater(Person):
    name    = "Bloat-Hater"
    role    = "Minimalist power user"
    goal    = "A notes tool that does exactly what it says and nothing else"
    pronoun = "they"

    def constraints(self, P):
        return [
            # Always: lean, no external code
            P.arrival_friction_total    == 0,
            P.new_note_step_count       <= 2,
            P.vendor_surface            == 0,
            P.external_dependency_count == 0,
            P.load_request_count        == 0,
            P.interactive_element_count <= 15,

            # search_heavy: search exists and works (feature earns its place)
            Implies(P.search_hit_count + P.search_miss_count >= 1,
                    P.search_hit_count >= 1),

            # search_heavy: no extra resources loaded for search
            Implies(P.search_hit_count + P.search_miss_count >= 1,
                    P.external_resource_count == 0),

            # bulk_import: zero storage errors even under load
            Implies(P.session_note_create_count >= 5,
                    P.storage_error_count == 0),
        ]
