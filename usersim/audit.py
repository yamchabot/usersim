"""
usersim audit — constraint system health analysis.

Run against a results.json file to detect:
  1. Vacuous constraints (antecedent never fires)
  2. Always-passing constraints (possible trivial thresholds)
  3. Constraint count per persona
  4. Variable density (coverage per constraint)
  5. Dead perceptions (computed but never referenced)
"""

import re
import glob
import importlib.util
import inspect
from collections import defaultdict
from pathlib import Path

_Z3_KEYWORDS = {"If", "then", "And", "Or", "Not", "Implies", "True", "False", "else"}


def _extract_vars(expr: str) -> set[str]:
    return {t for t in re.findall(r'\b[a-z][a-z0-9_]*\b', expr)
            if t not in _Z3_KEYWORDS}


def run_audit(results: dict, config: dict | None = None) -> dict:
    """
    Analyse results.json for constraint health problems.

    Returns a structured dict with keys:
      vacuous, always_passing, counts_per_persona,
      top_density, bottom_density, dead_perceptions, summary
    """
    raw_results   = results.get("results", [])
    summary       = results.get("summary", {})
    all_persons   = sorted({x["person"]   for x in raw_results})
    all_scenarios = sorted({x["path"] for x in raw_results})

    # ── 1. Vacuous constraints ────────────────────────────────────────────────
    label_ever_fired: dict[str, dict[str, bool]] = defaultdict(lambda: defaultdict(bool))
    for x in raw_results:
        for c in x.get("constraints", []):
            if c.get("antecedent_fired") is True:
                label_ever_fired[x["person"]][c["label"]] = True

    vacuous = []
    seen: set[tuple] = set()
    for x in raw_results:
        for c in x.get("constraints", []):
            if c.get("antecedent_fired") is False:
                key = (x["person"], c["label"])
                if key not in seen and not label_ever_fired[x["person"]][c["label"]]:
                    seen.add(key)
                    vacuous.append({"person": x["person"], "label": c["label"]})

    # ── 2. Always-passing constraints ─────────────────────────────────────────
    label_stats: dict[tuple, dict] = defaultdict(lambda: {"pass": 0, "total": 0})
    for x in raw_results:
        for c in x.get("constraints", []):
            if c.get("antecedent_fired") is not False:
                key = (x["person"], c["label"])
                label_stats[key]["total"] += 1
                if c.get("passed"):
                    label_stats[key]["pass"] += 1

    always_passing = [
        {"person": k[0], "label": k[1], "pass": v["pass"], "total": v["total"]}
        for k, v in label_stats.items()
        if v["total"] >= len(all_scenarios) and v["pass"] == v["total"]
    ]

    # ── 3. Constraint count per persona ───────────────────────────────────────
    counts_per_persona = []
    for person in all_persons:
        pr = [x for x in raw_results if x["person"] == person]
        counts = [len(x.get("constraints", [])) for x in pr]
        avg = sum(counts) / len(counts) if counts else 0
        counts_per_persona.append({"person": person, "avg_constraints": round(avg, 1)})

    # ── 4. Variable density ───────────────────────────────────────────────────
    density: dict[str, int] = {}
    for x in raw_results:
        for c in x.get("constraints", []):
            if c.get("antecedent_fired") is not False:
                label = c["label"]
                if label not in density:
                    density[label] = len(_extract_vars(c.get("expr", "")))

    sorted_density = sorted(density.items(), key=lambda x: x[1])
    top_density    = [{"label": l, "vars": n} for l, n in reversed(sorted_density[-10:])]
    bottom_density = [{"label": l, "vars": n} for l, n in sorted_density[:10]]

    # ── 5. Dead perceptions ───────────────────────────────────────────────────
    dead_perceptions: list[str] = []
    dead_error: str | None = None

    perceptions_path = _find_perceptions(config)
    users_pattern    = _find_users_pattern(config)

    if perceptions_path:
        try:
            spec = importlib.util.spec_from_file_location("_usersim_perc", perceptions_path)
            mod  = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            src = inspect.getsource(mod.compute)
            perception_keys = set(re.findall(r'"([a-z][a-z0-9_]*)"', src))

            referenced: set[str] = set()
            for path in glob.glob(users_pattern or "user_simulation/users/*.py"):
                with open(path) as f:
                    for m in re.finditer(r'P\.([a-z][a-z0-9_]*)', f.read()):
                        referenced.add(m.group(1))

            dead_perceptions = sorted(perception_keys - referenced)
        except Exception as e:
            dead_error = str(e)
    else:
        dead_error = "perceptions path not found (pass --config or run from project root)"

    return {
        "persons":   all_persons,
        "paths": all_scenarios,
        "summary": {
            "effective_tests":  summary.get("effective_tests", 0),
            "constraint_evals": summary.get("constraint_evals", 0),
            "satisfied":        summary.get("satisfied", 0),
            "total":            summary.get("total", 0),
            "vacuous_count":    len(vacuous),
            "always_passing_count": len(always_passing),
            "dead_perceptions_count": len(dead_perceptions),
        },
        "vacuous":           vacuous,
        "always_passing":    always_passing,
        "counts_per_persona": counts_per_persona,
        "top_density":       top_density,
        "bottom_density":    bottom_density,
        "dead_perceptions":  dead_perceptions,
        "dead_perceptions_error": dead_error,
    }


def _find_perceptions(config: dict | None) -> Path | None:
    if config:
        p = config.get("perceptions")
        base = config.get("_base_dir", Path("."))
        if p:
            candidate = Path(p) if Path(p).is_absolute() else base / p
            if candidate.exists():
                return candidate
    for candidate in [
        "user_simulation/perceptions.py",
        "perceptions.py",
        "usersim/perceptions.py",
    ]:
        if Path(candidate).exists():
            return Path(candidate)
    return None


def _find_users_pattern(config: dict | None) -> str | None:
    if not config:
        return None
    base = config.get("_base_dir", Path("."))
    users = config.get("users", [])
    if users and isinstance(users[0], str):
        # Resolve glob relative to config base dir
        pattern = users[0]
        if not Path(pattern).is_absolute():
            pattern = str(base / pattern)
        return pattern
    return None


def print_audit(audit: dict, file=None) -> None:
    """Pretty-print audit results to stderr (or file)."""
    import sys
    f = file or sys.stderr

    s = audit["summary"]
    print(f"\n=== usersim constraint audit ===", file=f)
    print(f"Persons: {len(audit['persons'])}  Scenarios: {len(audit['paths'])}", file=f)
    print(f"Effective tests:  {s['effective_tests']:,}", file=f)
    print(f"Constraint evals: {s['constraint_evals']:,}", file=f)
    print(f"Pass rate:        {s['satisfied']}/{s['total']}", file=f)

    # 1. Vacuous
    print(f"\n--- Vacuous constraints ({s['vacuous_count']}) ---", file=f)
    if audit["vacuous"]:
        for v in audit["vacuous"]:
            print(f"  {v['person']}: {v['label']}", file=f)
    else:
        print("  none ✓", file=f)

    # 2. Always-passing
    print(f"\n--- Always-passing constraints ({s['always_passing_count']}) ---", file=f)
    print("    (100% pass rate — run the broken-system test to verify these ask hard questions)", file=f)
    if audit["always_passing"]:
        for v in audit["always_passing"][:20]:
            print(f"  {v['person']}: {v['label']}  ({v['pass']}/{v['total']})", file=f)
        if len(audit["always_passing"]) > 20:
            print(f"  ... and {len(audit['always_passing']) - 20} more", file=f)
    else:
        print("  none (every constraint has at least one failure path)", file=f)

    # 3. Counts per persona
    print(f"\n--- Constraint count per persona ---", file=f)
    for row in audit["counts_per_persona"]:
        print(f"  {row['person']:<30} {row['avg_constraints']:>5} constraints/path", file=f)

    # 4. Variable density
    print(f"\n--- Most variable coverage (top 10) ---", file=f)
    for row in audit["top_density"]:
        print(f"  {row['vars']} vars  {row['label']}", file=f)
    print(f"\n--- Least variable coverage (bottom 10) ---", file=f)
    for row in audit["bottom_density"]:
        print(f"  {row['vars']} vars  {row['label']}", file=f)

    # 5. Dead perceptions
    print(f"\n--- Dead perceptions ({s['dead_perceptions_count']}) ---", file=f)
    if audit.get("dead_perceptions_error"):
        print(f"  (skipped: {audit['dead_perceptions_error']})", file=f)
    elif audit["dead_perceptions"]:
        for k in audit["dead_perceptions"]:
            print(f"  {k}", file=f)
    else:
        print("  none ✓", file=f)

    print(file=f)
