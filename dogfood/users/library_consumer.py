"""Developer using usersim programmatically — subcommands and schemas must be reliable."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from usersim import Person
from usersim.judgement.z3_compat import Implies, And, Not, named
from constraint_library import (
    scaffold_invariants,
    judge_invariants,
    report_invariants,
)


class LibraryConsumer(Person):
    name    = "library_consumer"
    role    = "Developer using usersim as a Python library"
    goal    = "use usersim judge and report subcommands programmatically with reliable schemas"
    pronoun = "he"

    def constraints(self, P):
        return [
            *scaffold_invariants(P),
            *judge_invariants(P),
            *report_invariants(P),

            # ── Library-consumer-specific ─────────────────────────────────
            # Programmatic users need exact exit 0, not just non-negative
            named("library/judge-exits-exactly-0",
                  Implies(P.judge_exit_code >= 0, P.judge_exit_code == 0)),
            named("library/report-exits-exactly-0",
                  Implies(P.report_exit_code >= 0, P.report_exit_code == 0)),
            named("library/scaffold-exits-exactly-0",
                  Implies(P.init_exit_code >= 0, P.init_exit_code == 0)),
            # All four scaffold files must be present — no missing pieces
            named("library/all-scaffold-files-present",
                  Implies(P.init_exit_code == 0,
                          P.config_created + P.instrumentation_created
                          + P.perceptions_created + P.user_file_created == 4)),
            # Judge satisfied count must be the full set for a well-formed test run
            named("library/judge-full-pass",
                  Implies(And(P.judge_exit_code == 0, P.judge_total_count >= 1),
                          P.judge_satisfied_count == P.judge_total_count)),
        ]
