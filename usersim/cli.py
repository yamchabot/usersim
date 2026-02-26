"""
usersim CLI

Every command reads from stdin and writes results JSON to stdout by default.
Use --out to save to a file instead.  Use --quiet to suppress the human summary.

Pipeline usage (three separate processes, shell pipes):

    python3 instrumentation.py \\
      | python3 perceptions.py \\
      | usersim judge --users users/*.py

All-in-one (run drives the perceptions → judgement steps):

    python3 instrumentation.py \\
      | usersim run --perceptions perceptions.py --users users/*.py

Other subcommands:

    usersim judge --perceptions perceptions.json --users users/*.py
    usersim judge --perceptions-dir perceptions/  --users users/*.py
    usersim report --results results.json [--out report.html]
    usersim init [DIR]
"""

import argparse
import json
import sys
from pathlib import Path


def cmd_run(args):
    """Perceptions + judgement.  Reads metrics JSON from stdin (or --metrics file)."""
    from usersim.runner import run_pipeline

    # Load metrics from file if given, otherwise runner reads from stdin
    metrics = None
    if args.metrics and args.metrics != "-":
        with open(args.metrics) as f:
            metrics = json.load(f)

    results = run_pipeline(
        perceptions_script=args.perceptions,
        user_files=args.users,
        metrics=metrics,
        output_path=args.out,
        scenario=args.scenario,
        person=args.person,
        verbose=args.verbose,
    )
    if not args.quiet:
        _print_summary(results, file=sys.stderr)
    return 0 if results["summary"]["score"] == 1.0 else 1


def cmd_judge(args):
    """Judgement only.  Reads perceptions JSON from stdin (or --perceptions file)."""
    from usersim.judgement.engine import run_judgement, run_matrix

    if args.perceptions_dir:
        results = run_matrix(
            perceptions_dir=args.perceptions_dir,
            user_files=args.users,
            output_path=args.out,
        )
    else:
        # "-" or None → stdin; anything else → file path
        source = args.perceptions if args.perceptions else "-"
        results = run_judgement(
            perceptions=source,
            user_files=args.users,
            output_path=args.out,
        )
    if not args.quiet:
        _print_summary(results, file=sys.stderr)
    return 0 if results["summary"]["score"] == 1.0 else 1


def cmd_report(args):
    """Generate an HTML report.  Reads results JSON from stdin (or --results file)."""
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

        print(f"\n{'':20}", end="", file=file)
        for s in scenarios:
            print(f"  {s[:12]:12}", end="", file=file)
        print(file=file)
        print("─" * (20 + 14 * len(scenarios)), file=file)
        for p in persons:
            print(f"  {p:18}", end="", file=file)
            for s in scenarios:
                r = result_map.get((p, s))
                sym = ("✓" if r["satisfied"] else "✗") if r else "─"
                print(f"  {sym:>12}", end="", file=file)
            print(file=file)
        print(file=file)
    else:
        for r in results.get("results", []):
            sym  = "✓" if r["satisfied"] else "✗"
            viol = f" — {r['violations'][0]}" if r.get("violations") else ""
            print(f"  {sym} {r['person']:20} score={r['score']:.3f}{viol}", file=file)

    print(f"\n  {satisfied}/{total} satisfied  (score {score:.1%})\n", file=file)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="usersim",
        description=(
            "User simulation framework.\n"
            "Each command reads JSON from stdin and writes results JSON to stdout.\n"
            "Use --out to save to a file.  Human summary always goes to stderr."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── run ───────────────────────────────────────────────────────────────────
    p_run = sub.add_parser(
        "run",
        help="Run perceptions + judgement (reads metrics JSON from stdin or --metrics)",
    )
    p_run.add_argument(
        "--metrics", default="-",
        help="Metrics JSON file (default: stdin)",
    )
    p_run.add_argument("--perceptions", required=True, help="Perceptions script path")
    p_run.add_argument("--users",       required=True, nargs="+", help="User Python files")
    p_run.add_argument("--out",         help="Save results JSON here (default: stdout)")
    p_run.add_argument("--scenario",    default="default")
    p_run.add_argument("--person",      help="Evaluate specific person only")
    p_run.add_argument("--quiet",       action="store_true", help="Suppress human summary")
    p_run.add_argument("--verbose",     action="store_true")
    p_run.set_defaults(func=cmd_run)

    # ── judge ─────────────────────────────────────────────────────────────────
    p_judge = sub.add_parser(
        "judge",
        help="Run judgement (reads perceptions JSON from stdin or --perceptions)",
    )
    p_judge.add_argument(
        "--perceptions", default=None,
        help="Perceptions JSON file; omit or use '-' to read from stdin",
    )
    p_judge.add_argument(
        "--perceptions-dir",
        help="Directory of perceptions JSON files (matrix mode)",
    )
    p_judge.add_argument("--users", required=True, nargs="+")
    p_judge.add_argument("--out",   help="Save results JSON here (default: stdout)")
    p_judge.add_argument("--quiet", action="store_true", help="Suppress human summary")
    p_judge.set_defaults(func=cmd_judge)

    # ── report ────────────────────────────────────────────────────────────────
    p_report = sub.add_parser(
        "report",
        help="Generate HTML report (reads results JSON from stdin or --results)",
    )
    p_report.add_argument(
        "--results", default=None,
        help="Results JSON file; omit or use '-' to read from stdin",
    )
    p_report.add_argument("--out", help="Output HTML path (default: report.html)")
    p_report.set_defaults(func=cmd_report)

    # ── init ──────────────────────────────────────────────────────────────────
    p_init = sub.add_parser("init", help="Scaffold a new usersim project")
    p_init.add_argument("dir", nargs="?", help="Target directory (default: cwd)")
    p_init.set_defaults(func=cmd_init)

    args = parser.parse_args(argv)
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
