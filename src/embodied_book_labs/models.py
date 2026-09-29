from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Pose:
    frame: str
    xyz: list[float]
    yaw: float = 0.0


@dataclass
class ObjectState:
    object_id: str
    category: str
    color: str
    pose: Pose
    confidence: float
    observed_at: float


@dataclass
class SceneState:
    scene_id: str
    version: int
    timestamp: float
    body: dict[str, Any]
    localization: dict[str, Any]
    objects: list[ObjectState]
    environment: dict[str, Any]


@dataclass
class TaskSpec:
    task_id: str
    instruction: str
    target_object_id: str | None
    recipient_id: str | None
    goal: dict[str, Any]
    constraints: list[str]
    unknowns: list[str]
    scene_ref: tuple[str, int]


@dataclass
class PlanStep:
    step_id: str
    skill: str
    arguments: dict[str, Any]
    preconditions: list[str]
    expected_effects: list[str]


@dataclass
class PlanSpec:
    plan_id: str
    task_id: str
    scene_ref: tuple[str, int]
    steps: list[PlanStep]
    replan_when: list[str]


@dataclass
class MotionCheck:
    feasible: bool
    reason: str
    clearance_m: float
    waypoints: list[list[float]]


@dataclass
class RuntimeEvent:
    t: float
    event_type: str
    status: str
    detail: dict[str, Any] = field(default_factory=dict)


def to_dict(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    if isinstance(value, list):
        return [to_dict(item) for item in value]
    return value
