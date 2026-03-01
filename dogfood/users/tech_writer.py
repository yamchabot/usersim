"""Technical writer who needs to understand and document the system clearly."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from usersim import Person
from usersim.judgement.z3_compat import Implies, And, Not, named
from constraint_library import (
    matrix_invariants,
    pipeline_invariants,
    scaffold_invariants,
    report_invariants,
)


class TechWriter(Person):
    name    = "tech_writer"
    role    = "Technical Writer"
    goal    = "understand output well enough to write clear documentation"
    pronoun = "she"

    def constraints(self, P):
        return [
            *matrix_invariants(P),
            *pipeline_invariants(P),
            *scaffold_invariants(P),
            *report_invariants(P),

            # ── Tech-writer-specific: clarity and self-documentation ──────
            # Report must have DOCTYPE — basic HTML validity for docs embedding
            named("docs/report-has-doctype",
                  Implies(P.report_file_created, P.report_has_doctype)),
            # Report must be self-contained — copy-paste into docs works
            named("docs/report-is-self-contained",
                  Implies(P.report_file_created, P.report_is_self_contained)),
            # Report must have person cards — the core explainable unit
            named("docs/report-has-explainable-cards",
                  Implies(P.report_file_created, P.report_has_cards)),
            # Scaffold YAML must be parseable — writer reads it to document format
            named("docs/scaffold-yaml-is-readable",
                  Implies(P.init_exit_code == 0, P.yaml_parseable)),
            # Error messages must be clean — writer quotes them in docs
            named("docs/error-messages-quotable",
                  Implies(P.missing_config_exit_code == 1, P.errors_are_clean)),
            # All constraints must be present — writer needs to enumerate them
            named("docs/all-constraints-enumerable",
                  Implies(P.pipeline_exit_code == 0, P.all_constraints_present)),
            # Report size must reflect content depth (not a stub)
            named("docs/report-is-substantive",
                  Implies(And(P.report_file_created, P.person_count >= 1,
                              P.scenario_count >= 1),
                          P.report_file_size_bytes
                          >= P.person_count * P.scenario_count * 150)),
            # Schema correctness required — writer documents the schema
            named("docs/output-schema-documentable",
                  Implies(P.pipeline_exit_code == 0, P.schema_is_correct)),
        ]
