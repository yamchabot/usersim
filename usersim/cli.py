"""
usersim CLI

Primary usage — driven by usersim.yaml config file:

    usersim run                        # LLM-readable narrative output (default)
    usersim run --matrix               # also print scenario×person grid
    usersim run --config path/to/usersim.yaml  # explicit config
    usersim run --scenario peak_load   # run one specific scenario
    usersim run --out results.json     # save results to file (also stdout)

Add `usersim run` to your Makefile, npm scripts, pyproject.toml, Bazel rules,
or whatever build system your project uses.  The config file declares how to
run each stage; usersim handles the rest.

Other subcommands (for one-off use, no config needed):

    usersim judge --users users/*.py          # reads perceptions JSON from stdin
    usersim judge --perceptions p.json ...    # from a file
    usersim judge --perceptions-dir perc/ ... # matrix mode
    usersim report --results results.json     # generate HTML report
    usersim audit --results results.json      # constraint health analysis
    usersim calibrate                         # print perception values per scenario
    usersim init [DIR]                        # scaffold a new project
"""

import argparse
import json
import sys
from pathlib import Path


def cmd_run(args):
    """
    Run the full pipeline as declared in usersim.yaml.

    Reads the config file, runs instrumentation + perceptions + judgement
    for each scenario, writes results to stdout (or --out file).
    """
    from usersim.runner import run_from_config

    try:
        results = run_from_config(
            config=args.config,
            scenario_override=args.scenario or None,
            output_path=args.out,
            verbose=args.verbose,
        )
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except (ValueError, RuntimeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if not args.quiet:
        if args.matrix:
            _print_summary(results, file=sys.stderr)
        _print_narrative(results, file=sys.stderr)

    return 0 if results["summary"]["score"] == 1.0 else 2


def cmd_judge(args):
    """
    Run judgement only.  Reads perceptions JSON from stdin or --perceptions file.
    Useful for one-off runs and scripting without a config file.
    """
    from usersim.judgement.engine import run_judgement, run_matrix

    if args.perceptions_dir:
        results = run_matrix(
            perceptions_dir=args.perceptions_dir,
            user_files=args.users,
            output_path=args.out,
        )
    else:
        source = args.perceptions if args.perceptions else "-"
        results = run_judgement(
            perceptions=source,
            user_files=args.users,
            output_path=args.out,
        )
    if not args.quiet:
        _print_summary(results, file=sys.stderr)
    return 0 if results["summary"]["score"] == 1.0 else 2


def cmd_report(args):
    """Generate an HTML report from results JSON (stdin or --results file)."""
    from usersim.report.html import generate_report

    if args.results and args.results != "-":
        with open(args.results) as f:
            results = json.load(f)
    else:
        results = json.load(sys.stdin)

    out_path = args.out or "report.html"
    generate_report(results, out_path)
    print(f"Report written to {out_path}", file=sys.stderr)
    return 0


def cmd_init(args):
    """Scaffold a new usersim project."""
    from usersim.scaffold import init_project
    target = Path(args.dir or ".")
    init_project(target)
    return 0


def cmd_audit(args):
    """Analyse constraint health — runs tests first if no --results file given."""
    from usersim.audit import run_audit, print_audit
    from usersim.runner import load_config, run_from_config

    config = None
    try:
        config = load_config(args.config)
    except Exception:
        pass

    if args.results and args.results != "-":
        with open(args.results) as f:
            results = json.load(f)
    elif args.results == "-":
        results = json.load(sys.stdin)
    else:
        # No results file — run the pipeline first
        if config is None:
            print("error: no results file and no usersim.yaml found", file=sys.stderr)
            return 1
        print("Running tests...", file=sys.stderr)
        try:
            results = run_from_config(config=args.config, verbose=False)
        except (FileNotFoundError, ValueError, RuntimeError) as e:
            print(f"error: {e}", file=sys.stderr)
            return 1

    audit = run_audit(results, config=config)

    if args.json:
        print(json.dumps(audit, indent=2))
    else:
        print_audit(audit)

    # Exit 1 if any vacuous constraints found (useful in CI)
    return 1 if audit["summary"]["vacuous_count"] > 0 else 0


def cmd_calibrate(args):
    """Print actual perception values per scenario for threshold calibration."""
    from usersim.runner import load_config
    from usersim.calibrate import run_calibrate

    try:
        config = load_config(args.config)
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    return run_calibrate(config, scenario_override=args.scenario or None)


def _print_summary(results: dict, file=sys.stderr) -> None:
    summary   = results.get("summary", {})
    total     = summary.get("total", 0)
    satisfied = summary.get("satisfied", 0)
    score     = summary.get("score", 0)
    schema    = results.get("schema", "")

    if "matrix" in schema:
        persons   = sorted({r["person"]   for r in results.get("results", [])})
        scenarios = sorted({r["scenario"] for r in results.get("results", [])})
        result_map = {(r["person"], r["scenario"]): r for r in results.get("results", [])}

        # Scenarios as rows, persons as columns (fewer persons than scenarios)
        row_w = max((len(s) for s in scenarios), default=8)
        col_w = max((len(p) for p in persons),   default=6) + 2

        # Header: person names
        print(f"\n{'':>{row_w}}", end="", file=file)
        for p in persons:
            print(f"  {p:>{col_w}}", end="", file=file)
        print(file=file)
        print("─" * (row_w + (col_w + 2) * len(persons)), file=file)

        # One row per scenario
        for s in scenarios:
            print(f"  {s:<{row_w}}", end="", file=file)
            for p in persons:
                r = result_map.get((p, s))
                sym = ("✓" if r["satisfied"] else "✗") if r else "─"
                print(f"  {sym:>{col_w}}", end="", file=file)
            print(file=file)
        print(file=file)
    else:
        for r in results.get("results", []):
            sym  = "✓" if r["satisfied"] else "✗"
            viol = f" — {r['violations'][0]}" if r.get("violations") else ""
            print(f"  {sym} {r['person']:20} score={r['score']:.3f}{viol}", file=file)

    eff   = summary.get("effective_tests",  0)
    evals = summary.get("constraint_evals", 0)
    eff_str = f"  ⚡ ~{eff:,} effective tests  ({evals} constraint evals × 4^k)\n" if eff else ""
    print(f"\n  {satisfied}/{total} satisfied  (score {score:.1%})\n{eff_str}", file=file)


def _print_narrative(results: dict, file=sys.stdout) -> None:
    """
    LLM-readable narrative output — one block per unsatisfied person.

    Format is designed to be unambiguous for AI coding agents:
    each block explains who is unhappy, what they want, which constraints
    failed, and in which scenarios — so the agent knows exactly what to fix.
    """
    all_results = results.get("results", [])
    schema      = results.get("schema", "")

    # Collect person metadata and group results by person
    persons_seen = []
    by_person: dict[str, list[dict]] = {}
    for r in all_results:
        p = r["person"]
        if p not in by_person:
            persons_seen.append(p)
            by_person[p] = []
        by_person[p].append(r)

    any_failure = any(
        not r["satisfied"]
        for rlist in by_person.values()
        for r in rlist
    )

    if not any_failure:
        total = results.get("summary", {}).get("total", 0)
        print(f"\nALL CHECKS PASSED ({total} person×scenario checks satisfied).\n", file=file)
        return

    print("\n" + "=" * 60, file=file)
    print("USER SIMULATION — FAILURES", file=file)
    print("=" * 60, file=file)
    print("The following users are unsatisfied with the current layout.", file=file)
    print("Fix the indicated constraints to make them happy.\n", file=file)

    for person_name in persons_seen:
        person_results = by_person[person_name]
        failing = [r for r in person_results if not r["satisfied"]]

        if not failing:
            continue

        # Pull metadata from first result
        first   = person_results[0]
        role    = first.get("role", "")
        goal    = first.get("goal", "")
        pronoun = first.get("pronoun", "they")
        pro     = pronoun
        Pro     = pro.capitalize()
        sv      = "" if pro == "they" else "s"

        # Deduplicate violations across scenarios
        seen_viols: set[str] = set()
        violations: list[str] = []
        for r in failing:
            for v in r.get("violations", []):
                if v not in seen_viols:
                    seen_viols.add(v)
                    violations.append(v)

        failing_scenarios = [r["scenario"] for r in failing]
        goal_lc = goal[0].lower() + goal[1:] if goal else "accomplish their goal"

        print(f"❌ {person_name} ({role})", file=file)
        print(f"   Goal: {Pro} want{sv} to {goal_lc}", file=file)

        if violations:
            print(f"   Failing constraints:", file=file)
            for v in violations:
                print(f"     • {v}", file=file)
        else:
            print(f"   (constraints not available — check formula)", file=file)

        if "matrix" in schema:
            print(f"   Failing scenarios: {', '.join(failing_scenarios)}", file=file)

        print(file=file)

    print("=" * 60 + "\n", file=file)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="usersim",
        description=(
            "User simulation framework — check whether your app satisfies real users.\n\n"
            "Quickstart:\n"
            "  usersim init        scaffold a new project\n"
            "  usersim run         run the pipeline (reads usersim.yaml)"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── run ───────────────────────────────────────────────────────────────────
    p_run = sub.add_parser(
        "run",
        help="Run the full pipeline (reads usersim.yaml)",
        description=(
            "Run instrumentation → perceptions → judgement as declared in\n"
            "usersim.yaml.  Add this to your Makefile, npm scripts, etc."
        ),
    )
    p_run.add_argument(
        "--config", metavar="FILE",
        help="Config file (default: usersim.yaml in current directory)",
    )
    p_run.add_argument(
        "--scenario", metavar="NAME",
        help="Run a single scenario by name (overrides config scenarios list)",
    )
    p_run.add_argument(
        "--out", metavar="FILE",
        help="Save results JSON here (also written to stdout)",
    )
    p_run.add_argument("--quiet",   action="store_true", help="Suppress all human output")
    p_run.add_argument("--matrix", action="store_true", help="Print scenario×person grid (token-heavy; not for LLM pipelines)")
    p_run.add_argument("--verbose", action="store_true", help="Print stage info to stderr")
    p_run.set_defaults(func=cmd_run)

    # ── judge ─────────────────────────────────────────────────────────────────
    p_judge = sub.add_parser(
        "judge",
        help="Run judgement only — reads perceptions JSON from stdin or file",
    )
    p_judge.add_argument(
        "--perceptions", metavar="FILE",
        help="Perceptions JSON file; omit or use '-' to read from stdin",
    )
    p_judge.add_argument(
        "--perceptions-dir", metavar="DIR",
        help="Directory of perceptions JSON files (matrix mode)",
    )
    p_judge.add_argument("--users", required=True, nargs="+", metavar="FILE",
                         help="User Python files")
    p_judge.add_argument("--out",   metavar="FILE",
                         help="Save results JSON here (default: stdout)")
    p_judge.add_argument("--quiet", action="store_true")
    p_judge.set_defaults(func=cmd_judge)

    # ── report ────────────────────────────────────────────────────────────────
    p_report = sub.add_parser(
        "report",
        help="Generate HTML report from results JSON",
    )
    p_report.add_argument(
        "--results", metavar="FILE",
        help="Results JSON file; omit or use '-' to read from stdin",
    )
    p_report.add_argument("--out", metavar="FILE", help="Output HTML (default: report.html)")
    p_report.set_defaults(func=cmd_report)

    # ── init ──────────────────────────────────────────────────────────────────
    p_init = sub.add_parser("init", help="Scaffold a new usersim project in DIR (default: cwd)")
    p_init.add_argument("dir", nargs="?", metavar="DIR")
    p_init.set_defaults(func=cmd_init)

    # ── audit ─────────────────────────────────────────────────────────────────
    p_audit = sub.add_parser(
        "audit",
        help="Analyse constraint health (runs tests first if no --results given)",
        description=(
            "Detects: vacuous constraints, trivially-passing constraints, dead perceptions,\n"
            "constraint count imbalance, and variable density distribution.\n\n"
            "If --results is omitted, runs the full test pipeline first (reads usersim.yaml).\n"
            "Exits 1 if any vacuous constraints are found (useful in CI)."
        ),
    )
    p_audit.add_argument(
        "--results", metavar="FILE",
        help="Results JSON file to analyse; use '-' for stdin. "
             "If omitted, tests are run automatically first.",
    )
    p_audit.add_argument(
        "--config", metavar="FILE",
        help="Config file (for locating perceptions.py; default: usersim.yaml)",
    )
    p_audit.add_argument("--json", action="store_true", help="Output as JSON")
    p_audit.set_defaults(func=cmd_audit)

    # ── calibrate ─────────────────────────────────────────────────────────────
    p_cal = sub.add_parser(
        "calibrate",
        help="Print actual perception values per scenario for threshold calibration",
        description=(
            "Runs instrumentation + perceptions for each scenario and prints the\n"
            "perception dict.  Use this to set constraint thresholds at realistic values."
        ),
    )
    p_cal.add_argument(
        "--config", metavar="FILE",
        help="Config file (default: usersim.yaml)",
    )
    p_cal.add_argument(
        "--scenario", metavar="NAME",
        help="Run a single scenario only",
    )
    p_cal.set_defaults(func=cmd_calibrate)

    args = parser.parse_args(argv)
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
