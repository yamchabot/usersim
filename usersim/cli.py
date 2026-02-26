"""
usersim CLI

Usage:
  usersim run   --metrics metrics.json --perceptions perceptions.py
                --users users/sarah.py users/marcus.py
                [--out results.json]

  usersim matrix --perceptions-dir perceptions/
                 --users users/sarah.py users/marcus.py
                 [--out results.json]

  usersim report --results results.json [--out report.html]
  usersim init   [DIR]
"""

import argparse
import json
import sys
from pathlib import Path


def cmd_run(args):
    """Run the full pipeline: instrumentation → perceptions → judgement."""
    from usersim.runner import run_pipeline
    results = run_pipeline(
        metrics_path=args.metrics,
        perceptions_script=args.perceptions,
        user_files=args.users,
        output_path=args.out,
        scenario=args.scenario,
        person=args.person,
        verbose=args.verbose,
    )
    _print_summary(results)
    return 0 if results["summary"]["score"] == 1.0 else 1


def cmd_judge(args):
    """Run only the judgement layer against an existing perceptions.json."""
    from usersim.judgement.engine import run_judgement, run_matrix
    if args.perceptions_dir:
        results = run_matrix(
            perceptions_dir=args.perceptions_dir,
            user_files=args.users,
            output_path=args.out,
        )
    else:
        results = run_judgement(
            perceptions_path=args.perceptions,
            user_files=args.users,
            output_path=args.out,
        )
    _print_summary(results)
    return 0 if results["summary"]["score"] == 1.0 else 1


def cmd_report(args):
    """Generate an HTML report from results.json."""
    from usersim.report.html import generate_report
    results_path = Path(args.results)
    out_path     = args.out or results_path.with_suffix(".html")
    with open(results_path) as f:
        results = json.load(f)
    generate_report(results, out_path)
    print(f"Report written to {out_path}")
    return 0


def cmd_init(args):
    """Scaffold a new usersim project."""
    from usersim.scaffold import init_project
    target = Path(args.dir or ".")
    init_project(target)
    return 0


def _print_summary(results: dict) -> None:
    summary = results.get("summary", {})
    total     = summary.get("total", 0)
    satisfied = summary.get("satisfied", 0)
    score     = summary.get("score", 0)
    schema    = results.get("schema", "")

    if "matrix" in schema:
        persons   = sorted({r["person"]   for r in results.get("results", [])})
        scenarios = sorted({r["scenario"] for r in results.get("results", [])})
        result_map = {(r["person"], r["scenario"]): r for r in results.get("results", [])}

        print(f"\n{'':20}", end="")
        for s in scenarios:
            print(f"  {s[:12]:12}", end="")
        print()
        print("─" * (20 + 14 * len(scenarios)))
        for p in persons:
            print(f"  {p:18}", end="")
            for s in scenarios:
                r = result_map.get((p, s))
                if r:
                    sym = "✓" if r["satisfied"] else "✗"
                    print(f"  {sym:>12}", end="")
                else:
                    print(f"  {'─':>12}", end="")
            print()
        print()
    else:
        for r in results.get("results", []):
            sym = "✓" if r["satisfied"] else "✗"
            viol = f" — {r['violations'][0]}" if r.get("violations") else ""
            print(f"  {sym} {r['person']:20} score={r['score']:.3f}{viol}")

    print(f"\n  {satisfied}/{total} satisfied  (score {score:.1%})\n")


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="usersim",
        description="User simulation framework — measure satisfaction across simulated personas.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── run ───────────────────────────────────────────────────────────────────
    p_run = sub.add_parser("run", help="Run the full pipeline")
    p_run.add_argument("--metrics",     required=True, help="Path to metrics.json")
    p_run.add_argument("--perceptions", required=True, help="Path to perceptions.py")
    p_run.add_argument("--users",       required=True, nargs="+", help="User Python files")
    p_run.add_argument("--out",         help="Write results.json here")
    p_run.add_argument("--scenario",    default="default", help="Scenario name")
    p_run.add_argument("--person",      help="Evaluate specific person only")
    p_run.add_argument("--verbose",     action="store_true")
    p_run.set_defaults(func=cmd_run)

    # ── judge ─────────────────────────────────────────────────────────────────
    p_judge = sub.add_parser("judge", help="Run judgement on existing perceptions.json")
    p_judge.add_argument("--perceptions",     help="Path to perceptions.json")
    p_judge.add_argument("--perceptions-dir", help="Dir of perceptions.json files (matrix mode)")
    p_judge.add_argument("--users", required=True, nargs="+")
    p_judge.add_argument("--out",   help="Write results.json here")
    p_judge.set_defaults(func=cmd_judge)

    # ── report ────────────────────────────────────────────────────────────────
    p_report = sub.add_parser("report", help="Generate HTML report from results.json")
    p_report.add_argument("--results", required=True)
    p_report.add_argument("--out")
    p_report.set_defaults(func=cmd_report)

    # ── init ──────────────────────────────────────────────────────────────────
    p_init = sub.add_parser("init", help="Scaffold a new usersim project")
    p_init.add_argument("dir", nargs="?", help="Target directory (default: cwd)")
    p_init.set_defaults(func=cmd_init)

    args = parser.parse_args(argv)
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
