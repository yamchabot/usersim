"""OSS contributor adding personas/groups — needs clean extension points and good errors."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from usersim import Person
from usersim.judgement.z3_compat import Implies, And, Not, named
from constraint_library import (
    matrix_invariants,
    pipeline_invariants,
    scaffold_invariants,
    error_handling_invariants,
    report_invariants,
)


class OSSContributor(Person):
    name    = "oss_contributor"
    role    = "Open Source Contributor"
    goal    = "add new personas and paths without breaking existing ones"
    pronoun = "they"

    def constraints(self, P):
        return [
            *matrix_invariants(P),
            *pipeline_invariants(P),
            *scaffold_invariants(P),
            *error_handling_invariants(P),
            *report_invariants(P),

            # ── OSS-specific: extensibility and non-regression ────────────
            # Scaffold must produce all files a contributor needs to extend
            named("oss/scaffold-produces-extension-surface",
                  Implies(P.init_exit_code == 0, P.scaffold_file_count >= 4)),
            # All constraints must be present — contributor needs full surface
            named("oss/all-constraints-visible",
                  Implies(P.pipeline_exit_code == 0, P.all_constraints_present)),
            # Error messages must be clean (contributor sees them most)
            named("oss/error-messages-are-clean",
                  Implies(P.missing_config_exit_code == 1, P.errors_are_clean)),
            named("oss/errors-go-to-stderr",
                  Implies(P.missing_config_exit_code == 1, P.errors_use_stderr)),
            # Adding a persona must not break existing result count
            named("oss/result-count-consistent-with-persons",
                  Implies(P.results_total >= 1,
                          P.results_total == P.person_count * P.scenario_count)),
            # Report must include all persons — verifies new persona was registered
            named("oss/report-reflects-all-persons",
                  Implies(And(P.report_file_created, P.person_count >= 1),
                          P.report_file_size_bytes >= P.person_count * 400)),
            # YAML must be parseable after scaffold — contributor forks from it
            named("oss/scaffold-yaml-parseable",
                  Implies(P.init_exit_code == 0, P.yaml_parseable)),
        ]
