"""Generator agent: implements sprint tasks one at a time and self-evaluates.

Each sprint ends with a brief self-assessment before handing off to the Evaluator.
When the Evaluator returns a FAIL, the Generator receives the concrete feedback
and retries with that context injected into the prompt.
"""

import json
import subprocess
from pathlib import Path
from typing import Optional

import anthropic

from models import EvaluationResult, ProductSpec, Sprint


_SYSTEM = """\
You are a senior software engineer implementing product features sprint by sprint.

Guidelines:
- Choose technologies that fit the product naturally; don't over-engineer.
- Write complete, runnable code – no stubs, no TODOs.
- Each sprint must leave the application in a working, testable state.
- Reuse and extend what already exists; don't rewrite working code.
- When retrying after a failed evaluation, fix ONLY the reported issues.
"""

_SELF_EVAL_PROMPT = """\
Review your implementation for this sprint and assess:
1. Feature completeness – are all tasks fully implemented?
2. Acceptance criteria – does the code satisfy every criterion?
3. Integration – does this sprint's work fit cleanly with previous sprints?
4. Runnability – can the application be started and manually tested right now?

Write a concise self-evaluation (3-5 sentences).  Be honest about any gaps.
"""

_TOOLS = [
    {
        "name": "write_file",
        "description": "Write (or overwrite) a file in the project output directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path relative to the project root."},
                "content": {"type": "string", "description": "Complete file content."},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "read_file",
        "description": "Read an existing file from the project output directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path relative to the project root."},
            },
            "required": ["path"],
        },
    },
    {
        "name": "list_files",
        "description": "List all files currently in the project output directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Sub-directory to list.  Omit for project root.",
                }
            },
        },
    },
    {
        "name": "run_command",
        "description": (
            "Run a shell command inside the project output directory "
            "(e.g. npm install, pip install -r requirements.txt)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
            },
            "required": ["command"],
        },
    },
]


class GeneratorAgent:
    def __init__(self, output_dir: str = "./output", model: str = "claude-sonnet-4-6"):
        self.client = anthropic.Anthropic()
        self.model = model
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def implement_sprint(
        self,
        spec: ProductSpec,
        sprint: Sprint,
        feedback: Optional[EvaluationResult] = None,
    ) -> None:
        """Implement all tasks for *sprint*, optionally fixing *feedback* issues."""
        messages = [{"role": "user", "content": self._build_prompt(spec, sprint, feedback)}]
        self._run_agentic_loop(messages)

    def self_evaluate(self, spec: ProductSpec, sprint: Sprint) -> str:
        """Return a short self-assessment of the just-completed sprint."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"You just implemented Sprint {sprint.number}: {sprint.goal}\n\n"
                        f"Tasks were:\n"
                        + "\n".join(f"- {t.description}" for t in sprint.tasks)
                        + f"\n\nExisting project files:\n{self._list_files_str()}\n\n"
                        + _SELF_EVAL_PROMPT
                    ),
                }
            ],
        )
        return response.content[0].text

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_prompt(
        self,
        spec: ProductSpec,
        sprint: Sprint,
        feedback: Optional[EvaluationResult],
    ) -> str:
        feature_ids = {t.feature_id for t in sprint.tasks}
        relevant = [f for f in spec.features if f.id in feature_ids]

        lines = [
            f"# Product: {spec.name}",
            spec.description,
            "",
            f"# Sprint {sprint.number}: {sprint.goal}",
            "",
            "## Tasks",
            *[f"- [{t.id}] {t.description}" for t in sprint.tasks],
            "",
            "## Features",
        ]
        for feat in relevant:
            lines += [
                f"### {feat.name}",
                feat.description,
                "Acceptance criteria:",
                *[f"- {c}" for c in feat.acceptance_criteria],
                "",
            ]

        lines += [
            "## Existing project files",
            self._list_files_str(),
            "",
        ]

        if feedback:
            lines += [
                "## FAILED EVALUATION – Fix the following issues",
                f"Overall: {feedback.overall_feedback}",
                "",
                "Bugs:",
                *[f"- {b}" for b in feedback.bugs],
                "",
                "Required improvements:",
                *[f"- {i}" for i in feedback.improvements],
                "",
                "Criterion scores:",
                *[
                    f"- {c.name}: {c.score:.2f} (threshold {c.threshold:.2f}) – {c.feedback}"
                    for c in feedback.criteria
                    if not c.passed
                ],
                "",
                "Fix ONLY the issues above.  Do not rewrite unrelated code.",
            ]
        else:
            lines.append(
                "Implement all tasks above.  Make sure the application can be "
                "started and manually tested when you are done."
            )

        return "\n".join(lines)

    def _run_agentic_loop(self, messages: list) -> None:
        while True:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=8096,
                system=[
                    {
                        "type": "text",
                        "text": _SYSTEM,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                tools=_TOOLS,
                messages=messages,
            )

            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                break

            if response.stop_reason == "tool_use":
                results = []
                for block in response.content:
                    if block.type == "tool_use":
                        output = self._dispatch_tool(block.name, block.input)
                        results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": output,
                            }
                        )
                messages.append({"role": "user", "content": results})
            else:
                break

    def _dispatch_tool(self, name: str, inp: dict) -> str:
        if name == "write_file":
            path = self.output_dir / inp["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(inp["content"], encoding="utf-8")
            return f"Written: {inp['path']}"

        if name == "read_file":
            path = self.output_dir / inp["path"]
            return path.read_text(encoding="utf-8") if path.exists() else f"Not found: {inp['path']}"

        if name == "list_files":
            sub = inp.get("directory", "")
            target = self.output_dir / sub if sub else self.output_dir
            if not target.exists():
                return f"Directory not found: {sub}"
            files = [
                str(p.relative_to(self.output_dir))
                for p in target.rglob("*")
                if p.is_file()
            ]
            return "\n".join(sorted(files)) if files else "(empty)"

        if name == "run_command":
            try:
                result = subprocess.run(
                    inp["command"],
                    shell=True,
                    cwd=self.output_dir,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                out = (result.stdout + result.stderr).strip()
                return out[:3000] if len(out) > 3000 else out
            except subprocess.TimeoutExpired:
                return "Command timed out after 120 s"

        return f"Unknown tool: {name}"

    def _list_files_str(self) -> str:
        files = sorted(
            str(p.relative_to(self.output_dir))
            for p in self.output_dir.rglob("*")
            if p.is_file() and not p.name.endswith(".json")
        )
        return "\n".join(files) if files else "(none yet)"
