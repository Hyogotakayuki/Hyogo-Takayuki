"""AI Product Planner – entry point.

Usage:
    python main.py "2Dレトロゲームメーカーを作って"
    python main.py "Build a personal finance tracker" --output ./my-app
    python main.py "Build a personal finance tracker" --sprints 1-3   # run specific sprints
    python main.py spec.json --from-spec                               # skip planning step

Environment variables:
    ANTHROPIC_API_KEY       Required – your Anthropic API key.
    APP_BASE_URL            Base URL of the running app (default: http://localhost:3000).
    PLAYWRIGHT_MCP_URL      URL of the Playwright MCP server (optional, enables real browser tests).
    PLANNER_MODEL           Claude model for the Planner  (default: claude-sonnet-4-6).
    GENERATOR_MODEL         Claude model for the Generator (default: claude-sonnet-4-6).
    EVALUATOR_MODEL         Claude model for the Evaluator (default: claude-sonnet-4-6).
"""

import argparse
import json
import os
import sys
from pathlib import Path

from agents.evaluator import EvaluatorAgent
from agents.generator import GeneratorAgent
from agents.planner import PlannerAgent
from models import EvaluationStatus, ProductSpec, Sprint


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run(
    prompt: str,
    output_dir: str = "./output",
    sprint_range: tuple[int, int] | None = None,
    max_retries: int = 3,
    from_spec: str | None = None,
) -> None:
    _banner("AI Product Planner")

    # ---- Phase 1: Planning --------------------------------------------------
    if from_spec:
        print(f"[Planner] Loading spec from {from_spec}")
        with open(from_spec, encoding="utf-8") as f:
            data = json.load(f)
        spec = _spec_from_dict(data)
    else:
        print("[Planner] Generating product specification …")
        planner = PlannerAgent(model=os.getenv("PLANNER_MODEL", "claude-sonnet-4-6"))
        spec = planner.generate_spec(prompt)

    _print_spec_summary(spec)

    # Persist spec
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    spec_path = out / "spec.json"
    with open(spec_path, "w", encoding="utf-8") as f:
        json.dump(spec.to_dict(), f, indent=2, ensure_ascii=False)
    print(f"[Planner] Spec saved → {spec_path}\n")

    # ---- Phase 2: Generation + Evaluation loop ------------------------------
    generator = GeneratorAgent(
        output_dir=str(out / "app"),
        model=os.getenv("GENERATOR_MODEL", "claude-sonnet-4-6"),
    )
    evaluator = EvaluatorAgent(
        model=os.getenv("EVALUATOR_MODEL", "claude-sonnet-4-6"),
        base_url=os.getenv("APP_BASE_URL", "http://localhost:3000"),
        playwright_mcp_url=os.getenv("PLAYWRIGHT_MCP_URL"),
    )

    sprints_to_run = _filter_sprints(spec.sprints, sprint_range)

    for sprint in sprints_to_run:
        _banner(f"Sprint {sprint.number}: {sprint.goal}", width=50)

        feedback = None
        attempt = 0

        while attempt <= max_retries:
            attempt += 1
            label = f"attempt {attempt}/{max_retries + 1}"

            print(f"[Generator] Implementing ({label}) …")
            generator.implement_sprint(spec, sprint, feedback)

            self_eval = generator.self_evaluate(spec, sprint)
            print(f"[Generator] Self-evaluation:\n  {self_eval.strip()[:300]}\n")

            print(f"[Evaluator] Testing sprint {sprint.number} ({label}) …")
            result = evaluator.evaluate(spec, sprint, str(out / "app"))

            # Save evaluation result
            eval_path = out / f"eval_sprint_{sprint.number}_attempt_{attempt}.json"
            with open(eval_path, "w", encoding="utf-8") as f:
                json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)

            if result.status == EvaluationStatus.PASS:
                print(f"[Evaluator] PASS  Sprint {sprint.number}")
                break
            else:
                failed = [c for c in result.criteria if not c.passed]
                print(
                    f"[Evaluator] FAIL  Sprint {sprint.number} – "
                    f"{len(failed)} criterion/criteria below threshold"
                )
                for c in failed:
                    print(f"  • {c.name}: {c.score:.2f} – {c.feedback}")

                if attempt > max_retries:
                    print(
                        f"[Pipeline] Sprint {sprint.number} failed after "
                        f"{max_retries + 1} attempts.  Continuing …"
                    )
                    break

                feedback = result

    _banner("Done")
    print(f"Output directory : {out.resolve()}")
    print(f"Application code : {(out / 'app').resolve()}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _banner(text: str, width: int = 60) -> None:
    print(f"\n{'=' * width}")
    print(f" {text}")
    print(f"{'=' * width}")


def _print_spec_summary(spec: ProductSpec) -> None:
    print(f"  Product  : {spec.name}")
    print(f"  Users    : {spec.target_users}")
    print(f"  Features : {len(spec.features)}")
    print(f"  Sprints  : {len(spec.sprints)}")


def _filter_sprints(
    sprints: list[Sprint],
    sprint_range: tuple[int, int] | None,
) -> list[Sprint]:
    if sprint_range is None:
        return sprints
    lo, hi = sprint_range
    return [s for s in sprints if lo <= s.number <= hi]


def _spec_from_dict(data: dict) -> ProductSpec:
    """Reconstruct a ProductSpec from its serialised dict form."""
    from models import Feature, Sprint, SprintTask

    features = [
        Feature(
            id=f["id"],
            name=f["name"],
            description=f["description"],
            acceptance_criteria=f.get("acceptance_criteria", []),
        )
        for f in data.get("features", [])
    ]
    sprints = [
        Sprint(
            number=s["number"],
            goal=s["goal"],
            tasks=[
                SprintTask(
                    id=t["id"],
                    feature_id=t.get("feature_id", ""),
                    description=t["description"],
                )
                for t in s.get("tasks", [])
            ],
        )
        for s in data.get("sprints", [])
    ]
    return ProductSpec(
        name=data["name"],
        description=data["description"],
        target_users=data.get("target_users", ""),
        features=features,
        sprints=sprints,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_sprint_range(value: str) -> tuple[int, int]:
    parts = value.split("-")
    if len(parts) == 1:
        n = int(parts[0])
        return (n, n)
    return (int(parts[0]), int(parts[1]))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI Product Planner – from idea to running app.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        help="1-4 line product description (or path to spec.json when --from-spec is set).",
    )
    parser.add_argument("--output", default="./output", help="Output directory (default: ./output).")
    parser.add_argument(
        "--sprints",
        help="Sprint range to run, e.g. '1-3' or '2'. Defaults to all.",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="Max Generator retries per sprint after an Evaluator FAIL (default: 3).",
    )
    parser.add_argument(
        "--from-spec",
        action="store_true",
        help="Treat the positional argument as a path to an existing spec.json.",
    )

    args = parser.parse_args()

    if not args.prompt:
        parser.print_help()
        sys.exit(1)

    sprint_range = _parse_sprint_range(args.sprints) if args.sprints else None

    run(
        prompt=args.prompt,
        output_dir=args.output,
        sprint_range=sprint_range,
        max_retries=args.retries,
        from_spec=args.prompt if args.from_spec else None,
    )


if __name__ == "__main__":
    main()
