"""Evaluator agent: tests the running application with Playwright MCP.

Each sprint is scored against five criteria (threshold 0.7).
Failing any criterion marks the sprint as FAIL and feeds concrete
bugs + improvements back to the Generator.

Playwright integration
----------------------
The agent is wired to the Playwright MCP server through Claude's tool-use
API.  In local development you can run the MCP server with:

    npx @playwright/mcp@latest --port 8931

and set the env var PLAYWRIGHT_MCP_URL=http://localhost:8931.

If the MCP server is not available the agent falls back to a lightweight
HTTP-only evaluation that exercises API endpoints directly.
"""

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

import anthropic

from models import (
    EvaluationCriterion,
    EvaluationResult,
    EvaluationStatus,
    ProductSpec,
    Sprint,
)


_SYSTEM = """\
You are a QA engineer performing acceptance testing on a web application.

Your job:
1. Navigate to the application and confirm it loads without errors.
2. Exercise each acceptance criterion listed in the sprint.
3. Try edge cases and look for broken UI, missing data, or unhelpful errors.
4. Record every bug and improvement you find.
5. Score each evaluation criterion from 0.0 to 1.0.
6. Submit your findings with the `report_evaluation` tool.

A sprint PASSES only when EVERY criterion scores ≥ 0.7.
Be rigorous but fair – the goal is a shippable product, not perfection.
"""

# Five universal evaluation dimensions and their descriptions shown to the model.
_CRITERIA_PROMPT = """\
Score each criterion 0.0–1.0 (threshold to pass: 0.7):

1. feature_completeness  – Are all sprint features present and reachable?
2. acceptance_criteria   – Do features satisfy their specified acceptance criteria?
3. user_experience       – Is the UI coherent, navigable, and free of obvious UX issues?
4. error_handling        – Does the app handle bad input / server errors gracefully?
5. performance           – Do pages and API responses feel acceptably fast (< 3 s)?
"""

_PLAYWRIGHT_TOOLS = [
    {
        "name": "playwright_navigate",
        "description": "Navigate the browser to a URL.",
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    },
    {
        "name": "playwright_screenshot",
        "description": "Capture a screenshot; returns a base64 PNG.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Optional save path."}},
        },
    },
    {
        "name": "playwright_click",
        "description": "Click on a page element by CSS selector or text.",
        "input_schema": {
            "type": "object",
            "properties": {"selector": {"type": "string"}},
            "required": ["selector"],
        },
    },
    {
        "name": "playwright_fill",
        "description": "Fill an input field.",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string"},
                "value": {"type": "string"},
            },
            "required": ["selector", "value"],
        },
    },
    {
        "name": "playwright_get_text",
        "description": "Return the visible text content of a page element.",
        "input_schema": {
            "type": "object",
            "properties": {"selector": {"type": "string"}},
            "required": ["selector"],
        },
    },
    {
        "name": "playwright_evaluate",
        "description": "Run a JavaScript expression in the browser and return the result.",
        "input_schema": {
            "type": "object",
            "properties": {"expression": {"type": "string"}},
            "required": ["expression"],
        },
    },
    {
        "name": "check_api",
        "description": "Send an HTTP request to an API endpoint and return the status + body.",
        "input_schema": {
            "type": "object",
            "properties": {
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"],
                },
                "url": {"type": "string"},
                "body": {"type": "object", "description": "JSON body for POST/PUT/PATCH."},
                "headers": {
                    "type": "object",
                    "description": "Extra HTTP headers.",
                },
            },
            "required": ["method", "url"],
        },
    },
    {
        "name": "report_evaluation",
        "description": "Submit the final evaluation report.  Call this exactly once.",
        "input_schema": {
            "type": "object",
            "properties": {
                "passed": {"type": "boolean"},
                "criteria": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "score": {"type": "number"},
                            "passed": {"type": "boolean"},
                            "feedback": {"type": "string"},
                        },
                        "required": ["name", "score", "passed", "feedback"],
                    },
                },
                "bugs": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Concrete, reproducible bug descriptions.",
                },
                "improvements": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific improvement suggestions.",
                },
                "overall_feedback": {"type": "string"},
            },
            "required": ["passed", "criteria", "bugs", "improvements", "overall_feedback"],
        },
    },
]


class EvaluatorAgent:
    def __init__(
        self,
        model: str = "claude-sonnet-4-6",
        base_url: str = "http://localhost:3000",
        playwright_mcp_url: Optional[str] = None,
    ):
        self.client = anthropic.Anthropic()
        self.model = model
        self.base_url = base_url
        # Allow override via env var so CI can point at a running MCP server.
        self.playwright_mcp_url = playwright_mcp_url or os.getenv("PLAYWRIGHT_MCP_URL")
        self._playwright_session: Optional[object] = None  # lazy-init if MCP available

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def evaluate(
        self,
        spec: ProductSpec,
        sprint: Sprint,
        output_dir: str,
    ) -> EvaluationResult:
        """Run acceptance tests for *sprint* and return a structured result."""
        feature_ids = {t.feature_id for t in sprint.tasks}
        relevant = [f for f in spec.features if f.id in feature_ids]

        user_message = self._build_prompt(spec, sprint, relevant)
        messages = [{"role": "user", "content": user_message}]

        report: Optional[dict] = None

        while True:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=[
                    {
                        "type": "text",
                        "text": _SYSTEM,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                tools=_PLAYWRIGHT_TOOLS,
                messages=messages,
            )

            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                break

            if response.stop_reason == "tool_use":
                results = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue
                    if block.name == "report_evaluation":
                        report = block.input
                        results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": "Report received.  Evaluation complete.",
                            }
                        )
                    else:
                        output = self._dispatch_tool(block.name, block.input)
                        results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": output,
                            }
                        )
                messages.append({"role": "user", "content": results})

                if report is not None:
                    break
            else:
                break

        if report:
            return _parse_report(sprint.number, report)

        # Fallback when model never called report_evaluation
        return EvaluationResult(
            sprint_number=sprint.number,
            status=EvaluationStatus.FAIL,
            criteria=[
                EvaluationCriterion(
                    name="evaluation_error",
                    description="Evaluation loop exited without a report.",
                    threshold=0.7,
                    score=0.0,
                    passed=False,
                    feedback="The evaluator did not submit a report – the application may not be running.",
                )
            ],
            bugs=["Application may not be reachable at " + self.base_url],
            improvements=["Ensure the application starts and listens on the expected port."],
            overall_feedback="Evaluation failed to complete.",
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_prompt(self, spec: ProductSpec, sprint: Sprint, relevant_features: list) -> str:
        lines = [
            f"# Evaluate Sprint {sprint.number}: {sprint.goal}",
            f"Product: {spec.name} – {spec.description}",
            f"Application URL: {self.base_url}",
            "",
            "## Features to test",
        ]
        for feat in relevant_features:
            lines += [
                f"### {feat.name}",
                feat.description,
                "Acceptance criteria:",
                *[f"- {c}" for c in feat.acceptance_criteria],
                "",
            ]

        lines += [
            _CRITERIA_PROMPT,
            "## Instructions",
            "1. Navigate to the application and take a screenshot.",
            "2. Work through each acceptance criterion methodically.",
            "3. Try at least one edge case per feature.",
            "4. Use check_api to verify relevant endpoints directly.",
            "5. Call report_evaluation with your findings.",
        ]
        return "\n".join(lines)

    def _dispatch_tool(self, name: str, inp: dict) -> str:
        if name == "check_api":
            return self._http_request(
                inp["method"],
                inp["url"],
                inp.get("body"),
                inp.get("headers"),
            )

        # Playwright tools: proxy to MCP server if available, otherwise stub.
        if self.playwright_mcp_url:
            return self._call_playwright_mcp(name, inp)

        return (
            f"[Playwright stub] {name}({json.dumps(inp)}) – "
            "Set PLAYWRIGHT_MCP_URL to enable real browser testing."
        )

    def _http_request(
        self,
        method: str,
        url: str,
        body: Optional[dict],
        headers: Optional[dict],
    ) -> str:
        try:
            data = json.dumps(body).encode() if body else None
            req = urllib.request.Request(url, data=data, method=method)
            req.add_header("Content-Type", "application/json")
            for k, v in (headers or {}).items():
                req.add_header(k, v)
            with urllib.request.urlopen(req, timeout=10) as resp:
                body_text = resp.read().decode("utf-8", errors="replace")[:2000]
                return f"HTTP {resp.status}\n{body_text}"
        except urllib.error.HTTPError as e:
            body_text = e.read().decode("utf-8", errors="replace")[:500]
            return f"HTTP {e.code} {e.reason}\n{body_text}"
        except Exception as exc:
            return f"Request failed: {exc}"

    def _call_playwright_mcp(self, tool_name: str, inp: dict) -> str:
        """Forward a Playwright tool call to the MCP server's REST bridge."""
        try:
            payload = {"tool": tool_name, "input": inp}
            data = json.dumps(payload).encode()
            req = urllib.request.Request(
                f"{self.playwright_mcp_url}/call",
                data=data,
                method="POST",
            )
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8", errors="replace")[:4000]
        except Exception as exc:
            return f"Playwright MCP call failed: {exc}"


# ---------------------------------------------------------------------------
# Parse helpers
# ---------------------------------------------------------------------------

def _parse_report(sprint_number: int, report: dict) -> EvaluationResult:
    criteria = [
        EvaluationCriterion(
            name=c["name"],
            description=c.get("feedback", ""),
            threshold=0.7,
            score=float(c.get("score", 0.0)),
            passed=bool(c.get("passed", False)),
            feedback=c.get("feedback", ""),
        )
        for c in report.get("criteria", [])
    ]

    all_pass = report.get("passed", False) and all(c.passed for c in criteria)

    return EvaluationResult(
        sprint_number=sprint_number,
        status=EvaluationStatus.PASS if all_pass else EvaluationStatus.FAIL,
        criteria=criteria,
        bugs=report.get("bugs", []),
        improvements=report.get("improvements", []),
        overall_feedback=report.get("overall_feedback", ""),
    )
