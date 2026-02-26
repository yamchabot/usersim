"""
usersim CLI

Primary usage — driven by usersim.yaml config file:

    usersim run                        # reads usersim.yaml in cwd
    usersim run --config ci.yaml       # explicit config file
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
        _print_summary(results, file=sys.stderr)

    return 0 if results["summary"]["score"] == 1.0 else 1


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
    return 0 if results["summary"]["score"] == 1.0 else 1


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

        col_w = max((len(s) for s in scenarios), default=8) + 2
        print(f"\n{'':20}", end="", file=file)
        for s in scenarios:
            print(f"  {s:>{col_w}}", end="", file=file)
        print(file=file)
        print("─" * (20 + (col_w + 2) * len(scenarios)), file=file)
        for p in persons:
            print(f"  {p:18}", end="", file=file)
            for s in scenarios:
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

    print(f"\n  {satisfied}/{total} satisfied  (score {score:.1%})\n", file=file)


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
    p_run.add_argument("--quiet",   action="store_true", help="Suppress human summary on stderr")
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

    args = parser.parse_args(argv)
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
