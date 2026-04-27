"""Evaluator agent: tests a sprint's output via Playwright and scores it."""
from __future__ import annotations
import json
import subprocess
import time
import anthropic
from .models import ProductSpec, Sprint, SprintImplementation, EvalResult, EvalCriterion

MODEL = "claude-sonnet-4-6"

_SYSTEM = """\
You are a senior QA engineer evaluating a sprint's implementation.

You will:
1. Review the sprint goals and acceptance criteria.
2. Use the provided browser tools to interact with the live application.
3. Score each evaluation criterion from 0.0 to 1.0.
4. A sprint PASSES only when every criterion meets or exceeds its threshold.
5. Be specific: evidence must reference concrete actions you took and what you observed.

Be strict but fair. A criterion at 0.8 that needs 0.9 should still be marked failed.
"""

_EVAL_TOOL: dict = {
    "name": "submit_evaluation",
    "description": "Submit the final evaluation result for this sprint.",
    "input_schema": {
        "type": "object",
        "required": ["criteria", "bugs_found", "improvements", "detailed_feedback"],
        "properties": {
            "criteria": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["name", "threshold", "score", "passed", "evidence"],
                    "properties": {
                        "name": {"type": "string"},
                        "threshold": {"type": "number", "minimum": 0, "maximum": 1},
                        "score": {"type": "number", "minimum": 0, "maximum": 1},
                        "passed": {"type": "boolean"},
                        "evidence": {"type": "string"},
                    },
                },
            },
            "bugs_found": {"type": "array", "items": {"type": "string"}},
            "improvements": {"type": "array", "items": {"type": "string"}},
            "detailed_feedback": {"type": "string"},
        },
    },
}

_PLAYWRIGHT_TOOLS: list[dict] = [
    {
        "name": "navigate",
        "description": "Navigate the browser to a URL.",
        "input_schema": {
            "type": "object",
            "required": ["url"],
            "properties": {"url": {"type": "string"}},
        },
    },
    {
        "name": "click",
        "description": "Click an element identified by a CSS selector or visible text.",
        "input_schema": {
            "type": "object",
            "required": ["selector"],
            "properties": {
                "selector": {"type": "string"},
                "by_text": {"type": "boolean", "default": False},
            },
        },
    },
    {
        "name": "fill",
        "description": "Type text into an input field.",
        "input_schema": {
            "type": "object",
            "required": ["selector", "value"],
            "properties": {
                "selector": {"type": "string"},
                "value": {"type": "string"},
            },
        },
    },
    {
        "name": "get_text",
        "description": "Return the visible text content of an element.",
        "input_schema": {
            "type": "object",
            "required": ["selector"],
            "properties": {"selector": {"type": "string"}},
        },
    },
    {
        "name": "screenshot",
        "description": "Capture a screenshot and return a description of what is visible.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
        },
    },
    {
        "name": "assert_visible",
        "description": "Assert that an element or text is visible on the page.",
        "input_schema": {
            "type": "object",
            "required": ["selector"],
            "properties": {
                "selector": {"type": "string"},
                "by_text": {"type": "boolean", "default": False},
            },
        },
    },
    {
        "name": "api_request",
        "description": "Make an HTTP request and return the response body.",
        "input_schema": {
            "type": "object",
            "required": ["method", "url"],
            "properties": {
                "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"]},
                "url": {"type": "string"},
                "body": {"type": "object"},
                "headers": {"type": "object"},
            },
        },
    },
]

DEFAULT_CRITERIA = [
    ("feature_completeness", 0.8),
    ("ui_usability", 0.7),
    ("error_handling", 0.7),
    ("acceptance_criteria_coverage", 0.85),
]


def _dispatch_tool(name: str, args: dict, page) -> str:
    """Execute a Playwright tool call and return a string result."""
    try:
        if name == "navigate":
            page.goto(args["url"], timeout=10000)
            return f"Navigated to {args['url']}"

        elif name == "click":
            if args.get("by_text"):
                page.get_by_text(args["selector"]).click()
            else:
                page.locator(args["selector"]).click()
            return f"Clicked {args['selector']}"

        elif name == "fill":
            page.locator(args["selector"]).fill(args["value"])
            return f"Filled {args['selector']} with {args['value']!r}"

        elif name == "get_text":
            text = page.locator(args["selector"]).inner_text()
            return f"Text content: {text}"

        elif name == "screenshot":
            path = args.get("path", "/tmp/eval_screenshot.png")
            page.screenshot(path=path)
            return f"Screenshot saved to {path}"

        elif name == "assert_visible":
            if args.get("by_text"):
                visible = page.get_by_text(args["selector"]).is_visible()
            else:
                visible = page.locator(args["selector"]).is_visible()
            return f"{'Visible' if visible else 'NOT visible'}: {args['selector']}"

        elif name == "api_request":
            import urllib.request
            req = urllib.request.Request(
                args["url"],
                method=args["method"],
                headers=args.get("headers", {}),
            )
            if args.get("body"):
                req.data = json.dumps(args["body"]).encode()
                req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.read().decode()[:2000]

    except Exception as exc:
        return f"[tool error] {exc}"

    return "[unknown tool]"


def _run_with_playwright(
    client: anthropic.Anthropic,
    messages: list[dict],
    tools: list[dict],
    page,
) -> dict:
    all_tools = _PLAYWRIGHT_TOOLS + [_EVAL_TOOL]

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=8192,
            system=_SYSTEM,
            tools=all_tools,
            messages=messages,
        )

        tool_use_block = next((b for b in response.content if b.type == "tool_use"), None)
        if tool_use_block is None or tool_use_block.name == "submit_evaluation":
            if tool_use_block:
                return tool_use_block.input
            raise RuntimeError("Evaluator stopped without submitting evaluation")

        result = _dispatch_tool(tool_use_block.name, tool_use_block.input, page)

        messages = messages + [
            {"role": "assistant", "content": response.content},
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_block.id,
                        "content": result,
                    }
                ],
            },
        ]


def _run_static(
    client: anthropic.Anthropic,
    messages: list[dict],
) -> dict:
    """Fallback evaluation without a live browser — Claude reasons from code alone."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=8192,
        system=_SYSTEM + "\n\nNote: No live browser is available. Evaluate based on the code files provided.",
        tools=[_EVAL_TOOL],
        tool_choice={"type": "tool", "name": "submit_evaluation"},
        messages=messages,
    )
    tool_use_block = next(b for b in response.content if b.type == "tool_use")
    return tool_use_block.input


def _build_eval_prompt(
    spec: ProductSpec,
    sprint: Sprint,
    impl: SprintImplementation,
    criteria: list[tuple[str, float]],
) -> list[dict]:
    sprint_features = spec.get_features_for_sprint(sprint)

    ac_block = "\n".join(
        f"### {f.name}\n" + "\n".join(f"- {c}" for c in f.acceptance_criteria)
        for f in sprint_features
    )

    code_block = "\n\n".join(
        f"--- {file.path} ---\n{file.content}"
        for file in impl.files
    )

    criteria_block = "\n".join(
        f"- {name}: threshold {threshold:.0%}" for name, threshold in criteria
    )

    return [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"# Evaluation: Sprint {sprint.number} — {sprint.name}\n\n"
                        f"## App URL\n{impl.app_url}\n\n"
                        f"## Start command\n`{impl.start_command}`\n\n"
                        f"## Sprint goals\n" + "\n".join(f"- {g}" for g in sprint.goals) + "\n\n"
                        f"## Acceptance criteria\n{ac_block}\n\n"
                        f"## Evaluation criteria (name: threshold)\n{criteria_block}\n\n"
                        f"## Implementation self-evaluation\n{impl.self_evaluation}\n\n"
                        f"## Known limitations\n" + "\n".join(f"- {l}" for l in impl.known_limitations)
                    ),
                    "cache_control": {"type": "ephemeral"},
                },
                {
                    "type": "text",
                    "text": f"\n## Source files\n\n{code_block}\n\nBegin evaluation now.",
                },
            ],
        }
    ]


def evaluate(
    spec: ProductSpec,
    sprint: Sprint,
    impl: SprintImplementation,
    criteria: list[tuple[str, float]] | None = None,
    *,
    use_playwright: bool = True,
    verbose: bool = False,
) -> EvalResult:
    """Evaluate *impl* against the sprint goals and return an EvalResult."""
    if criteria is None:
        criteria = DEFAULT_CRITERIA

    client = anthropic.Anthropic()

    if verbose:
        print(f"[Evaluator] Evaluating sprint {sprint.number}: {sprint.name}")

    messages = _build_eval_prompt(spec, sprint, impl, criteria)

    raw: dict | None = None

    if use_playwright:
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                page = browser.new_page()
                try:
                    raw = _run_with_playwright(client, messages, _PLAYWRIGHT_TOOLS, page)
                finally:
                    browser.close()
        except ImportError:
            if verbose:
                print("[Evaluator] Playwright not installed — falling back to static analysis")
        except Exception as exc:
            if verbose:
                print(f"[Evaluator] Playwright failed ({exc}) — falling back to static analysis")

    if raw is None:
        raw = _run_static(client, messages)

    result = EvalResult.from_tool_input(sprint.number, raw)

    if verbose:
        status = "PASSED" if result.overall_passed else "FAILED"
        print(f"[Evaluator] Sprint {sprint.number} {status}")
        for c in result.criteria:
            mark = "✓" if c.passed else "✗"
            print(f"  {mark} {c.name}: {c.score:.2f} / {c.threshold:.2f}")

    return result
