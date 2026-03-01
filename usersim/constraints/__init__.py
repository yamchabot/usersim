"""
usersim.constraints — pre-built domain constraint modules.

Each module provides named constraint groups for a specific domain.
Persona authors import groups and compose them with persona-specific logic.

Available modules:
  from usersim.constraints.reliability  import error_rate, latency, availability
  from usersim.constraints.throughput   import throughput_floor, queue_depth
  from usersim.constraints.search       import recall, precision, result_count
  from usersim.constraints.retention    import session_depth, return_rate
  from usersim.constraints.privacy      import data_exposure, consent, audit_trail
  from usersim.constraints.cli          import exit_codes, output_format, timing

Usage pattern:

    from usersim.constraints.reliability import error_rate, latency
    from usersim.judgement.z3_compat import named, Implies

    class MyUser:
        def constraints(self, P):
            return [
                *error_rate(P),            # error_total / request_total <= 0.01
                *latency(P, p99_ms=500),   # p99 under threshold
                named("my/custom-check",
                      Implies(P.requests > 100, P.cache_hit_rate >= 50)),
            ]

Constraint naming follows "domain/check-name" convention. Groups accept
a FactNamespace (P) and optional threshold overrides.
"""

from usersim.constraints.reliability import error_rate, latency, availability
from usersim.constraints.throughput  import throughput_floor, queue_depth
from usersim.constraints.search      import recall, precision, result_count
from usersim.constraints.retention   import session_depth, return_rate
from usersim.constraints.privacy     import data_exposure, consent, audit_trail
from usersim.constraints.cli         import exit_codes, output_format, timing

__all__ = [
    "error_rate", "latency", "availability",
    "throughput_floor", "queue_depth",
    "recall", "precision", "result_count",
    "session_depth", "return_rate",
    "data_exposure", "consent", "audit_trail",
    "exit_codes", "output_format", "timing",
]
