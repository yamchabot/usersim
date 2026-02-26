"""
processor.py — a simple in-memory data processor.

Sorts, searches, and summarises lists of records.
This is the application being tested by usersim.
"""
from __future__ import annotations
import statistics


def sort_records(records: list[dict], key: str, reverse: bool = False) -> list[dict]:
    """Sort records by the given key.  Missing keys sort to the end."""
    return sorted(records, key=lambda r: (key not in r, r.get(key, 0)), reverse=reverse)


def search_records(records: list[dict], query: str) -> list[dict]:
    """Case-insensitive substring search across all string values."""
    q = query.lower()
    return [r for r in records if any(q in str(v).lower() for v in r.values())]


def summarise(records: list[dict], field: str) -> dict:
    """Compute descriptive statistics for a numeric field."""
    values = [r[field] for r in records if field in r and isinstance(r[field], (int, float))]
    if not values:
        return {"count": 0}
    return {
        "count":  len(values),
        "mean":   round(statistics.mean(values), 4),
        "median": round(statistics.median(values), 4),
        "stdev":  round(statistics.stdev(values), 4) if len(values) > 1 else 0.0,
        "min":    min(values),
        "max":    max(values),
    }
