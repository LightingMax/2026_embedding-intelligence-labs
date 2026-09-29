from __future__ import annotations

import json
import os
from pathlib import Path

import rclpy
from embodied_book_interfaces.msg import BookState
from embodied_book_interfaces.srv import QuerySkills
from embodied_book_labs.pipeline import default_skill_catalog, result_bundle
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy


class ScenarioPublisher(Node):
    def __init__(self) -> None:
        super().__init__("embodied_book_scenario")
        qos = QoSProfile(depth=1)
        qos.reliability = ReliabilityPolicy.RELIABLE
        qos.durability = DurabilityPolicy.TRANSIENT_LOCAL
        self.topic_publishers = {
            "/book/scene_state": self.create_publisher(BookState, "/book/scene_state", qos),
            "/book/task_spec": self.create_publisher(BookState, "/book/task_spec", qos),
            "/book/plan_spec": self.create_publisher(BookState, "/book/plan_spec", qos),
            "/book/runtime_state": self.create_publisher(BookState, "/book/runtime_state", qos),
        }
        data_dir = Path(os.getenv("BOOK_DATA_DIR", "/workspace/data"))
        self.bundle = result_bundle(data_dir)
        self.catalog = default_skill_catalog()
        self.service = self.create_service(QuerySkills, "/book/query_skills", self.query_skills)
        self.timer = self.create_timer(0.25, self.publish_once)
        self.sent = False

    def _message(self, schema: str, value: dict, version: int) -> BookState:
        message = BookState()
        message.stamp = self.get_clock().now().to_msg()
        message.correlation_id = "run01"
        message.schema_name = schema
        message.schema_version = 1
        message.data_version = version
        message.json_data = json.dumps(value, ensure_ascii=False)
        return message

    def publish_once(self) -> None:
        if self.sent:
            return
        payloads = {
            "/book/scene_state": ("SceneState", self.bundle["chapter_1_scene_state"], self.bundle["chapter_1_scene_state"]["version"]),
            "/book/task_spec": ("TaskSpec", self.bundle["chapter_2_task_spec"], self.bundle["chapter_2_task_spec"]["spec_version"]),
            "/book/plan_spec": ("PlanSpec", self.bundle["chapter_3_plan_spec"], self.bundle["chapter_3_plan_spec"]["spec_version"]),
            "/book/runtime_state": ("RuntimeState", self.bundle["chapter_6_runtime"]["runtime_state"], self.bundle["chapter_6_runtime"]["runtime_state"]["runtime_version"]),
        }
        for topic, (schema, payload, version) in payloads.items():
            self.topic_publishers[topic].publish(self._message(schema, payload, int(version)))
            self.get_logger().info(f"published {topic} ({schema} v{version})")
        self.sent = True

    def query_skills(self, _request: QuerySkills.Request, response: QuerySkills.Response) -> QuerySkills.Response:
        response.catalog_version = self.catalog["catalog_version"]
        response.skill_names = sorted(self.catalog["skills"])
        return response


def main() -> None:
    rclpy.init()
    node = ScenarioPublisher()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
