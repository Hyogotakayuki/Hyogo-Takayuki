"""Generator agent: implements one sprint at a time from a ProductSpec."""
from __future__ import annotations
import json
import anthropic
from .models import ProductSpec, Sprint, SprintImplementation, GeneratedFile, EvalResult

MODEL = "claude-sonnet-4-6"

_SYSTEM = """\
You are a senior software engineer building a product sprint by sprint.

You receive:
- A product specification describing WHAT to build.
- The current sprint's goals and deliverables.
- (Optionally) feedback from the previous evaluation attempt.

Your job:
1. Implement all features assigned to this sprint as working, runnable code.
2. Write complete file contents — no placeholders, no "TODO" stubs.
3. Make the app launchable with a single shell command.
4. Perform an honest self-evaluation before handing off.

Do not invent features not in the spec. Do not omit features in the sprint scope.
"""

_IMPL_TOOL: dict = {
    "name": "submit_implementation",
    "description": "Submit the sprint implementation including all source files.",
    "input_schema": {
        "type": "object",
        "required": [
            "implemented_features", "files", "self_evaluation",
            "known_limitations", "start_command", "app_url",
        ],
        "properties": {
            "implemented_features": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Short description of each feature implemented.",
            },
            "files": {
                "type": "array",
                "description": "All files created or modified in this sprint.",
                "items": {
                    "type": "object",
                    "required": ["path", "content"],
                    "properties": {
                        "path": {"type": "string", "description": "Relative path from project root."},
                        "content": {"type": "string", "description": "Full file content."},
                    },
                },
            },
            "self_evaluation": {
                "type": "string",
                "description": "Honest assessment: what works, what is rough, what may fail evaluation.",
            },
            "known_limitations": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Known gaps or shortcuts taken in this sprint.",
            },
            "start_command": {
                "type": "string",
                "description": "Shell command to start the application (e.g. 'python app.py').",
            },
            "app_url": {
                "type": "string",
                "description": "URL where the running app can be reached (e.g. 'http://localhost:5000').",
            },
        },
    },
}


def _build_sprint_prompt(
    spec: ProductSpec,
    sprint: Sprint,
    prior_implementations: list[SprintImplementation],
    eval_feedback: EvalResult | None,
) -> list[dict]:
    sprint_features = spec.get_features_for_sprint(sprint)

    feature_block = "\n".join(
        f"## Feature {f.id}: {f.name} [{f.priority}]\n"
        f"{f.description}\n"
        "Acceptance criteria:\n"
        + "\n".join(f"- {c}" for c in f.acceptance_criteria)
        for f in sprint_features
    )

    sprint_block = (
        f"## Sprint {sprint.number}: {sprint.name}\n"
        f"Goals:\n" + "\n".join(f"- {g}" for g in sprint.goals) + "\n"
        f"Deliverables:\n" + "\n".join(f"- {d}" for d in sprint.deliverables) + "\n"
        f"Definition of done:\n" + "\n".join(f"- {d}" for d in sprint.definition_of_done)
    )

    prior_block = ""
    if prior_implementations:
        prior_block = "\n\n# Previously implemented sprints\n"
        for impl in prior_implementations:
            files_summary = ", ".join(f.path for f in impl.files)
            prior_block += (
                f"Sprint {impl.sprint_number}: {files_summary}\n"
                f"Start command: {impl.start_command}\n"
            )

    feedback_block = ""
    if eval_feedback and not eval_feedback.overall_passed:
        failed = [c for c in eval_feedback.criteria if not c.passed]
        feedback_block = "\n\n# ⚠ Evaluation FAILED — fix these issues before resubmitting\n"
        for c in failed:
            feedback_block += f"- [{c.name}] score {c.score:.2f} < threshold {c.threshold:.2f}: {c.evidence}\n"
        if eval_feedback.bugs_found:
            feedback_block += "\nBugs to fix:\n" + "\n".join(f"- {b}" for b in eval_feedback.bugs_found)
        feedback_block += f"\n\nFull feedback:\n{eval_feedback.detailed_feedback}"

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"# Product: {spec.product_name}\n"
                        f"{spec.overview}\n\n"
                        f"Target users: {spec.target_users}\n"
                        f"Value proposition: {spec.core_value_proposition}\n"
                    ),
                    # Cache the spec — it's reused across every sprint.
                    "cache_control": {"type": "ephemeral"},
                },
                {
                    "type": "text",
                    "text": (
                        f"\n# Features in scope for this sprint\n{feature_block}\n\n"
                        f"{sprint_block}"
                        f"{prior_block}"
                        f"{feedback_block}\n\n"
                        "Implement the sprint now and submit via the tool."
                    ),
                },
            ],
        }
    ]
    return messages


def generate(
    spec: ProductSpec,
    sprint: Sprint,
    prior_implementations: list[SprintImplementation],
    eval_feedback: EvalResult | None = None,
    *,
    verbose: bool = False,
) -> SprintImplementation:
    """Generate code for *sprint*, optionally incorporating *eval_feedback*."""
    client = anthropic.Anthropic()

    if verbose:
        action = "Fixing" if eval_feedback else "Implementing"
        print(f"[Generator] {action} sprint {sprint.number}: {sprint.name}")

    messages = _build_sprint_prompt(spec, sprint, prior_implementations, eval_feedback)

    response = client.messages.create(
        model=MODEL,
        max_tokens=16384,
        system=_SYSTEM,
        tools=[_IMPL_TOOL],
        tool_choice={"type": "tool", "name": "submit_implementation"},
        messages=messages,
        betas=["prompt-caching-2024-07-31"],
    )

    tool_use_block = next(b for b in response.content if b.type == "tool_use")
    data = tool_use_block.input

    files = [GeneratedFile(path=f["path"], content=f["content"]) for f in data["files"]]

    impl = SprintImplementation(
        sprint_number=sprint.number,
        implemented_features=data["implemented_features"],
        files=files,
        self_evaluation=data["self_evaluation"],
        known_limitations=data.get("known_limitations", []),
        start_command=data["start_command"],
        app_url=data["app_url"],
    )

    if verbose:
        print(f"[Generator] Sprint {sprint.number} done — {len(files)} file(s)")
        print(f"[Generator] Self-eval: {impl.self_evaluation[:120]}…")

    return impl
