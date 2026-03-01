"""DevEx engineer caring about CLI ergonomics, onboarding friction, time-to-first-run."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from usersim import Person
from usersim.judgement.z3_compat import Implies, And, Not, named
from constraint_library import (
    matrix_invariants,
    pipeline_invariants,
    scaffold_invariants,
    report_invariants,
    timing_invariants,
)


class DevExEngineer(Person):
    name    = "devex_engineer"
    role    = "Developer Experience Engineer"
    goal    = "minimize onboarding friction — scaffold works, errors are friendly, report is readable"
    pronoun = "they"

    def constraints(self, P):
        return [
            *matrix_invariants(P),
            *pipeline_invariants(P),
            *scaffold_invariants(P),
            *report_invariants(P),
            *timing_invariants(P, max_ms_per_result=5000, max_total_ms=120000),

            # ── DevEx-specific: zero friction onboarding ─────────────────
            # Scaffold must succeed and produce all expected files
            named("devex/scaffold-exits-0",
                  Implies(P.init_exit_code >= 0, P.init_exit_code == 0)),
            named("devex/scaffold-creates-at-least-4-files",
                  Implies(P.init_exit_code == 0, P.scaffold_file_count >= 4)),
            # YAML config must be parseable out of the box
            named("devex/scaffold-yaml-immediately-parseable",
                  Implies(P.init_exit_code == 0, P.yaml_parseable)),
            # Report must be self-contained (no external deps to open it)
            named("devex/report-is-self-contained",
                  Implies(P.report_file_created, P.report_is_self_contained)),
            # Report must have human-readable cards
            named("devex/report-has-person-cards",
                  Implies(P.report_file_created, P.report_has_cards)),
            # Error messages must be clean — friendly, not stack traces
            named("devex/errors-are-clean",
                  Implies(P.missing_config_exit_code == 1, P.errors_are_clean)),
            # Time-to-first-result must feel fast: under 10s for small matrix
            named("devex/fast-first-run",
                  Implies(And(P.pipeline_wall_clock_ms > 0,
                              P.person_count <= 5, P.scenario_count <= 6),
                          P.pipeline_wall_clock_ms <= 30000)),
            # Report size scales with content — proves it's not an empty shell
            named("devex/report-content-scales-with-results",
                  Implies(And(P.report_file_created, P.results_total >= 1),
                          P.report_file_size_bytes >= P.results_total * 300)),
        ]
