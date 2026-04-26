"""Planner agent: expands a 1-4 line idea into a detailed product specification.

Design principle: focus on WHAT to build, not HOW.  No database schemas,
no library choices, no architectural decisions – those belong to the Generator.
"""

import json
import anthropic
from models import Feature, ProductSpec, Sprint, SprintTask


_SYSTEM = """\
You are a product strategist who turns brief ideas into actionable product specifications.

Rules:
- Describe features from the USER's perspective, not the engineer's.
- Do NOT specify technologies, frameworks, database schemas, or code structure.
- Every acceptance criterion must be observable and testable through a UI or API.
- Keep sprints small: each one should be independently shippable.
"""

_SCHEMA_EXAMPLE = {
    "name": "Product name",
    "description": "2-3 sentences explaining the product and its core value.",
    "target_users": "Who will use this product and why.",
    "features": [
        {
            "id": "F001",
            "name": "Feature name",
            "description": "What this does for the user.",
            "acceptance_criteria": [
                "User can perform action X and sees result Y.",
            ],
        }
    ],
    "sprints": [
        {
            "number": 1,
            "goal": "One sentence describing the value this sprint delivers.",
            "tasks": [
                {
                    "id": "T001",
                    "feature_id": "F001",
                    "description": "What needs to be built (user-facing, not technical).",
                }
            ],
        }
    ],
}


class PlannerAgent:
    def __init__(self, model: str = "claude-sonnet-4-6"):
        self.client = anthropic.Anthropic()
        self.model = model

    def generate_spec(self, prompt: str) -> ProductSpec:
        """Turn a 1-4 line prompt into a full ProductSpec."""
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
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Create a detailed product specification for this idea:\n\n{prompt}\n\n"
                        "Requirements:\n"
                        "- 8 to 16 features that together make the product compelling\n"
                        "- 5 to 10 sprints; Sprint 1 must be a runnable MVP\n"
                        "- 2 to 5 tasks per sprint\n"
                        "- Acceptance criteria must be specific and testable\n\n"
                        "Output ONLY valid JSON matching this schema (no markdown fences):\n"
                        + json.dumps(_SCHEMA_EXAMPLE, indent=2, ensure_ascii=False)
                    ),
                }
            ],
        )

        raw = response.content[0].text.strip()
        # Strip markdown code fences if the model includes them
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.rsplit("```", 1)[0].strip()

        data = json.loads(raw)
        return _parse(data)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse(data: dict) -> ProductSpec:
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
