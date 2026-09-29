from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass
class Pose:
    frame: str
    xyz: list[float]
    yaw: float = 0.0
    covariance_xyz: list[float] = field(default_factory=list)


@dataclass
class ObjectState:
    object_id: str
    category: str
    color: str
    pose: Pose
    confidence: float
    observed_at: float
    attributes: dict[str, Any] = field(default_factory=dict)
    visibility: str = "visible"
    source: str = "vision"
    evidence_refs: list[str] = field(default_factory=list)
    relations: list[dict[str, Any]] = field(default_factory=list)
    affordance_candidates: list[dict[str, Any]] = field(default_factory=list)
    validity: dict[str, Any] = field(default_factory=lambda: {"status": "usable"})


@dataclass
class SceneState:
    scene_id: str
    version: int
    timestamp: float
    body: dict[str, Any]
    localization: dict[str, Any]
    objects: list[ObjectState]
    environment: dict[str, Any]
    schema_version: int = 1
    session_id: str = "session_blue_cup_01"
    time: dict[str, Any] = field(default_factory=dict)
    map_state: dict[str, Any] = field(default_factory=dict)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    validity: dict[str, Any] = field(default_factory=lambda: {"status": "usable", "invalid_fields": []})


@dataclass
class TaskSpec:
    task_id: str
    instruction: str
    target_object_id: Optional[str]
    recipient_id: Optional[str]
    goal: dict[str, Any]
    constraints: list[str]
    unknowns: list[str]
    scene_ref: tuple[str, int]
    spec_version: int = 1
    intent: str = "deliver_object"
    candidate_object_ids: list[str] = field(default_factory=list)
    success_conditions: list[str] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    clarification_questions: list[str] = field(default_factory=list)
    status: str = "resolved"
    planning_status: str = "ready"
    ready_for_physical_execution: bool = True


@dataclass
class PlanStep:
    step_id: str
    skill: str
    arguments: dict[str, Any]
    preconditions: list[str]
    expected_effects: list[str]
    contract_version: str = "1.0"
    timeout_s: float = 30.0
    resources: list[str] = field(default_factory=list)
    failure_modes: list[str] = field(default_factory=list)


@dataclass
class PlanSpec:
    plan_id: str
    task_id: str
    scene_ref: tuple[str, int]
    steps: list[PlanStep]
    replan_when: list[str]
    spec_version: int = 1
    status: str = "valid"
    validation: list[dict[str, Any]] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    estimated_cost: dict[str, float] = field(default_factory=dict)
    risk_controls: list[str] = field(default_factory=list)


@dataclass
class MotionCheck:
    feasible: bool
    reason: str
    clearance_m: float
    waypoints: list[list[float]]
    scene_ref: Optional[tuple[str, int]] = None
    model: str = "teaching_2d_mobile_manipulator"
    failure_category: Optional[str] = None
    constraints_checked: list[str] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)
    assumptions: list[str] = field(default_factory=list)


@dataclass
class RuntimeEvent:
    t: float
    event_type: str
    status: str
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class RuntimeState:
    runtime_state_id: str
    runtime_version: int
    task_ref: tuple[str, int]
    plan_ref: tuple[str, int]
    plan_state_ref: tuple[str, int]
    current_scene_ref: tuple[str, int]
    task_status: str
    current_node: Optional[str]
    completed_nodes: list[str]
    facts: list[str]
    evidence: list[dict[str, Any]]
    recovery_count: int = 0
    final_reason: str = ""


def to_dict(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    if isinstance(value, list):
        return [to_dict(item) for item in value]
    return value
