from __future__ import annotations

import json
import os
from pathlib import Path

from embodied_book_interfaces.action import ExecuteSkill
from embodied_book_labs.pipeline import result_bundle
from rclpy.action import ActionClient
from rclpy.node import Node


class AgentRunner(Node):
    def __init__(self) -> None:
        super().__init__("embodied_book_agent_runner")
        data_dir = Path(os.getenv("BOOK_DATA_DIR", "/workspace/data"))
        self.bundle = result_bundle(data_dir)
        self.steps = self.bundle["chapter_3_plan_spec"]["steps"]
        self.scene_version = self.bundle["chapter_1_scene_state"]["version"]
        self.client = ActionClient(self, ExecuteSkill, "/book/execute_skill")
        self.events: list[dict] = []
        self.index = 0
        self.waiting = False
        self.done = False
        self.status = "running"
        self.fault = os.getenv("BOOK_ROS_FAULT", "none")
        self.cancel_sent = False
        self.goal_handle = None
        self.timer = self.create_timer(0.05, self.tick)

    def record(self, event_type: str, status: str, detail: dict) -> None:
        self.events.append({"event_type": event_type, "status": status, "detail": detail})
        self.get_logger().info(f"{event_type}: {status} {detail}")

    def tick(self) -> None:
        if self.done or self.waiting or not self.client.server_is_ready():
            return
        if self.index >= len(self.steps):
            self.status = "succeeded"
            self.done = True
            self.record("task_completed", "succeeded", {"steps": len(self.steps)})
            return
        step = self.steps[self.index]
        goal = ExecuteSkill.Goal()
        goal.correlation_id = f"ros-run01:{step['step_id']}"
        goal.skill = step["skill"]
        goal.arguments_json = json.dumps(step["arguments"], ensure_ascii=False)
        goal.scene_version = self.scene_version
        self.waiting = True
        self.record("skill_dispatched", "running", {"step_id": step["step_id"], "skill": step["skill"]})
        future = self.client.send_goal_async(goal, feedback_callback=self.feedback)
        future.add_done_callback(self.goal_response)

    def goal_response(self, future) -> None:
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.record("skill_rejected", "failed", {"step": self.steps[self.index]["step_id"]})
            self.status = "failed"
            self.done = True
            self.waiting = False
            return
        self.goal_handle = goal_handle
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.result)

    def feedback(self, message) -> None:
        feedback = message.feedback
        step = self.steps[self.index]
        self.record("skill_feedback", feedback.phase, {"step_id": step["step_id"], "progress": round(float(feedback.progress), 2)})
        if (
            self.fault == "user_cancel"
            and step["skill"] == "grasp"
            and feedback.progress >= 0.5
            and not self.cancel_sent
            and self.goal_handle is not None
        ):
            self.cancel_sent = True
            self.record("cancel_requested", "canceling", {"step_id": step["step_id"]})
            self.goal_handle.cancel_goal_async()

    def result(self, future) -> None:
        result = future.result().result
        step = self.steps[self.index]
        self.record("skill_result", result.status, {"step_id": step["step_id"], "detail": json.loads(result.detail_json or "{}")})
        self.waiting = False
        if result.status == "succeeded":
            self.index += 1
        elif result.status == "canceled_safe_hold":
            self.status = "canceled"
            self.done = True
        else:
            self.status = "failed"
            self.done = True

    def report(self) -> dict:
        return {
            "backend": "ros2_jazzy",
            "action": "/book/execute_skill",
            "fault": self.fault,
            "status": self.status,
            "completed_steps": self.index,
            "events": self.events,
        }
