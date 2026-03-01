"""
Person base class.

Each simulated user is a Python class that extends Person and implements
`constraints()`.  The method receives a `facts` namespace where each key in
the perceptions.json "facts" object is accessible as an attribute.

Example
-------
from usersim import Person
from usersim.judgement.z3_compat import And, Implies

class SeniorEngineer(Person):
    name        = "senior_engineer"
    description = "Experienced dev who needs to understand call-site impact quickly."

    def constraints(self, P):
        # P.some_fact is a Z3 Bool variable
        return [
            P.layout_is_clear,
            Implies(P.is_large_graph, P.has_visible_clusters),
        ]
"""


class FactNamespace:
    """
    Wraps a dict of {name → Z3_Bool} so person files can write
    `P.understands_structure` instead of `facts["understands_structure"]`.
    """
    def __init__(self, fact_vars: dict):
        self._vars = fact_vars

    def __getattr__(self, name: str):
        try:
            return self._vars[name]
        except KeyError:
            # Return a sentinel expression that evaluates to -1 (unobserved).
            # Constraints gated with Implies(P.x >= 0, ...) will be vacuously
            # true when x == -1, so library functions safely reference facts
            # that are absent from a given perceptions dict.
            from usersim.judgement.z3_compat import IntVal
            return IntVal(-1)

    def __repr__(self):
        return f"Facts({sorted(self._vars.keys())})"


class Person:
    """
    Base class for simulated users.

    Subclass this and implement `constraints(self, P)`.
    `P` is a FactNamespace — access facts as attributes (P.fact_name).
    Return a list of Z3 expressions; if all are satisfiable the user is
    considered "satisfied" for that scenario.
    """

    name:        str = ""
    description: str = ""
    role:        str = ""   # job title shown in reports
    goal:        str = ""   # what this person wants to accomplish
    pronoun:     str = "they"  # he / she / they

    def constraints(self, P: FactNamespace) -> list:
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement constraints(self, P)."
        )

    def __repr__(self):
        return f"Person(name={self.name!r})"
