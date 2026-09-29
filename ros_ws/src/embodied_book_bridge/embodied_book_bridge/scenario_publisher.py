from __future__ import annotations

import json
from pathlib import Path

import rclpy
from embodied_book_labs.pipeline import result_bundle
from rclpy.node import Node
from std_msgs.msg import String


class ScenarioPublisher(Node):
    def __init__(self) -> None:
        super().__init__("embodied_book_scenario")
        self.publishers = {
            "/book/scene_state": self.create_publisher(String, "/book/scene_state", 10),
            "/book/task_spec": self.create_publisher(String, "/book/task_spec", 10),
            "/book/plan_spec": self.create_publisher(String, "/book/plan_spec", 10),
            "/book/runtime_events": self.create_publisher(String, "/book/runtime_events", 10),
        }
        self.timer = self.create_timer(1.0, self.publish_once)
        self.sent = False

    def publish_once(self) -> None:
        if self.sent:
            return
        bundle = result_bundle(Path("/workspace/data"))
        payloads = {
            "/book/scene_state": bundle["chapter_1_scene_state"],
            "/book/task_spec": bundle["chapter_2_task_spec"],
            "/book/plan_spec": bundle["chapter_3_plan_spec"],
            "/book/runtime_events": bundle["chapter_6_runtime_events"],
        }
        for topic, payload in payloads.items():
            message = String()
            message.data = json.dumps(payload, ensure_ascii=False)
            self.publishers[topic].publish(message)
            self.get_logger().info(f"published {topic}")
        self.sent = True


def main() -> None:
    rclpy.init()
    node = ScenarioPublisher()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
