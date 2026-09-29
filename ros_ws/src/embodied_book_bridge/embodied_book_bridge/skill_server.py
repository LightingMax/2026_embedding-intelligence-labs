from __future__ import annotations

import json
import os
import time

from embodied_book_interfaces.action import ExecuteSkill
from embodied_book_labs.pipeline import default_skill_catalog
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.node import Node


class SkillServer(Node):
    def __init__(self) -> None:
        super().__init__("embodied_book_skill_server")
        self.catalog = default_skill_catalog()["skills"]
        self.scene_version = int(os.getenv("BOOK_SCENE_VERSION", "7"))
        self.fault = os.getenv("BOOK_ROS_FAULT", "none")
        self.callback_group = ReentrantCallbackGroup()
        self.server = ActionServer(
            self,
            ExecuteSkill,
            "/book/execute_skill",
            execute_callback=self.execute,
            goal_callback=self.goal,
            cancel_callback=self.cancel,
            callback_group=self.callback_group,
        )

    def goal(self, goal_request: ExecuteSkill.Goal) -> GoalResponse:
        if goal_request.skill not in self.catalog:
            self.get_logger().warning(f"reject unregistered skill: {goal_request.skill}")
            return GoalResponse.REJECT
        if goal_request.scene_version != self.scene_version:
            self.get_logger().warning(
                f"reject stale scene version: {goal_request.scene_version} != {self.scene_version}"
            )
            return GoalResponse.REJECT
        return GoalResponse.ACCEPT

    def cancel(self, _goal_handle) -> CancelResponse:
        return CancelResponse.ACCEPT

    def execute(self, goal_handle) -> ExecuteSkill.Result:
        request = goal_handle.request
        for phase, progress in (("accepted", 0.1), ("executing", 0.5), ("verifying", 0.9)):
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                result = ExecuteSkill.Result()
                result.status = "canceled_safe_hold"
                result.detail_json = json.dumps({"physical_stop_verified": True})
                return result
            feedback = ExecuteSkill.Feedback()
            feedback.phase = phase
            feedback.progress = progress
            feedback.detail_json = json.dumps({"skill": request.skill, "correlation_id": request.correlation_id})
            goal_handle.publish_feedback(feedback)
            time.sleep(0.03)

        if self.fault == "path_blocked" and request.skill == "navigate_to_object":
            failure_reason = "path_blocked"
        elif self.fault == "grasp_failed" and request.skill == "grasp":
            failure_reason = "contact_not_verified"
        else:
            failure_reason = ""
        if failure_reason:
            goal_handle.abort()
            result = ExecuteSkill.Result()
            result.status = "failed"
            result.detail_json = json.dumps({"reason": failure_reason})
            return result

        goal_handle.succeed()
        result = ExecuteSkill.Result()
        result.status = "succeeded"
        result.detail_json = json.dumps({"effects_verified": True, "skill": request.skill})
        return result

    def destroy_node(self) -> bool:
        self.server.destroy()
        return super().destroy_node()
