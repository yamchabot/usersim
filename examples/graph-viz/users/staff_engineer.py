"""
Staff Engineer — deep technical user who needs call-site precision.
High expectations for layout quality and structural accuracy.
"""
from usersim import Person
from usersim.judgement.z3_compat import And, Implies


class StaffEngineer(Person):
    name        = "staff_engineer"
    description = "Needs to trace call chains and identify coupling hotspots."

    def constraints(self, P):
        return [
            # Layout must be clear enough to trace paths
            P.layout_is_clear,
            # Hubs should be visually centred (not buried in corners)
            P.hubs_are_centred,
            # Can follow chains when they exist
            Implies(P.can_follow_chains, P.layout_is_clear),
            # Edge routing shouldn't cross module boundaries needlessly
            Implies(P.is_multi_module, P.edges_route_cleanly),
            # Crossing edges are a serious problem for this user
            P.few_crossings,
        ]
