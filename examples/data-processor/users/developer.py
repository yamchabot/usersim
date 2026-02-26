"""
Developer using the processor interactively in a script or REPL.
They call sort/search/summarise on their own datasets.
Expects operations to feel responsive — waiting more than a second
is annoying, and anything over 10s is a blocker.
"""
from usersim import Person


class Developer(Person):
    name        = "developer"
    description = "Uses the processor interactively; expects fast, responsive operations."

    def constraints(self, P):
        return [
            P.no_errors,
            P.sort_is_acceptable,      # sort under 1s
            P.search_is_acceptable,    # search under 2s
            P.summary_is_acceptable,   # summary under 5s
            P.search_returns_results,  # search must actually find things
        ]
