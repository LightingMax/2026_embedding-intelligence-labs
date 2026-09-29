from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .models import (
    MotionCheck,
    ObjectState,
    PlanSpec,
    PlanStep,
    Pose,
    RuntimeEvent,
    SceneState,
    TaskSpec,
    to_dict,
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def perceive(raw: dict[str, Any]) -> SceneState:
    """Chapter 1: fuse body, localization, and visual observations."""
    objects = [
        ObjectState(
            object_id=item["object_id"],
            category=item["category"],
            color=item["color"],
            pose=Pose(**item["pose"]),
            confidence=float(item["confidence"]),
            observed_at=float(item["observed_at"]),
        )
        for item in raw["vision"]["objects"]
    ]
    return SceneState(
        scene_id=raw["scene_id"],
        version=int(raw["version"]),
        timestamp=float(raw["timestamp"]),
        body=raw["proprioception"],
        localization=raw["localization"],
        objects=objects,
        environment=raw["environment"],
    )


def understand(scene: SceneState, instruction: str) -> TaskSpec:
    """Chapter 2: resolve reference and express the requested goal."""
    tokens = instruction.lower()
    candidates = [
        obj
        for obj in scene.objects
        if obj.category == "cup" and ("蓝" not in instruction or obj.color == "blue")
    ]
    candidates.sort(key=lambda item: item.confidence, reverse=True)
    unknowns: list[str] = []
    target_id: str | None = None
    if not candidates:
        unknowns.append("target_not_observed")
    elif len(candidates) > 1 and candidates[0].confidence - candidates[1].confidence < 0.1:
        unknowns.append("target_ambiguous")
    else:
        target_id = candidates[0].object_id
    recipient = "person_01" if ("我" in instruction or "me" in tokens) else None
    if recipient is None:
        unknowns.append("recipient_unknown")
    return TaskSpec(
        task_id="task_blue_cup_01",
        instruction=instruction,
        target_object_id=target_id,
        recipient_id=recipient,
        goal={"relation": "stable_handover", "object": target_id, "recipient": recipient},
        constraints=["cup_upright", "human_safe_distance", "verify_handover"],
        unknowns=unknowns,
        scene_ref=(scene.scene_id, scene.version),
    )


def plan(task: TaskSpec) -> PlanSpec:
    """Chapter 3: turn a semantic goal into a checked discrete skill plan."""
    if task.unknowns:
        steps = [
            PlanStep(
                "s0",
                "clarify_or_observe",
                {"unknowns": task.unknowns},
                ["task_active"],
                ["unknowns_resolved"],
            )
        ]
    else:
        target = task.target_object_id
        recipient = task.recipient_id
        steps = [
            PlanStep("s1", "verify_target", {"object_id": target}, ["object_tracked"], ["target_verified"]),
            PlanStep("s2", "navigate_to_object", {"object_id": target}, ["target_verified"], ["at_pregrasp"]),
            PlanStep("s3", "grasp", {"object_id": target, "keep_upright": True}, ["at_pregrasp", "hand_available"], ["object_held"]),
            PlanStep("s4", "navigate_to_recipient", {"recipient_id": recipient}, ["object_held"], ["at_handover"]),
            PlanStep("s5", "handover", {"object_id": target, "recipient_id": recipient}, ["at_handover"], ["handover_candidate"]),
            PlanStep("s6", "verify_handover", {"object_id": target}, ["handover_candidate"], ["goal_satisfied"]),
        ]
    return PlanSpec(
        plan_id="plan_blue_cup_01",
        task_id=task.task_id,
        scene_ref=task.scene_ref,
        steps=steps,
        replan_when=["scene_version_changed", "skill_unavailable", "safety_state_changed"],
    )


def check_motion(scene: SceneState, task: TaskSpec) -> MotionCheck:
    """Chapter 4: perform a small geometric feasibility check."""
    target = next((obj for obj in scene.objects if obj.object_id == task.target_object_id), None)
    if target is None:
        return MotionCheck(False, "target_missing", 0.0, [])
    base = scene.localization["base_pose"]["xyz"]
    goal = target.pose.xyz
    distance = math.dist(base[:2], goal[:2])
    max_reach = float(scene.body["capabilities"]["mobile_manipulation_range_m"])
    clearance = float(scene.environment["minimum_clearance_m"])
    if clearance < 0.35:
        return MotionCheck(False, "clearance_too_small", clearance, [])
    if distance > max_reach:
        return MotionCheck(False, "outside_operating_range", clearance, [])
    waypoints = [
        [base[0], base[1], base[2]],
        [(base[0] + goal[0]) / 2, (base[1] + goal[1]) / 2, base[2]],
        [goal[0] - 0.45, goal[1], base[2]],
    ]
    return MotionCheck(True, "feasible", clearance, waypoints)


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
    return {"algorithm": "categorical_behavior_cloning", "samples": samples, "policy": policy}


def run_agent(
    scene: SceneState,
    task: TaskSpec,
    plan_spec: PlanSpec,
    motion: MotionCheck,
    fault: str = "none",
) -> list[RuntimeEvent]:
    """Chapter 6: execute with explicit evidence, cancellation and replanning."""
    events: list[RuntimeEvent] = []
    now = 0.0
    if task.unknowns:
        return [RuntimeEvent(now, "task_blocked", "waiting_for_information", {"unknowns": task.unknowns})]
    if not motion.feasible:
        return [RuntimeEvent(now, "motion_rejected", "failed", {"reason": motion.reason})]
    for index, step in enumerate(plan_spec.steps):
        now += 0.1
        events.append(RuntimeEvent(now, "skill_started", "running", {"step_id": step.step_id, "skill": step.skill}))
        if fault == "target_moved" and step.skill == "navigate_to_object":
            events.append(RuntimeEvent(now + 0.02, "scene_version_changed", "replan_required", {"old": scene.version, "new": scene.version + 1}))
            break
        if fault == "human_entered" and step.skill == "grasp":
            events.append(RuntimeEvent(now + 0.02, "safety_stop", "paused", {"reason": "human_in_protective_zone"}))
            break
        if fault == "user_cancel" and index == 2:
            events.append(RuntimeEvent(now + 0.02, "cancel_requested", "canceling", {"step_id": step.step_id}))
            events.append(RuntimeEvent(now + 0.05, "safe_hold_reached", "canceled", {"object_retained": True}))
            break
        events.append(RuntimeEvent(now + 0.05, "skill_effect_verified", "succeeded", {"effects": step.expected_effects}))
        now += 0.05
    else:
        events.append(RuntimeEvent(now + 0.05, "task_completed", "succeeded", {"evidence": "goal_satisfied"}))
    return events


def result_bundle(data_dir: Path, fault: str = "none") -> dict[str, Any]:
    raw = load_json(data_dir / "blue_cup_scene.json")
    scene = perceive(raw)
    task = understand(scene, raw["instruction"])
    plan_spec = plan(task)
    motion = check_motion(scene, task)
    learned = train_behavior_clone(data_dir / "demonstrations.jsonl")
    events = run_agent(scene, task, plan_spec, motion, fault=fault)
    return {
        "chapter_1_scene_state": to_dict(scene),
        "chapter_2_task_spec": to_dict(task),
        "chapter_3_plan_spec": to_dict(plan_spec),
        "chapter_4_motion_check": to_dict(motion),
        "chapter_5_learned_policy": learned,
        "chapter_6_runtime_events": to_dict(events),
    }
