"""Planner agent: expands a 1-4 line idea into a full ProductSpec."""
from __future__ import annotations
import json
import anthropic
from .models import ProductSpec

MODEL = "claude-sonnet-4-6"

_SYSTEM = """\
You are an expert product strategist. Your job is to expand a brief product idea into a \
comprehensive product specification.

Rules:
- Focus on WHAT the product does, never HOW to implement it technically.
- Do not prescribe databases, frameworks, data structures, or algorithms.
- Features must be user-facing and testable from the outside.
- Acceptance criteria must be observable behaviours, not implementation steps.
- Generate between 8 and 20 features grouped into 5-12 sprints.
- Each sprint should deliver visible, working functionality end-to-end.
- out_of_scope should list things users might expect but you deliberately exclude v1.
"""

_SPEC_TOOL: dict = {
    "name": "create_product_spec",
    "description": "Submit the complete product specification.",
    "input_schema": {
        "type": "object",
        "required": [
            "product_name", "overview", "target_users",
            "core_value_proposition", "features", "sprints", "out_of_scope",
        ],
        "properties": {
            "product_name": {"type": "string"},
            "overview": {"type": "string", "description": "2-3 sentences describing the product."},
            "target_users": {"type": "string"},
            "core_value_proposition": {"type": "string"},
            "features": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "name", "description", "priority", "user_stories", "acceptance_criteria"],
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "priority": {"type": "string", "enum": ["must-have", "should-have", "nice-to-have"]},
                        "user_stories": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["title", "as_a", "i_want", "so_that"],
                                "properties": {
                                    "title": {"type": "string"},
                                    "as_a": {"type": "string"},
                                    "i_want": {"type": "string"},
                                    "so_that": {"type": "string"},
                                },
                            },
                        },
                        "acceptance_criteria": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
            "sprints": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["number", "name", "feature_ids", "goals", "deliverables", "definition_of_done"],
                    "properties": {
                        "number": {"type": "integer"},
                        "name": {"type": "string"},
                        "feature_ids": {"type": "array", "items": {"type": "integer"}},
                        "goals": {"type": "array", "items": {"type": "string"}},
                        "deliverables": {"type": "array", "items": {"type": "string"}},
                        "definition_of_done": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
            "out_of_scope": {"type": "array", "items": {"type": "string"}},
        },
    },
}


def plan(idea: str, *, verbose: bool = False) -> ProductSpec:
    """Expand *idea* (1-4 lines) into a ProductSpec."""
    client = anthropic.Anthropic()

    if verbose:
        print(f"[Planner] Expanding idea: {idea!r}")

    response = client.messages.create(
        model=MODEL,
        max_tokens=8192,
        system=_SYSTEM,
        tools=[_SPEC_TOOL],
        tool_choice={"type": "tool", "name": "create_product_spec"},
        messages=[
            {
                "role": "user",
                "content": (
                    "Expand the following product idea into a full specification:\n\n"
                    f"{idea.strip()}"
                ),
            }
        ],
    )

    tool_use_block = next(b for b in response.content if b.type == "tool_use")
    spec_data = tool_use_block.input

    if verbose:
        feature_count = len(spec_data.get("features", []))
        sprint_count = len(spec_data.get("sprints", []))
        print(f"[Planner] Generated spec: {feature_count} features, {sprint_count} sprints")

    return ProductSpec(**spec_data)
