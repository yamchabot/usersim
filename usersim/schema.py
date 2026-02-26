"""
JSON schema definitions and validators for the usersim interchange format.

Three documents flow through the pipeline:

  metrics.json      → produced by your instrumentation (any language)
  perceptions.json  → produced by your perception script (any language)
  results.json      → produced by the usersim judgement engine (Z3)

Each document carries a "schema" field so tools can verify compatibility.
"""

METRICS_SCHEMA     = "usersim.metrics.v1"
PERCEPTIONS_SCHEMA = "usersim.perceptions.v1"
RESULTS_SCHEMA     = "usersim.results.v1"


def validate_metrics(doc: dict) -> None:
    """Raise ValueError if the metrics document is malformed."""
    if doc.get("schema") != METRICS_SCHEMA:
        raise ValueError(
            f"Expected schema '{METRICS_SCHEMA}', got {doc.get('schema')!r}. "
            "Ensure your instrumentation sets {\"schema\": \"usersim.metrics.v1\"}."
        )
    if "metrics" not in doc or not isinstance(doc["metrics"], dict):
        raise ValueError("metrics.json must contain a 'metrics' object.")


def validate_perceptions(doc: dict) -> None:
    """Raise ValueError if the perceptions document is malformed."""
    if doc.get("schema") != PERCEPTIONS_SCHEMA:
        raise ValueError(
            f"Expected schema '{PERCEPTIONS_SCHEMA}', got {doc.get('schema')!r}."
        )
    if "facts" not in doc or not isinstance(doc["facts"], dict):
        raise ValueError("perceptions.json must contain a 'facts' object.")
    if "person" not in doc:
        raise ValueError("perceptions.json must contain a 'person' field.")
