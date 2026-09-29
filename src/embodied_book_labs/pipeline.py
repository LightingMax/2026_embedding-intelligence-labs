from __future__ import annotations

import copy
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Optional

from .models import (
    MotionCheck,
    ObjectState,
    PlanSpec,
    PlanStep,
    Pose,
    RuntimeEvent,
    RuntimeState,
    SceneState,
    TaskSpec,
    to_dict,
)


FAULTS = (
    "none",
    "target_moved",
    "path_blocked",
    "grasp_failed",
    "human_entered",
    "feedback_lost",
    "user_cancel",
)

SCENARIOS = (
    "nominal",
    "camera_blackout",
    "localization_lost",
    "depth_invalid",
    "target_moved",
    "ambiguous_target",
    "rule_conflict",
    "clearance_blocked",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def apply_scenario(raw: dict[str, Any], scenario: str) -> dict[str, Any]:
    """Apply one controlled perturbation while preserving the source fixture."""
    if scenario not in SCENARIOS:
        raise ValueError(f"unknown scenario: {scenario}")
    changed = copy.deepcopy(raw)
    if scenario == "camera_blackout":
        changed["vision"]["enabled"] = False
        changed["vision"]["objects"] = []
    elif scenario == "localization_lost":
        changed["localization"]["status"] = "relocalizing"
        changed["localization"]["base_pose"]["valid"] = False
    elif scenario == "depth_invalid":
        for item in changed["vision"]["objects"]:
            if item["object_id"] == "cup_blue":
                item["depth_valid"] = False
                item["pose"]["covariance_xyz"] = [0.25, 0.25, 0.35]
    elif scenario == "target_moved":
        changed["version"] += 1
        changed["timestamp"] += 0.5
        for item in changed["vision"]["objects"]:
            if item["object_id"] == "cup_blue":
                item["pose"]["xyz"][0] += 0.35
                item["observed_at"] = changed["timestamp"] - 0.02
    elif scenario == "ambiguous_target":
        changed["vision"]["objects"].append(
            {
                "object_id": "cup_blue_02",
                "category": "cup",
                "color": "blue",
                "pose": {"frame": "map", "xyz": [1.72, -0.18, 0.82], "yaw": 0.0},
                "confidence": 0.91,
                "observed_at": changed["timestamp"] - 0.03,
                "attributes": {"container_state": "empty"},
            }
        )
    elif scenario == "rule_conflict":
        changed["instruction"] = "请把带蓝色装饰的奖杯递给我"
    elif scenario == "clearance_blocked":
        changed["environment"]["minimum_clearance_m"] = 0.28
    return changed


def perceive(raw: dict[str, Any]) -> SceneState:
    """Chapter 1: fuse body, localization, and visual observations."""
    objects = []
    for item in raw["vision"]["objects"]:
        pose_data = item["pose"]
        depth_valid = bool(item.get("depth_valid", True))
        validity = {
            "status": "usable" if depth_valid else "semantic_only",
            "for_navigation": depth_valid,
            "for_manipulation": depth_valid,
        }
        objects.append(
            ObjectState(
                object_id=item["object_id"],
                category=item["category"],
                color=item["color"],
                pose=Pose(
                    frame=pose_data["frame"],
                    xyz=list(pose_data["xyz"]),
                    yaw=float(pose_data.get("yaw", 0.0)),
                    covariance_xyz=list(pose_data.get("covariance_xyz", [0.0025, 0.0025, 0.004])),
                ),
                confidence=float(item["confidence"]),
                observed_at=float(item["observed_at"]),
                attributes=copy.deepcopy(item.get("attributes", {})),
                visibility=item.get("visibility", "visible"),
                source=item.get("source", "head_rgbd_detector"),
                evidence_refs=list(item.get("evidence_refs", [f"rgb_region:{item['object_id']}", f"depth:{item['object_id']}"])),
                relations=copy.deepcopy(item.get("relations", [])),
                affordance_candidates=copy.deepcopy(item.get("affordance_candidates", [])),
                validity=validity,
            )
        )

    invalid_fields: list[str] = []
    if not raw["vision"].get("enabled", True):
        invalid_fields.append("objects.current_observation")
    if raw["localization"].get("status", "normal") != "normal":
        invalid_fields.append("robot.pose.map")
    if any(obj.validity["status"] != "usable" for obj in objects):
        invalid_fields.append("objects.precise_geometry")
    status = "usable" if not invalid_fields else "degraded"
    return SceneState(
        scene_id=raw["scene_id"],
        version=int(raw["version"]),
        timestamp=float(raw["timestamp"]),
        body=copy.deepcopy(raw["proprioception"]),
        localization=copy.deepcopy(raw["localization"]),
        objects=objects,
        environment=copy.deepcopy(raw["environment"]),
        schema_version=1,
        session_id=raw.get("session_id", "session_blue_cup_01"),
        time={
            "reference": float(raw["timestamp"]),
            "time_base": "simulation_clock",
            "max_age_s": 0.5,
        },
        map_state={
            "map_id": raw["localization"].get("map_id", "unknown"),
            "version": raw["localization"].get("map_version", 1),
            "frame_id": "map",
            "status": raw["localization"].get("status", "normal"),
        },
        evidence=[
            {"evidence_id": "proprioception:latest", "source": "joint_imu_contact", "timestamp": raw["timestamp"]},
            {"evidence_id": "localization:latest", "source": raw["localization"].get("method", "unknown"), "timestamp": raw["timestamp"]},
            {"evidence_id": "vision:latest", "source": raw["vision"].get("camera", "unknown"), "timestamp": raw["timestamp"]},
        ],
        validity={"status": status, "invalid_fields": invalid_fields},
    )


def _instruction_filters(instruction: str) -> tuple[Optional[str], Optional[str]]:
    lowered = instruction.lower()
    category: Optional[str] = None
    if "奖杯" in instruction or "trophy" in lowered:
        category = "trophy"
    elif "杯" in instruction or "cup" in lowered:
        category = "cup"
    color = "blue" if "蓝" in instruction or "blue" in lowered else None
    return category, color


def understand(scene: SceneState, instruction: str) -> TaskSpec:
    """Chapter 2: ground language while retaining ambiguity and rule conflicts."""
    category, color = _instruction_filters(instruction)
    candidates = [
        obj
        for obj in scene.objects
        if (category is None or obj.category == category) and (color is None or obj.color == color)
    ]
    candidates.sort(key=lambda item: item.confidence, reverse=True)
    candidate_ids = [obj.object_id for obj in candidates]
    unknowns: list[str] = []
    conflicts: list[str] = []
    target: Optional[ObjectState] = None
    if not candidates:
        unknowns.append("target_not_observed")
    elif len(candidates) > 1 and (
        category is None or color is None or candidates[0].confidence - candidates[1].confidence < 0.1
    ):
        unknowns.append("target_ambiguous")
    else:
        target = candidates[0]

    recipient = "person_01" if ("我" in instruction or "me" in instruction.lower()) else None
    if recipient is None:
        unknowns.append("recipient_unknown")
    if target and "do_not_move_without_authorization" in target.attributes.get("restrictions", []):
        conflicts.append("site_rule_forbids_moving_target")

    if conflicts:
        status = "conflicted"
        planning_status = "blocked"
    elif unknowns:
        status = "ambiguous" if "target_ambiguous" in unknowns else "unknown"
        planning_status = "plan_with_information_actions"
    else:
        status = "resolved"
        planning_status = "ready"

    questions = []
    if "target_ambiguous" in unknowns:
        questions.append("请确认要递送哪一个候选物体。")
    if "target_not_observed" in unknowns:
        questions.append("当前没有观察到符合描述的物体，是否允许重新观察？")
    if "recipient_unknown" in unknowns:
        questions.append("请确认接收者身份。")
    if conflicts:
        questions.append("目标受场地规则限制，请提供授权或改选目标。")

    target_id = target.object_id if target else None
    constraints = ["cup_upright", "human_safe_distance", "verify_handover"]
    if conflicts:
        constraints.append("authorization_required_for_restricted_object")
    evidence = [
        {"claim": "instruction", "source": "user_utterance", "value": instruction},
        {
            "claim": "target_binding",
            "source": "scene_objects_and_language_filters",
            "category_filter": category,
            "color_filter": color,
            "candidate_ids": candidate_ids,
        },
    ]
    return TaskSpec(
        task_id="task_blue_cup_01",
        instruction=instruction,
        target_object_id=target_id,
        recipient_id=recipient,
        goal={"relation": "stable_handover", "object": target_id, "recipient": recipient},
        constraints=constraints,
        unknowns=unknowns,
        scene_ref=(scene.scene_id, scene.version),
        spec_version=1,
        intent="deliver_object",
        candidate_object_ids=candidate_ids,
        success_conditions=[
            f"stable_held_by({target_id or 'target'}, {recipient or 'recipient'})",
            f"released_by(robot, {target_id or 'target'})",
            f"object_stable({target_id or 'target'})",
        ],
        evidence=evidence,
        conflicts=conflicts,
        clarification_questions=questions,
        status=status,
        planning_status=planning_status,
        ready_for_physical_execution=(planning_status == "ready"),
    )


def _step(
    step_id: str,
    skill: str,
    arguments: dict[str, Any],
    preconditions: list[str],
    effects: list[str],
    resources: Iterable[str],
    failure_modes: Iterable[str],
) -> PlanStep:
    return PlanStep(
        step_id,
        skill,
        arguments,
        preconditions,
        effects,
        resources=list(resources),
        failure_modes=list(failure_modes),
    )


def default_skill_catalog() -> dict[str, Any]:
    skills = {
        "clarify_or_observe": {"version": "1.0", "physical": False},
        "request_authorization_or_reselect": {"version": "1.0", "physical": False},
        "verify_target": {"version": "1.0", "physical": False},
        "navigate_to_object": {"version": "1.0", "physical": True},
        "grasp": {"version": "1.0", "physical": True},
        "navigate_to_recipient": {"version": "1.0", "physical": True},
        "handover": {"version": "1.0", "physical": True},
        "verify_handover": {"version": "1.0", "physical": False},
    }
    return {"catalog_version": "2026.1", "skills": skills}


def plan(task: TaskSpec, skill_catalog: Optional[dict[str, Any]] = None) -> PlanSpec:
    """Chapter 3: generate a discrete plan and validate its registered skills."""
    catalog = skill_catalog or default_skill_catalog()
    if task.conflicts:
        steps = [
            _step(
                "s0",
                "request_authorization_or_reselect",
                {"conflicts": task.conflicts},
                ["task_active"],
                ["conflict_resolved"],
                ["dialog"],
                ["authorization_denied", "user_unavailable"],
            )
        ]
    elif task.unknowns:
        steps = [
            _step(
                "s0",
                "clarify_or_observe",
                {"unknowns": task.unknowns},
                ["task_active"],
                ["unknowns_resolved"],
                ["camera", "dialog"],
                ["target_still_unknown", "user_unavailable"],
            )
        ]
    else:
        target = task.target_object_id
        recipient = task.recipient_id
        steps = [
            _step("s1", "verify_target", {"object_id": target}, ["object_tracked"], ["target_verified"], ["camera"], ["input_stale", "target_lost"]),
            _step("s2", "navigate_to_object", {"object_id": target}, ["target_verified"], ["at_pregrasp"], ["base", "localization"], ["path_blocked", "input_stale"]),
            _step("s3", "grasp", {"object_id": target, "keep_upright": True}, ["at_pregrasp", "hand_available"], ["object_held"], ["right_hand", "torso"], ["unreachable", "contact_not_verified", "input_stale"]),
            _step("s4", "navigate_to_recipient", {"recipient_id": recipient}, ["object_held"], ["at_handover"], ["base", "right_hand"], ["path_blocked", "feedback_timeout"]),
            _step("s5", "handover", {"object_id": target, "recipient_id": recipient}, ["at_handover"], ["handover_candidate"], ["right_hand", "human_workspace"], ["recipient_not_ready", "contact_not_verified"]),
            _step("s6", "verify_handover", {"object_id": target}, ["handover_candidate"], ["goal_satisfied"], ["camera", "gripper_state"], ["verification_failed"]),
        ]

    registered = catalog.get("skills", {})
    validation = [
        {
            "check": "registered_skills",
            "status": "passed" if all(step.skill in registered for step in steps) else "failed",
            "missing": [step.skill for step in steps if step.skill not in registered],
        },
        {
            "check": "task_semantics",
            "status": "passed" if task.planning_status == "ready" else task.planning_status,
        },
        {
            "check": "physical_execution_gate",
            "status": "passed" if task.ready_for_physical_execution else "blocked",
        },
    ]
    missing = validation[0]["missing"]
    if missing:
        status = "invalid"
    elif task.planning_status == "blocked":
        status = "blocked"
    elif task.planning_status == "plan_with_information_actions":
        status = "information_actions_only"
    else:
        status = "valid"
    return PlanSpec(
        plan_id="plan_blue_cup_01",
        task_id=task.task_id,
        scene_ref=task.scene_ref,
        steps=steps,
        replan_when=["scene_version_changed", "skill_unavailable", "safety_state_changed", "physical_check_failed"],
        spec_version=1,
        status=status,
        validation=validation,
        assumptions=["scene_ref_is_current", "registered_skill_contracts_unchanged"],
        estimated_cost={"relative_time": float(len(steps)), "relative_risk": 2.0 if len(steps) > 1 else 0.5},
        risk_controls=["verify_before_physical_dispatch", "stop_on_safety_event", "verify_final_goal"],
    )


def _point_segment_distance(point: list[float], start: list[float], end: list[float]) -> float:
    dx, dy = end[0] - start[0], end[1] - start[1]
    if dx == 0 and dy == 0:
        return math.dist(point[:2], start[:2])
    u = ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / (dx * dx + dy * dy)
    u = max(0.0, min(1.0, u))
    projected = [start[0] + u * dx, start[1] + u * dy]
    return math.dist(point[:2], projected)


def _path_length(waypoints: list[list[float]]) -> float:
    return sum(math.dist(a[:2], b[:2]) for a, b in zip(waypoints, waypoints[1:]))


def check_motion(scene: SceneState, task: TaskSpec) -> MotionCheck:
    """Chapter 4: check geometry and return a categorized, conditional result."""
    checked = ["state_freshness", "operating_range", "corridor_clearance", "obstacle_clearance"]
    if scene.validity["status"] == "degraded" and "robot.pose.map" in scene.validity["invalid_fields"]:
        return MotionCheck(False, "state_insufficient", 0.0, [], task.scene_ref, failure_category="state_invalid", constraints_checked=checked)
    target = next((obj for obj in scene.objects if obj.object_id == task.target_object_id), None)
    if target is None:
        return MotionCheck(False, "target_missing", 0.0, [], task.scene_ref, failure_category="state_invalid", constraints_checked=checked)
    if target.validity.get("for_manipulation") is False:
        return MotionCheck(False, "target_geometry_invalid", 0.0, [], task.scene_ref, failure_category="state_invalid", constraints_checked=checked)

    base = list(scene.localization["base_pose"]["xyz"])
    goal = list(target.pose.xyz)
    distance = math.dist(base[:2], goal[:2])
    max_reach = float(scene.body["capabilities"]["mobile_manipulation_range_m"])
    clearance = float(scene.environment["minimum_clearance_m"])
    metrics = {"target_distance_m": distance, "operating_range_margin_m": max_reach - distance, "minimum_clearance_m": clearance}
    if clearance < 0.35:
        return MotionCheck(False, "clearance_too_small", clearance, [], task.scene_ref, failure_category="collision", constraints_checked=checked, metrics=metrics)
    if distance > max_reach:
        return MotionCheck(False, "outside_operating_range", clearance, [], task.scene_ref, failure_category="geometric_unreachable", constraints_checked=checked, metrics=metrics)

    pregrasp = [goal[0] - 0.45, goal[1], base[2]]
    waypoints = [base]
    detour_used = False
    for obstacle in scene.environment.get("obstacles", []):
        center = obstacle["center"]
        required = float(obstacle["radius_m"]) + 0.4
        if _point_segment_distance(center, base, pregrasp) < required:
            if not scene.environment.get("alternate_route_available", True):
                return MotionCheck(False, "path_blocked", clearance, [], task.scene_ref, failure_category="collision", constraints_checked=checked, metrics=metrics)
            direction = 1.0 if center[1] <= 0 else -1.0
            waypoints.append([center[0], center[1] + direction * required, base[2]])
            detour_used = True
    waypoints.extend([[(base[0] + pregrasp[0]) / 2, (base[1] + pregrasp[1]) / 2, base[2]], pregrasp])
    metrics.update({"path_length_m": _path_length(waypoints), "detour_used": float(detour_used), "pregrasp_offset_m": 0.45})
    return MotionCheck(
        True,
        "feasible",
        clearance,
        waypoints,
        task.scene_ref,
        constraints_checked=checked,
        metrics=metrics,
        assumptions=["2d_navigation_geometry", "quasi_static_pregrasp", "low_level_balance_controller_available"],
    )


def train_behavior_clone(path: Path) -> dict[str, Any]:
    """Chapter 5: a transparent categorical behavior-cloning baseline."""
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    samples = 0
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            counts[row["phase"]][row["action"]] += 1
            samples += 1
    policy = {phase: counter.most_common(1)[0][0] for phase, counter in counts.items()}
    confidence = {
        phase: counter.most_common(1)[0][1] / sum(counter.values()) for phase, counter in counts.items()
    }
    required_phases = {"search", "approach", "grasp", "handover", "recover"}
    return {
        "algorithm": "categorical_behavior_cloning",
        "samples": samples,
        "policy": policy,
        "phase_counts": {phase: dict(counter) for phase, counter in counts.items()},
        "majority_confidence": confidence,
        "coverage": {
            "required_phases": sorted(required_phases),
            "missing_phases": sorted(required_phases - set(policy)),
            "recovery_demonstrated": "recover" in policy,
        },
        "limitations": ["phase_is_given", "no_continuous_control", "no_out_of_distribution_guarantee"],
    }


def _rollout_reach(policy_gain: float, actuator_gain: float, delay_steps: int, target: float = 1.0) -> dict[str, Any]:
    position = 0.0
    action_queue = [0.0] * (delay_steps + 1)
    action_change = 0.0
    previous = 0.0
    clipped = 0
    for step in range(40):
        error = target - position
        action = max(-0.12, min(0.12, policy_gain * error))
        clipped += int(abs(policy_gain * error) > 0.12)
        action_change += abs(action - previous)
        previous = action
        action_queue.append(action)
        applied = action_queue.pop(0)
        position += actuator_gain * applied
        if abs(target - position) < 0.025:
            return {"success": True, "steps": step + 1, "final_error": abs(target - position), "action_change": action_change, "clipped": clipped}
    return {"success": False, "steps": 40, "final_error": abs(target - position), "action_change": action_change, "clipped": clipped}


def reach_policy_study(seed: int = 7) -> dict[str, Any]:
    """Fit a one-parameter reach policy under fixed and randomized dynamics."""
    rng = random.Random(seed)
    fixed_train = [(1.0, 0) for _ in range(12)]
    randomized_train = [(rng.uniform(0.72, 1.18), rng.choice([0, 1, 2])) for _ in range(48)]
    candidates = [0.2 + 0.04 * index for index in range(34)]

    def fit(cases: list[tuple[float, int]]) -> float:
        def loss(gain: float) -> float:
            rows = [_rollout_reach(gain, actuator, delay) for actuator, delay in cases]
            return sum(row["final_error"] + 0.002 * row["steps"] + 0.001 * row["action_change"] for row in rows) / len(rows)
        return min(candidates, key=loss)

    policies = {"fixed_training": fit(fixed_train), "randomized_training": fit(randomized_train)}
    evaluation = {
        "nominal": [(1.0, 0)],
        "in_range_unseen": [(0.78, 1), (0.92, 2), (1.12, 1)],
        "boundary": [(0.7, 2), (1.2, 2)],
        "out_of_range": [(0.5, 3), (1.35, 3)],
    }
    results: dict[str, Any] = {}
    for policy_name, gain in policies.items():
        groups = {}
        for group, cases in evaluation.items():
            rows = [_rollout_reach(gain, actuator, delay) for actuator, delay in cases]
            groups[group] = {
                "success_rate": sum(row["success"] for row in rows) / len(rows),
                "mean_final_error": sum(row["final_error"] for row in rows) / len(rows),
                "mean_steps": sum(row["steps"] for row in rows) / len(rows),
                "trials": rows,
            }
        results[policy_name] = {"policy_gain": gain, "evaluation": groups}
    return {
        "method": "deterministic_grid_search_for_bounded_reach_policy",
        "seed": seed,
        "observation": "target_minus_position",
        "action": "bounded_position_increment",
        "policies": results,
        "claim_boundary": "This teaching study demonstrates evaluation across dynamics; it is not PPO or a G1 deployment result.",
    }


def execute_agent(
    scene: SceneState,
    task: TaskSpec,
    plan_spec: PlanSpec,
    motion: MotionCheck,
    fault: str = "none",
) -> tuple[RuntimeState, list[RuntimeEvent]]:
    """Chapter 6: execute contracts with version checks, recovery, and evidence."""
    if fault not in FAULTS:
        raise ValueError(f"unknown fault: {fault}")
    events: list[RuntimeEvent] = []
    now = 0.0
    completed: list[str] = []
    facts = ["task_active", "object_tracked", "hand_available"]
    evidence: list[dict[str, Any]] = []
    recovery_count = 0
    current_scene_version = scene.version
    final_status = "running"
    final_reason = ""

    def emit(event_type: str, status: str, detail: Optional[dict[str, Any]] = None, advance: float = 0.02) -> None:
        nonlocal now
        now = round(now + advance, 3)
        events.append(RuntimeEvent(now, event_type, status, detail or {}))

    emit("specifications_loaded", "succeeded", {"task_ref": [task.task_id, task.spec_version], "plan_ref": [plan_spec.plan_id, plan_spec.spec_version]})
    if task.unknowns or task.conflicts or plan_spec.status not in {"valid"}:
        final_status = "blocked"
        final_reason = "task_or_plan_not_ready"
        emit("task_blocked", final_status, {"unknowns": task.unknowns, "conflicts": task.conflicts, "plan_status": plan_spec.status})
    elif not motion.feasible:
        final_status = "failed"
        final_reason = motion.reason
        emit("motion_rejected", final_status, {"reason": motion.reason, "category": motion.failure_category})
    else:
        for index, step in enumerate(plan_spec.steps):
            emit("dispatch_guard_checked", "passed", {"step_id": step.step_id, "scene_version": current_scene_version})
            emit("skill_started", "running", {"step_id": step.step_id, "skill": step.skill, "correlation_id": f"run01:{step.step_id}"})

            if fault == "target_moved" and step.skill == "navigate_to_object":
                recovery_count += 1
                current_scene_version += 1
                emit("scene_version_changed", "replan_required", {"old": scene.version, "new": current_scene_version})
                emit("stale_dispatch_prevented", "succeeded", {"step_id": step.step_id})
                emit("target_reobserved", "succeeded", {"scene_version": current_scene_version})
                emit("local_plan_revalidated", "recovered", {"recovery": "update_motion_goal"})
            elif fault == "path_blocked" and step.skill == "navigate_to_object":
                recovery_count += 1
                emit("skill_result", "failed", {"reason": "path_blocked", "blocked_region": "aisle_a"})
                emit("replan_requested", "running", {"reason": "path_blocked"})
                emit("alternate_approach_selected", "recovered", {"route": "aisle_b"})
            elif fault == "grasp_failed" and step.skill == "grasp":
                recovery_count += 1
                emit("skill_result", "verification_failed", {"reason": "contact_not_verified"})
                emit("safe_retreat", "succeeded", {"distance_m": 0.12})
                emit("target_reobserved", "succeeded", {"scene_version": current_scene_version})
                emit("skill_retry", "recovered", {"attempt": 2, "changed": "pregrasp_offset"})
            elif fault == "human_entered" and step.skill == "grasp":
                recovery_count += 1
                emit("safety_stop", "paused", {"reason": "human_in_protective_zone"}, 0.001)
                emit("safe_hold_reached", "paused", {"physical_stop_verified": True})
                emit("protective_zone_clear", "running", {"operator_reset": True}, 0.5)
                emit("dispatch_guard_rechecked", "recovered", {"scene_version": current_scene_version})
            elif fault == "feedback_lost" and step.skill == "navigate_to_recipient":
                recovery_count += 1
                emit("feedback_timeout", "unknown", {"timeout_s": step.timeout_s})
                emit("safe_hold_reached", "paused", {"object_retained": True})
                emit("operator_assistance_required", "blocked", {"reason": "physical_outcome_unknown"})
                final_status = "blocked"
                final_reason = "feedback_timeout_outcome_unknown"
                break
            elif fault == "user_cancel" and index == 2:
                emit("cancel_requested", "canceling", {"step_id": step.step_id})
                emit("safe_hold_reached", "canceled", {"object_retained": True, "physical_stop_verified": True})
                final_status = "canceled"
                final_reason = "user_requested"
                break

            emit("skill_feedback", "running", {"step_id": step.step_id, "progress": 1.0})
            emit("skill_effect_verified", "succeeded", {"step_id": step.step_id, "effects": step.expected_effects})
            completed.append(step.step_id)
            facts.extend(effect for effect in step.expected_effects if effect not in facts)
            evidence.append({"step_id": step.step_id, "observed_effects": step.expected_effects, "scene_version": current_scene_version})
        else:
            final_status = "succeeded"
            final_reason = "goal_satisfied_with_evidence"
            emit("task_completed", "succeeded", {"evidence": task.success_conditions, "recovery_count": recovery_count})

    state = RuntimeState(
        runtime_state_id="runtime_blue_cup_01",
        runtime_version=len(events),
        task_ref=(task.task_id, task.spec_version),
        plan_ref=(plan_spec.plan_id, plan_spec.spec_version),
        plan_state_ref=plan_spec.scene_ref,
        current_scene_ref=(scene.scene_id, current_scene_version),
        task_status=final_status,
        current_node=None if final_status in {"succeeded", "failed", "blocked", "canceled"} else (plan_spec.steps[len(completed)].step_id if len(completed) < len(plan_spec.steps) else None),
        completed_nodes=completed,
        facts=facts,
        evidence=evidence,
        recovery_count=recovery_count,
        final_reason=final_reason,
    )
    return state, events


def run_agent(
    scene: SceneState,
    task: TaskSpec,
    plan_spec: PlanSpec,
    motion: MotionCheck,
    fault: str = "none",
) -> list[RuntimeEvent]:
    """Compatibility wrapper returning the event list used in earlier exercises."""
    return execute_agent(scene, task, plan_spec, motion, fault)[1]


def result_bundle(data_dir: Path, fault: str = "none", scenario: str = "nominal") -> dict[str, Any]:
    raw = apply_scenario(load_json(data_dir / "blue_cup_scene.json"), scenario)
    scene = perceive(raw)
    task = understand(scene, raw["instruction"])
    plan_spec = plan(task)
    motion = check_motion(scene, task)
    learned = train_behavior_clone(data_dir / "demonstrations.jsonl")
    learned["reach_policy_study"] = reach_policy_study()
    runtime, events = execute_agent(scene, task, plan_spec, motion, fault=fault)
    return {
        "run_metadata": {"scenario": scenario, "fault": fault, "deterministic": True, "schema_version": 1},
        "chapter_1_scene_state": to_dict(scene),
        "chapter_2_task_spec": to_dict(task),
        "chapter_3_plan_spec": to_dict(plan_spec),
        "chapter_4_motion_check": to_dict(motion),
        "chapter_5_learned_policy": learned,
        "chapter_6_runtime": {"runtime_state": to_dict(runtime), "events": to_dict(events)},
    }


def experiment_matrix(data_dir: Path) -> dict[str, Any]:
    """Run the book's representative perturbations and return compact evidence."""
    base_raw = load_json(data_dir / "blue_cup_scene.json")
    perception_cases = {}
    for scenario in ("nominal", "camera_blackout", "localization_lost", "depth_invalid", "target_moved"):
        scene = perceive(apply_scenario(base_raw, scenario))
        perception_cases[scenario] = {
            "scene_version": scene.version,
            "validity": scene.validity,
            "objects": len(scene.objects),
            "manipulation_usable": sum(obj.validity.get("for_manipulation", False) for obj in scene.objects),
        }

    cognition_cases = {}
    nominal_scene = perceive(base_raw)
    for label, instruction in {
        "category_and_color": "请把蓝色杯子递给我",
        "color_ambiguous": "请把蓝色的那个递给我",
        "category_ambiguous": "请把杯子递给我",
        "rule_conflict": "请把带蓝色装饰的奖杯递给我",
    }.items():
        task = understand(nominal_scene, instruction)
        cognition_cases[label] = {
            "status": task.status,
            "target": task.target_object_id,
            "candidates": task.candidate_object_ids,
            "unknowns": task.unknowns,
            "conflicts": task.conflicts,
        }

    nominal_task = understand(nominal_scene, base_raw["instruction"])
    complete_catalog = default_skill_catalog()
    missing_catalog = copy.deepcopy(complete_catalog)
    del missing_catalog["skills"]["grasp"]
    planning_cases = {
        "nominal": to_dict(plan(nominal_task)),
        "skill_missing": to_dict(plan(nominal_task, missing_catalog)),
        "rule_conflict": to_dict(plan(understand(nominal_scene, "请把带蓝色装饰的奖杯递给我"))),
        "stale_state": {
            "plan_scene_ref": list(plan(nominal_task).scene_ref),
            "current_scene_ref": [nominal_scene.scene_id, nominal_scene.version + 1],
            "validation": "failed",
            "reason": "scene_version_changed",
        },
    }

    motion_cases = {}
    for scenario in ("nominal", "clearance_blocked", "localization_lost", "depth_invalid"):
        scene = perceive(apply_scenario(base_raw, scenario))
        task = understand(scene, base_raw["instruction"])
        motion_cases[scenario] = to_dict(check_motion(scene, task))
    obstacle_raw = copy.deepcopy(base_raw)
    obstacle_raw["environment"]["obstacles"] = [{"center": [0.9, 0.15], "radius_m": 0.28}]
    obstacle_scene = perceive(obstacle_raw)
    motion_cases["detour"] = to_dict(check_motion(obstacle_scene, understand(obstacle_scene, base_raw["instruction"])))

    agent_cases = {}
    plan_spec = plan(nominal_task)
    motion = check_motion(nominal_scene, nominal_task)
    for fault in FAULTS:
        runtime, events = execute_agent(nominal_scene, nominal_task, plan_spec, motion, fault)
        agent_cases[fault] = {
            "final_status": runtime.task_status,
            "final_reason": runtime.final_reason,
            "recovery_count": runtime.recovery_count,
            "events": len(events),
            "detected": [event.event_type for event in events if event.status in {"failed", "paused", "blocked", "unknown", "replan_required"}],
        }

    return {
        "chapter_1_perception_cases": perception_cases,
        "chapter_2_cognition_cases": cognition_cases,
        "chapter_3_planning_cases": planning_cases,
        "chapter_4_motion_cases": motion_cases,
        "chapter_5_learning_cases": {
            "behavior_clone": train_behavior_clone(data_dir / "demonstrations.jsonl"),
            "reach_policy_study": reach_policy_study(),
        },
        "chapter_6_agent_faults": agent_cases,
    }
