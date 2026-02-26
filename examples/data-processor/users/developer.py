"""
Developer using the processor interactively in a script or REPL.
Calls sort/search/summarise on their own datasets and expects the
operations to feel responsive.  Any errors break their workflow.
"""
from usersim import Person


class Developer(Person):
    name        = "developer"
    description = "Interactive use; needs operations to feel responsive."

    def constraints(self, P):
        return [
            P.error_rate  <= 0.0,       # any error is a blocker
            P.sort_ms     <= 1_000,     # sort should finish in under a second
            P.search_ms   <= 2_000,     # search can be a little slower
            P.summary_ms  <= 5_000,     # aggregation has most slack
            P.search_returned_results,  # search must actually find things
        ]
