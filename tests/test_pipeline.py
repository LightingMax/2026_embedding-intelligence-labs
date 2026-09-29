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
        self.assertEqual(events[-1].status, "replan_required")

    def test_behavior_clone_keeps_recovery_action(self) -> None:
        model = train_behavior_clone(self.data / "demonstrations.jsonl")
        self.assertEqual(model["policy"]["recover"], "retreat_and_reobserve")

    def test_end_to_end_report_is_self_contained(self) -> None:
        bundle = result_bundle(self.data)
        with tempfile.TemporaryDirectory() as directory:
            report = write_report(bundle, Path(directory))
            self.assertTrue(report.exists())
            parsed = json.loads((Path(directory) / "result.json").read_text(encoding="utf-8"))
            self.assertEqual(parsed["chapter_6_runtime_events"][-1]["event_type"], "task_completed")


if __name__ == "__main__":
    unittest.main()
