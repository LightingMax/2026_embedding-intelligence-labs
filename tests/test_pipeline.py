from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from embodied_book_labs.pipeline import (  # noqa: E402
    check_motion,
    execute_agent,
    experiment_matrix,
    load_json,
    perceive,
    plan,
    result_bundle,
    run_agent,
    train_behavior_clone,
    understand,
)
from embodied_book_labs.report import write_report  # noqa: E402


class PipelineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.data = ROOT / "data"
        self.scene = perceive(load_json(self.data / "blue_cup_scene.json"))
        self.task = understand(self.scene, "请把桌上的蓝色杯子递给我")

    def test_semantic_grounding_does_not_select_blue_trophy(self) -> None:
        self.assertEqual(self.task.target_object_id, "cup_blue")
        self.assertEqual(self.task.unknowns, [])

    def test_plan_and_motion_interfaces(self) -> None:
        plan_spec = plan(self.task)
        self.assertEqual(plan_spec.steps[2].skill, "grasp")
        self.assertTrue(check_motion(self.scene, self.task).feasible)

    def test_target_move_requests_replanning(self) -> None:
        plan_spec = plan(self.task)
        events = run_agent(self.scene, self.task, plan_spec, check_motion(self.scene, self.task), "target_moved")
        event_types = [event.event_type for event in events]
        self.assertIn("scene_version_changed", event_types)
        self.assertIn("stale_dispatch_prevented", event_types)
        self.assertEqual(events[-1].event_type, "task_completed")

    def test_task_understanding_retains_ambiguity_and_rule_conflict(self) -> None:
        ambiguous = understand(self.scene, "请把蓝色的那个递给我")
        restricted = understand(self.scene, "请把带蓝色装饰的奖杯递给我")
        self.assertEqual(ambiguous.status, "ambiguous")
        self.assertIn("target_ambiguous", ambiguous.unknowns)
        self.assertEqual(restricted.status, "conflicted")
        self.assertFalse(restricted.ready_for_physical_execution)

    def test_motion_returns_categorized_failures(self) -> None:
        raw = load_json(self.data / "blue_cup_scene.json")
        raw["environment"]["minimum_clearance_m"] = 0.2
        scene = perceive(raw)
        result = check_motion(scene, understand(scene, raw["instruction"]))
        self.assertFalse(result.feasible)
        self.assertEqual(result.failure_category, "collision")

    def test_feedback_loss_does_not_report_success(self) -> None:
        plan_spec = plan(self.task)
        runtime, events = execute_agent(
            self.scene, self.task, plan_spec, check_motion(self.scene, self.task), "feedback_lost"
        )
        self.assertEqual(runtime.task_status, "blocked")
        self.assertEqual(runtime.final_reason, "feedback_timeout_outcome_unknown")
        self.assertNotIn("task_completed", [event.event_type for event in events])

    def test_behavior_clone_keeps_recovery_action(self) -> None:
        model = train_behavior_clone(self.data / "demonstrations.jsonl")
        self.assertEqual(model["policy"]["recover"], "retreat_and_reobserve")

    def test_end_to_end_report_is_self_contained(self) -> None:
        bundle = result_bundle(self.data)
        with tempfile.TemporaryDirectory() as directory:
            report = write_report(bundle, Path(directory))
            self.assertTrue(report.exists())
            parsed = json.loads((Path(directory) / "result.json").read_text(encoding="utf-8"))
            self.assertEqual(parsed["chapter_6_runtime"]["events"][-1]["event_type"], "task_completed")
            self.assertTrue((Path(directory) / "timeline.csv").exists())

    def test_experiment_matrix_covers_all_runtime_faults(self) -> None:
        matrix = experiment_matrix(self.data)
        faults = matrix["chapter_6_agent_faults"]
        self.assertEqual(
            set(faults),
            {"none", "target_moved", "path_blocked", "grasp_failed", "human_entered", "feedback_lost", "user_cancel"},
        )
        self.assertEqual(faults["feedback_lost"]["final_status"], "blocked")
        self.assertEqual(faults["user_cancel"]["final_status"], "canceled")


if __name__ == "__main__":
    unittest.main()
