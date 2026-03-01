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
            Not(And(P.judge_exit_code == 0, P.judge_total_count == 0)),
            Implies(P.judge_exit_code >= 0, P.judge_exit_code == 0),
            Implies(P.judge_exit_code == 0, P.judge_output_valid),
            Implies(P.judge_exit_code == 0, P.judge_schema_correct),
            Implies(P.judge_exit_code == 0, P.judge_has_results),
            # satisfied <= total — arithmetic consistency
            Implies(P.judge_total_count >= 1, P.judge_satisfied_count <= P.judge_total_count),
            # In a well-formed judge run, at least half must satisfy
            Implies(
                And(P.judge_exit_code == 0, P.judge_total_count >= 1),
                P.judge_satisfied_count * 2 >= P.judge_total_count,
            ),
            # If judge succeeded with results, satisfied count must be positive
            Implies(
                And(P.judge_exit_code == 0, P.judge_total_count >= 1),
                P.judge_satisfied_count >= 1,
            ),

            # ── Report: must be programmatically reliable ─────────────────
            Implies(P.report_exit_code >= 0, P.report_exit_code == 0),
            Implies(P.report_exit_code == 0, P.report_file_created),
            Implies(P.report_file_created, P.report_has_doctype),
            Implies(P.report_file_created, P.report_is_self_contained),
            # A self-contained, card-bearing report must be substantive
            Implies(
                And(P.report_file_created, P.report_is_self_contained, P.report_has_cards),
                P.report_file_size_bytes >= 5000,
            ),
            # Full quality report: all three signals → larger size floor
            Implies(
                And(P.report_has_doctype, P.report_is_self_contained, P.report_has_cards),
                P.report_file_size_bytes >= 8000,
            ),

            # ── Scaffold: file count must match individual file flags ──────
            Implies(P.init_exit_code >= 0, P.init_exit_code == 0),
            Implies(P.init_exit_code == 0, P.yaml_parseable),
            # Sum of boolean file flags must equal or bound scaffold_file_count
            Implies(
                P.init_exit_code == 0,
                P.config_created + P.instrumentation_created
                + P.perceptions_created + P.user_file_created == 4,
            ),
            # file count must be at least the sum of known files
            Implies(
                P.init_exit_code == 0,
                P.scaffold_file_count >= P.config_created
                + P.instrumentation_created + P.perceptions_created
                + P.user_file_created,
            ),
            # yaml_parseable implies config_created — can't parse a missing file
            Implies(P.yaml_parseable, P.config_created),
        ]
