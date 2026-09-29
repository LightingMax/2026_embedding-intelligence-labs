from __future__ import annotations

import json
import os
import time
from pathlib import Path

import rclpy
from rclpy.executors import MultiThreadedExecutor

from .agent_runner import AgentRunner
from .scenario_publisher import ScenarioPublisher
from .skill_server import SkillServer


def main() -> None:
    rclpy.init()
    nodes = [ScenarioPublisher(), SkillServer(), AgentRunner()]
    runner = nodes[-1]
    executor = MultiThreadedExecutor(num_threads=4)
    for node in nodes:
        executor.add_node(node)
    deadline = time.monotonic() + float(os.getenv("BOOK_ROS_TIMEOUT_S", "30"))
    try:
        while rclpy.ok() and not runner.done and time.monotonic() < deadline:
            executor.spin_once(timeout_sec=0.1)
        if not runner.done:
            runner.status = "timeout"
            runner.record("demo_timeout", "failed", {})
        output = Path(os.getenv("BOOK_ROS_REPORT", "/workspace/artifacts/ros2/result.json"))
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(runner.report(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"ROS2_INTEGRATION_{runner.status.upper()} report={output}")
        if runner.status != "succeeded" and runner.fault == "none":
            raise RuntimeError(f"ROS 2 integration failed: {runner.status}")
    finally:
        executor.shutdown()
        for node in nodes:
            node.destroy_node()
        rclpy.shutdown()
