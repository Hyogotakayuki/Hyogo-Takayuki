from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class UserStory(BaseModel):
    title: str
    as_a: str
    i_want: str
    so_that: str


class Feature(BaseModel):
    id: int
    name: str
    description: str
    priority: Literal["must-have", "should-have", "nice-to-have"]
    user_stories: list[UserStory]
    acceptance_criteria: list[str]


class Sprint(BaseModel):
    number: int
    name: str
    feature_ids: list[int]
    goals: list[str]
    deliverables: list[str]
    definition_of_done: list[str]


class ProductSpec(BaseModel):
    product_name: str
    overview: str
    target_users: str
    core_value_proposition: str
    features: list[Feature]
    sprints: list[Sprint]
    out_of_scope: list[str]

    def get_sprint(self, number: int) -> Sprint | None:
        return next((s for s in self.sprints if s.number == number), None)

    def get_features_for_sprint(self, sprint: Sprint) -> list[Feature]:
        return [f for f in self.features if f.id in sprint.feature_ids]


class GeneratedFile(BaseModel):
    path: str
    content: str


class SprintImplementation(BaseModel):
    sprint_number: int
    implemented_features: list[str]
    files: list[GeneratedFile]
    self_evaluation: str
    known_limitations: list[str]
    start_command: str
    app_url: str


class EvalCriterion(BaseModel):
    name: str
    threshold: float
    score: float
    passed: bool
    evidence: str


class EvalResult(BaseModel):
    sprint_number: int
    overall_passed: bool
    criteria: list[EvalCriterion]
    bugs_found: list[str]
    improvements: list[str]
    detailed_feedback: str

    @classmethod
    def from_tool_input(cls, sprint_number: int, data: dict) -> EvalResult:
        criteria = [EvalCriterion(**c) for c in data["criteria"]]
        overall = all(c.passed for c in criteria)
        return cls(
            sprint_number=sprint_number,
            overall_passed=overall,
            criteria=criteria,
            bugs_found=data.get("bugs_found", []),
            improvements=data.get("improvements", []),
            detailed_feedback=data.get("detailed_feedback", ""),
        )
