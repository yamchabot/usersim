from usersim.judgement.person import Person
from usersim.judgement.z3_compat import Implies, named


class BloatHater(Person):
    name    = "Bloat-Hater"
    role    = "Minimalist power user"
    goal    = "A notes tool that does exactly what it says and nothing else"
    pronoun = "they"

    def constraints(self, P):
        return [
            # friction
            named("friction/zero-arrival-barriers", P.arrival_friction_total == 0),
            named("friction/minimal-steps-to-note", P.new_note_step_count <= 2),

            # footprint
            named("footprint/no-vendor-dependencies", P.vendor_surface == 0),
            named("footprint/no-external-deps",       P.external_dependency_count == 0),
            named("footprint/no-load-requests",       P.load_request_count == 0),
            named("footprint/ui-element-count",       P.interactive_element_count <= 15),
            named("footprint/search-no-extra-resources",
                  Implies(P.search_hit_count + P.search_miss_count >= 1,
                          P.external_resource_count == 0)),

            # correctness
            named("correctness/search-finds-results",
                  Implies(P.search_hit_count + P.search_miss_count >= 1,
                          P.search_hit_count >= 1)),
            named("correctness/bulk-no-storage-errors",
                  Implies(P.session_note_create_count >= 5, P.storage_error_count == 0)),
        ]
