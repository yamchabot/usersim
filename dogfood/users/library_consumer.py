"""Developer using usersim programmatically — subcommands and schemas must be reliable."""
from usersim import Person
from usersim.judgement.z3_compat import Implies, And, Not


class LibraryConsumer(Person):
    name    = "library_consumer"
    role    = "Developer using usersim as a Python library"
    goal    = "use usersim judge and report subcommands programmatically with reliable schemas"
    pronoun = "he"

    def constraints(self, P):
        return [
            # ── Judge: structural invariants ──────────────────────────────
            # Exit 0 with nothing evaluated is a silent failure
            Not(And(P.judge_exit_code == 0, P.judge_total_count == 0)),
            # satisfied can never exceed total — arithmetic consistency
            Implies(P.judge_total_count >= 1, P.judge_satisfied_count <= P.judge_total_count),
            # At least one persona must be satisfied in any valid judge run
            Implies(P.judge_total_count >= 1, P.judge_satisfied_count >= 1),
            # Schema and output must be machine-reliable
            Implies(P.judge_exit_code == 0, P.judge_output_valid),
            Implies(P.judge_exit_code == 0, P.judge_schema_correct),
            Implies(P.judge_exit_code == 0, P.judge_has_results),
            # Programmatic users require exact exit 0 — not just non-negative
            Implies(P.judge_exit_code >= 0, P.judge_exit_code == 0),

            # ── Report: structural invariants ─────────────────────────────
            Implies(P.report_exit_code >= 0, P.report_exit_code == 0),
            Implies(P.report_exit_code == 0, P.report_file_created),
            Implies(P.report_file_created, P.report_has_doctype),
            Implies(P.report_file_created, P.report_is_self_contained),
            # Report must be non-trivially sized (anything under 5KB is a stub)
            Implies(P.report_file_created, P.report_file_size_bytes >= 5000),

            # ── Scaffold: all files must be individually present ──────────
            Implies(P.init_exit_code >= 0, P.init_exit_code == 0),
            Implies(P.init_exit_code == 0, P.config_created),
            Implies(P.init_exit_code == 0, P.instrumentation_created),
            Implies(P.init_exit_code == 0, P.perceptions_created),
            Implies(P.init_exit_code == 0, P.user_file_created),
            Implies(P.init_exit_code == 0, P.yaml_parseable),
            # File count must match the individual file flags — count can't lie
            Implies(
                And(P.config_created, P.instrumentation_created,
                    P.perceptions_created, P.user_file_created),
                P.scaffold_file_count >= 4,
            ),
        ]
