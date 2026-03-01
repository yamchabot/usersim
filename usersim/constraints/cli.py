"""
usersim.constraints.cli — exit codes, output format, and timing for CLI tools.

Perceptions contract:
  exit_code         (int)        — process exit code (-1 = not observed)
  stdout_bytes      (int >= 0)   — length of stdout output
  stderr_bytes      (int >= 0)   — length of stderr output
  wall_clock_ms     (int >= 0)   — total elapsed time in milliseconds
  output_valid_json (bool)       — stdout is parseable JSON
  has_error_message (bool)       — error message present (on failure paths)
  traceback_present (bool)       — raw traceback leaked to output

These are the most commonly reused constraints across any CLI-based project.
They encode the de facto contract for well-behaved Unix command-line tools.
"""
from usersim.judgement.z3_compat import And, Implies, Not, named


def exit_codes(P):
    """Standard Unix exit code contract: 0 = success, 1 = user error, 2 = usage."""
    return [
        # Success path
        named("cli/exit-0-means-success",
              Implies(P.exit_code == 0, Not(P.has_error_message))),
        # Error path: exit 1 for recoverable errors
        named("cli/exit-1-on-user-error",
              Implies(And(P.exit_code >= 0, P.exit_code != 0),
                      P.has_error_message)),
        # No tracebacks ever
        named("cli/no-traceback-on-success",
              Implies(P.exit_code == 0, Not(P.traceback_present))),
        named("cli/no-traceback-on-error",
              Not(P.traceback_present)),
        # Stderr routing: errors go to stderr, not stdout
        named("cli/errors-route-to-stderr",
              Implies(And(P.exit_code != 0, P.exit_code >= 0),
                      P.stderr_bytes >= 1)),
        named("cli/stderr-not-polluted-on-success",
              Implies(P.exit_code == 0, P.stderr_bytes == 0)),
    ]


def output_format(P):
    """Output format constraints: valid JSON on success, nothing extra on errors."""
    return [
        named("cli/success-produces-valid-json",
              Implies(P.exit_code == 0, P.output_valid_json)),
        named("cli/success-produces-output",
              Implies(P.exit_code == 0, P.stdout_bytes >= 1)),
        named("cli/error-path-empty-stdout",
              Implies(And(P.exit_code >= 0, P.exit_code != 0),
                      P.stdout_bytes == 0)),
        named("cli/valid-json-implies-output-present",
              Implies(P.output_valid_json, P.stdout_bytes >= 2)),
    ]


def timing(P, *, max_ms: int = 10000, min_ms: int = 1):
    """Wall-clock time bounded and non-trivial when output produced.

    Args:
        P:      FactNamespace.
        max_ms: Hard ceiling in milliseconds (default 10 seconds).
        min_ms: Floor: if output was produced, took at least this long.
    """
    return [
        named("cli/timing-under-ceiling",
              Implies(P.wall_clock_ms >= 0, P.wall_clock_ms <= max_ms)),
        named("cli/timing-floor-when-output-produced",
              Implies(P.stdout_bytes >= 1, P.wall_clock_ms >= min_ms)),
        named("cli/timing-non-negative",
              Implies(P.wall_clock_ms >= 0, P.wall_clock_ms >= 0)),
    ]
