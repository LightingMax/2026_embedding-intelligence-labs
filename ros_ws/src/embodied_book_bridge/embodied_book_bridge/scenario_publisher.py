from __future__ import annotations

import json
from pathlib import Path

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class ScenarioPublisher(Node):
    def __init__(self) -> None:
        super().__init__("embodied_book_scenario")
        self.publisher = self.create_publisher(String, "/book/raw_observation", 10)
        self.timer = self.create_timer(1.0, self.publish_once)
        self.sent = False

    def publish_once(self) -> None:
        if self.sent:
            return
        path = Path("/workspace/data/blue_cup_scene.json")
        message = String()
        message.data = json.dumps(json.loads(path.read_text(encoding="utf-8")), ensure_ascii=False)
        self.publisher.publish(message)
        self.get_logger().info("published /book/raw_observation")
        self.sent = True


def main() -> None:
    rclpy.init()
    node = ScenarioPublisher()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
