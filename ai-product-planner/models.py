from dataclasses import dataclass, field
from typing import List
from enum import Enum


class EvaluationStatus(Enum):
    PASS = "pass"
    FAIL = "fail"


@dataclass
class Feature:
    id: str
    name: str
    description: str
    acceptance_criteria: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "acceptance_criteria": self.acceptance_criteria,
        }


@dataclass
class SprintTask:
    id: str
    feature_id: str
    description: str

    def to_dict(self):
        return {
            "id": self.id,
            "feature_id": self.feature_id,
            "description": self.description,
        }


@dataclass
class Sprint:
    number: int
    goal: str
    tasks: List[SprintTask] = field(default_factory=list)

    def to_dict(self):
        return {
            "number": self.number,
            "goal": self.goal,
            "tasks": [t.to_dict() for t in self.tasks],
        }


@dataclass
class ProductSpec:
    name: str
    description: str
    target_users: str
    features: List[Feature] = field(default_factory=list)
    sprints: List[Sprint] = field(default_factory=list)

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "target_users": self.target_users,
            "features": [f.to_dict() for f in self.features],
            "sprints": [s.to_dict() for s in self.sprints],
        }


@dataclass
class EvaluationCriterion:
    name: str
    description: str
    threshold: float = 0.7
    score: float = 0.0
    passed: bool = False
    feedback: str = ""

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "threshold": self.threshold,
            "score": self.score,
            "passed": self.passed,
            "feedback": self.feedback,
        }


@dataclass
class EvaluationResult:
    sprint_number: int
    status: EvaluationStatus
    criteria: List[EvaluationCriterion] = field(default_factory=list)
    bugs: List[str] = field(default_factory=list)
    improvements: List[str] = field(default_factory=list)
    overall_feedback: str = ""

    def to_dict(self):
        return {
            "sprint_number": self.sprint_number,
            "status": self.status.value,
            "criteria": [c.to_dict() for c in self.criteria],
            "bugs": self.bugs,
            "improvements": self.improvements,
            "overall_feedback": self.overall_feedback,
        }
