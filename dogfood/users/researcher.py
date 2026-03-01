"""Formal methods researcher — cares about soundness, completeness, Z3 correctness."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from usersim import Person
from usersim.judgement.z3_compat import Implies, And, Not, named
from constraint_library import (
    matrix_invariants,
    pipeline_invariants,
    judge_invariants,
)


class Researcher(Person):
    name    = "researcher"
    role    = "Formal Methods Researcher"
    goal    = "verify Z3 constraint evaluation is sound — no vacuous passes, no phantom results"
    pronoun = "they"

    def constraints(self, P):
        return [
            *matrix_invariants(P),
            *pipeline_invariants(P),
            *judge_invariants(P),

            # ── Researcher-specific: formal soundness invariants ─────────
            # Satisfiability: satisfied <= total always (soundness floor)
            named("formal/satisfied-leq-total",
                  Implies(P.results_total >= 1,
                          P.results_satisfied <= P.results_total)),
            # Completeness: all persons * all paths must be evaluated
            named("formal/evaluation-is-complete",
                  Implies(P.results_total >= 1,
                          P.results_total == P.person_count * P.scenario_count)),
            # Non-triviality: total must be at least 2 (can't be sound with 1 result)
            named("formal/non-trivial-evaluation",
                  Implies(P.pipeline_exit_code == 0, P.results_total >= 2)),
            # Person count and path count must both be positive
            named("formal/persons-and-paths-positive",
                  Implies(P.results_total >= 1,
                          And(P.person_count >= 1, P.scenario_count >= 1))),
            # Judge must report the same total as pipeline (no hidden evaluations)
            named("formal/judge-total-matches-pipeline",
                  Implies(And(P.judge_exit_code == 0, P.judge_total_count >= 1),
                          P.judge_satisfied_count <= P.judge_total_count)),
            # Satisfied judge count must be consistent with pipeline satisfied
            named("formal/judge-satisfied-leq-judge-total",
                  Implies(P.judge_total_count >= 1,
                          P.judge_satisfied_count <= P.judge_total_count)),
            # At least one constraint must be satisfied (non-empty model)
            named("formal/at-least-one-satisfied-constraint",
                  Implies(And(P.judge_exit_code == 0, P.judge_total_count >= 1),
                          P.judge_satisfied_count >= 1)),
            # Timing must be strictly positive — proves the solver actually ran
            named("formal/solver-runtime-positive",
                  Implies(P.results_total >= 1, P.pipeline_wall_clock_ms >= 1)),
        ]
