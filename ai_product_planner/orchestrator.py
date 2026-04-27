"""Orchestrator: drives the Planner → Generator → Evaluator pipeline."""
from __future__ import annotations
import os
import json
import pathlib
from dataclasses import dataclass, field
from .models import ProductSpec, SprintImplementation, EvalResult
from . import planner, generator, evaluator

MAX_RETRIES = 3


@dataclass
class SprintRecord:
    sprint_number: int
    attempts: list[SprintImplementation] = field(default_factory=list)
    evals: list[EvalResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return bool(self.evals) and self.evals[-1].overall_passed

    @property
    def final_impl(self) -> SprintImplementation | None:
        return self.attempts[-1] if self.attempts else None


@dataclass
class RunResult:
    spec: ProductSpec
    records: list[SprintRecord]
    output_dir: pathlib.Path

    @property
    def succeeded_sprints(self) -> list[SprintRecord]:
        return [r for r in self.records if r.passed]

    @property
    def failed_sprints(self) -> list[SprintRecord]:
        return [r for r in self.records if not r.passed]


def _write_files(impl: SprintImplementation, output_dir: pathlib.Path) -> None:
    for gf in impl.files:
        dest = output_dir / gf.path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(gf.content, encoding="utf-8")


def _save_spec(spec: ProductSpec, output_dir: pathlib.Path) -> None:
    (output_dir / ".ai_planner").mkdir(exist_ok=True)
    (output_dir / ".ai_planner" / "spec.json").write_text(
        spec.model_dump_json(indent=2), encoding="utf-8"
    )


def _save_record(record: SprintRecord, output_dir: pathlib.Path) -> None:
    meta_dir = output_dir / ".ai_planner" / f"sprint_{record.sprint_number:02d}"
    meta_dir.mkdir(parents=True, exist_ok=True)
    if record.evals:
        last_eval = record.evals[-1]
        (meta_dir / "eval.json").write_text(
            last_eval.model_dump_json(indent=2), encoding="utf-8"
        )


def run(
    idea: str,
    output_dir: str | pathlib.Path = "output",
    *,
    sprint_range: tuple[int, int] | None = None,
    eval_criteria: list[tuple[str, float]] | None = None,
    use_playwright: bool = True,
    verbose: bool = True,
) -> RunResult:
    """
    Full pipeline: plan → generate each sprint → evaluate → retry on failure.

    Args:
        idea:          1-4 line product idea.
        output_dir:    Directory where generated code is written.
        sprint_range:  (first, last) sprint numbers to execute (1-indexed, inclusive).
                       Defaults to all sprints.
        eval_criteria: List of (criterion_name, threshold) pairs.
        use_playwright: Attempt Playwright browser tests in the Evaluator.
        verbose:       Print progress to stdout.
    """
    output_dir = pathlib.Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Phase 1: Plan ────────────────────────────────────────────────────────
    spec = planner.plan(idea, verbose=verbose)
    _save_spec(spec, output_dir)

    if verbose:
        print(f"\n{'='*60}")
        print(f"Product: {spec.product_name}")
        print(f"Features: {len(spec.features)}  Sprints: {len(spec.sprints)}")
        print(f"{'='*60}\n")

    # Filter sprints if requested
    sprints_to_run = spec.sprints
    if sprint_range:
        lo, hi = sprint_range
        sprints_to_run = [s for s in spec.sprints if lo <= s.number <= hi]

    records: list[SprintRecord] = []
    prior_impls: list[SprintImplementation] = []

    # ── Phase 2: Sprint loop ─────────────────────────────────────────────────
    for sprint in sprints_to_run:
        if verbose:
            print(f"\n[Sprint {sprint.number}/{len(spec.sprints)}] {sprint.name}")
            print("-" * 50)

        record = SprintRecord(sprint_number=sprint.number)
        last_eval: EvalResult | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            if verbose and attempt > 1:
                print(f"  [Retry {attempt}/{MAX_RETRIES}]")

            # Generate
            impl = generator.generate(
                spec, sprint, prior_impls,
                eval_feedback=last_eval,
                verbose=verbose,
            )
            record.attempts.append(impl)
            _write_files(impl, output_dir)

            # Evaluate
            result = evaluator.evaluate(
                spec, sprint, impl,
                criteria=eval_criteria,
                use_playwright=use_playwright,
                verbose=verbose,
            )
            record.evals.append(result)
            last_eval = result
            _save_record(record, output_dir)

            if result.overall_passed:
                break

            if attempt == MAX_RETRIES and verbose:
                print(f"  [Sprint {sprint.number}] Exhausted retries — moving on")

        # Carry the last implementation forward as context for subsequent sprints
        if record.final_impl:
            prior_impls.append(record.final_impl)

        records.append(record)

    return RunResult(spec=spec, records=records, output_dir=output_dir)


def load_spec(output_dir: str | pathlib.Path) -> ProductSpec:
    """Reload a previously generated ProductSpec from disk."""
    path = pathlib.Path(output_dir) / ".ai_planner" / "spec.json"
    return ProductSpec.model_validate_json(path.read_text(encoding="utf-8"))
