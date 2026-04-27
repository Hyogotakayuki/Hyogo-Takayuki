"""CLI entry point for the AI Product Planner."""
from __future__ import annotations
import argparse
import sys
import pathlib
from . import orchestrator, planner


def _parse_criteria(raw: list[str]) -> list[tuple[str, float]]:
    result = []
    for item in raw:
        if ":" not in item:
            print(f"[warn] Skipping invalid criterion (expected 'name:threshold'): {item}")
            continue
        name, _, threshold_str = item.partition(":")
        try:
            result.append((name.strip(), float(threshold_str.strip())))
        except ValueError:
            print(f"[warn] Skipping invalid threshold for {name!r}: {threshold_str}")
    return result or None


def cmd_plan(args: argparse.Namespace) -> None:
    idea = args.idea or sys.stdin.read()
    spec = planner.plan(idea.strip(), verbose=True)

    print(f"\n{'='*60}")
    print(f"  {spec.product_name}")
    print(f"{'='*60}")
    print(f"\nOverview\n  {spec.overview}")
    print(f"\nTarget users\n  {spec.target_users}")
    print(f"\nValue proposition\n  {spec.core_value_proposition}")
    print(f"\nFeatures ({len(spec.features)})")
    for f in spec.features:
        print(f"  [{f.priority[:1].upper()}] {f.id:>2}. {f.name}")
    print(f"\nSprints ({len(spec.sprints)})")
    for s in spec.sprints:
        feat_ids = ", ".join(str(i) for i in s.feature_ids)
        print(f"  Sprint {s.number:>2}: {s.name}  (features: {feat_ids})")
    print(f"\nOut of scope")
    for item in spec.out_of_scope:
        print(f"  - {item}")

    if args.save:
        out = pathlib.Path(args.save)
        out.mkdir(parents=True, exist_ok=True)
        orchestrator._save_spec(spec, out)
        print(f"\nSpec saved to {out / '.ai_planner' / 'spec.json'}")


def cmd_run(args: argparse.Namespace) -> None:
    idea = args.idea or sys.stdin.read()

    sprint_range = None
    if args.sprints:
        parts = args.sprints.split("-")
        sprint_range = (int(parts[0]), int(parts[-1]))

    criteria = _parse_criteria(args.criteria) if args.criteria else None

    result = orchestrator.run(
        idea.strip(),
        output_dir=args.output,
        sprint_range=sprint_range,
        eval_criteria=criteria,
        use_playwright=not args.no_playwright,
        verbose=True,
    )

    print(f"\n{'='*60}")
    print("  Run complete")
    print(f"{'='*60}")
    print(f"Output directory : {result.output_dir}")
    print(f"Sprints passed   : {len(result.succeeded_sprints)} / {len(result.records)}")

    if result.failed_sprints:
        print(f"\nFailed sprints:")
        for rec in result.failed_sprints:
            sprint = result.spec.get_sprint(rec.sprint_number)
            print(f"  Sprint {rec.sprint_number}: {sprint.name if sprint else '?'}")
            if rec.evals:
                ev = rec.evals[-1]
                for c in ev.criteria:
                    if not c.passed:
                        print(f"    ✗ {c.name}: {c.score:.2f} < {c.threshold:.2f}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="ai-product-planner",
        description="Turn a 1-4 line idea into a working product, sprint by sprint.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── plan ─────────────────────────────────────────────────────────────────
    p_plan = sub.add_parser("plan", help="Generate a product spec without building anything.")
    p_plan.add_argument("idea", nargs="?", help="1-4 line product idea (reads stdin if omitted).")
    p_plan.add_argument("--save", metavar="DIR", help="Save the spec JSON to this directory.")
    p_plan.set_defaults(func=cmd_plan)

    # ── run ──────────────────────────────────────────────────────────────────
    p_run = sub.add_parser("run", help="Plan, generate, and evaluate all sprints.")
    p_run.add_argument("idea", nargs="?", help="1-4 line product idea (reads stdin if omitted).")
    p_run.add_argument("-o", "--output", default="output", metavar="DIR",
                       help="Directory to write generated code (default: output).")
    p_run.add_argument("--sprints", metavar="N-M",
                       help="Only run sprints N through M (e.g. '1-3').")
    p_run.add_argument("--criteria", nargs="+", metavar="NAME:THRESHOLD",
                       help="Evaluation criteria overrides (e.g. ui_usability:0.8).")
    p_run.add_argument("--no-playwright", action="store_true",
                       help="Skip Playwright browser testing (static code analysis only).")
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
