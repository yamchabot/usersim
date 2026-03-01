"""Developer using usersim programmatically — subcommands and schemas must be reliable."""
from usersim import Person
from usersim.judgement.z3_compat import Implies


class LibraryConsumer(Person):
    name    = "library_consumer"
    role    = "Developer using usersim as a Python library"
    goal    = "use usersim judge and report subcommands programmatically with reliable schemas"
    pronoun = "he"

    def constraints(self, P):
        return [
            # ── Judge subcommand ──────────────────────────────────────────
            Implies(P.judge_exit_code >= 0, P.judge_exit_code == 0),
            Implies(P.judge_exit_code == 0, P.judge_output_valid),
            Implies(P.judge_exit_code == 0, P.judge_schema_correct),
            Implies(P.judge_exit_code == 0, P.judge_has_results),
            # Judge must evaluate something and produce at least one satisfied result
            Implies(P.judge_exit_code == 0, P.judge_total_count >= 1),
            Implies(P.judge_total_count >= 1, P.judge_satisfied_count >= 1),

            # ── Report subcommand ─────────────────────────────────────────
            Implies(P.report_exit_code >= 0, P.report_exit_code == 0),
            Implies(P.report_exit_code == 0, P.report_file_created),
            Implies(P.report_file_created, P.report_has_doctype),
            # Report must be self-contained (no external deps to break programmatic use)
            Implies(P.report_file_created, P.report_is_self_contained),
            # Report must be non-trivially sized
            Implies(P.report_file_created, P.report_file_size_bytes >= 5000),

            # ── Init scaffold ─────────────────────────────────────────────
            Implies(P.init_exit_code >= 0, P.init_exit_code == 0),
            Implies(P.init_exit_code == 0, P.yaml_parseable),
            Implies(P.init_exit_code == 0, P.scaffold_file_count >= 4),
            # All four key files must exist
            Implies(P.init_exit_code == 0, P.config_created),
            Implies(P.init_exit_code == 0, P.instrumentation_created),
            Implies(P.init_exit_code == 0, P.perceptions_created),
            Implies(P.init_exit_code == 0, P.user_file_created),
        ]
