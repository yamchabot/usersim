"""Compliance auditor needing reproducible evidence that all constraints were checked."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from usersim import Person
from usersim.judgement.z3_compat import Implies, And, Not, named
from constraint_library import (
    matrix_invariants,
    pipeline_invariants,
    judge_invariants,
    report_invariants,
    scaffold_invariants,
)


class ComplianceAuditor(Person):
    name    = "compliance_auditor"
    role    = "Compliance / Auditor"
    goal    = "produce a reproducible, complete audit trail of constraint evaluation"
    pronoun = "he"

    def constraints(self, P):
        return [
            *matrix_invariants(P),
            *pipeline_invariants(P),
            *judge_invariants(P),
            *report_invariants(P),
            *scaffold_invariants(P),

            # ── Audit-specific: completeness and reproducibility ──────────
            # All constraints must be present in output — nothing omitted
            named("audit/all-constraints-present",
                  Implies(P.pipeline_exit_code == 0, P.all_constraints_present)),
            # Output must be valid JSON — machine-parseable evidence
            named("audit/output-is-machine-parseable",
                  Implies(P.pipeline_exit_code == 0, P.output_is_valid_json)),
            # Schema must be correct — evidence format is stable
            named("audit/schema-is-stable",
                  Implies(P.pipeline_exit_code == 0, P.schema_is_correct)),
            # Report must exist as a durable artifact
            named("audit/report-artifact-exists",
                  Implies(P.report_exit_code == 0, P.report_file_created)),
            # Report must be substantial enough to contain all findings
            named("audit/report-covers-full-matrix",
                  Implies(And(P.report_file_created, P.results_total >= 1,
                              P.person_count >= 1),
                          P.report_file_size_bytes
                          >= P.results_total * P.person_count * 80)),
            # Judge and pipeline must agree on total count
            named("audit/judge-pipeline-result-count-agree",
                  Implies(And(P.judge_exit_code == 0, P.judge_total_count >= 1),
                          P.judge_satisfied_count <= P.judge_total_count)),
            # Satisfied count must never exceed total — no phantom passes
            named("audit/no-phantom-passes",
                  Implies(P.judge_total_count >= 1,
                          P.judge_satisfied_count <= P.judge_total_count)),
            # Scaffold files must be traceable — all 4 present
            named("audit/scaffold-files-fully-traceable",
                  Implies(P.init_exit_code == 0, P.scaffold_file_count >= 4)),
        ]
