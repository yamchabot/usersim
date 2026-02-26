"""
CTO — needs architectural clarity at a glance.
Tolerates visual complexity as long as the big picture is readable.
"""
from usersim import Person
from usersim.judgement.z3_compat import And, Implies


class CTO(Person):
    name        = "cto"
    description = "Needs to understand module dependencies and risk areas quickly."

    def constraints(self, P):
        return [
            # Must be able to tell modules apart
            Implies(P.is_multi_module, P.blobs_are_separated),
            # Large graphs must at least be navigable
            Implies(P.graph_is_large, P.clusters_visible),
            # Doesn't demand pixel-perfect layouts, just no spaghetti
            P.no_spaghetti,
        ]
