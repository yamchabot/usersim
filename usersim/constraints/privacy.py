"""
usersim.constraints.privacy — data exposure, consent, and audit trail.

Perceptions contract:
  pii_fields_exposed    (int >= 0)  — count of PII fields in output
  pii_fields_total      (int >= 0)  — total PII fields in the system
  consent_recorded      (bool)      — consent captured before data use
  audit_events_total    (int >= 0)  — total audit log events emitted
  audit_events_expected (int >= 0)  — expected audit events for this path
  data_retention_days   (int >= 0)  — how long data is kept
  anonymized            (bool)      — data passed through anonymization
"""
from usersim.judgement.z3_compat import And, Implies, Not, named


def data_exposure(P, *, max_pii_exposed: int = 0):
    """PII fields must not leak into output.

    Args:
        P:               FactNamespace.
        max_pii_exposed: Maximum PII fields allowed in output (default 0).
    """
    return [
        named("privacy/no-pii-in-output",
              Implies(P.pii_fields_total >= 0,
                      P.pii_fields_exposed <= max_pii_exposed)),
        named("privacy/exposed-never-exceeds-total",
              Implies(P.pii_fields_total >= 0,
                      P.pii_fields_exposed <= P.pii_fields_total)),
        named("privacy/anonymization-reduces-exposure",
              Implies(And(P.anonymized, P.pii_fields_total >= 1),
                      P.pii_fields_exposed == 0)),
        named("privacy/no-exposure-without-data",
              Implies(P.pii_fields_total == 0, P.pii_fields_exposed == 0)),
    ]


def consent(P):
    """Consent must be recorded before any data use."""
    return [
        named("privacy/consent-recorded-before-use",
              Implies(P.pii_fields_total >= 1, P.consent_recorded)),
        named("privacy/no-pii-without-consent",
              Not(And(P.pii_fields_total >= 1, P.pii_fields_exposed >= 1,
                      Not(P.consent_recorded)))),
    ]


def audit_trail(P, *, max_retention_days: int = 365):
    """Audit events must be complete and data retention bounded.

    Args:
        P:                  FactNamespace.
        max_retention_days: Maximum data retention period (default 365 days).
    """
    return [
        named("privacy/audit-log-complete",
              Implies(P.audit_events_expected >= 1,
                      P.audit_events_total >= P.audit_events_expected)),
        named("privacy/no-extra-audit-events",
              Implies(P.audit_events_expected >= 1,
                      P.audit_events_total <= P.audit_events_expected * 2)),
        named("privacy/retention-within-policy",
              Implies(P.data_retention_days >= 0,
                      P.data_retention_days <= max_retention_days)),
        named("privacy/retention-positive",
              Implies(P.data_retention_days >= 0, P.data_retention_days >= 1)),
        # Audit required when data is retained
        named("privacy/retention-implies-audit",
              Implies(And(P.data_retention_days >= 1, P.audit_events_expected >= 1),
                      P.audit_events_total >= 1)),
    ]
