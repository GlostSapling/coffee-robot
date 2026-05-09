from __future__ import annotations

import sys
import os
from typing import List

# 添加 SDK 路径以便导入
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "sdk"))

from aubo_openclaw_sdk import AuboOpenclawSDK, SDKError
from robot.base import RobotController, Pose


class WebAPIRobotController(RobotController):
    """Windows 后端：通过 AuboOpenclawSDK HTTP API 控制机器人。"""

    def __init__(self, config: dict):
        super().__init__(config)
        cfg = config["robot"]["webapi"]
        self.sdk = AuboOpenclawSDK(
            host=cfg["host"],
            webapi_port=cfg["webapi_port"],
            ros2api_port=cfg["ros2api_port"],
        )
        self._robot_ip = cfg["robot_ip"]
        self._robot_port = cfg.get("robot_port", 8899)

    def connect(self) -> bool:
        try:
            self.sdk.connect_robot(self._robot_ip, self._robot_port)
            self.connected = True
            return True
        except SDKError as e:
            print(f"[WebAPI] Connection failed: {e}")
            self.connected = False
            return False

    def disconnect(self):
        if self.connected:
            try:
                self.sdk.disconnect_robot()
            except SDKError:
                pass
            self.connected = False

    def movej(self, joints: List[float], velocity_scale: float = 1.0):
        if len(joints) != 6:
            raise ValueError(f"Expected 6 joints, got {len(joints)}")
        self.sdk.movej(joints)

    def movel(self, pose: Pose, velocity_scale: float = 1.0):
        raise NotImplementedError("Linear move not yet supported via WebAPI")

    def get_joint_positions(self) -> List[float]:
        status = self.sdk.get_robot_status()
        return status.get("joints", [0.0] * 6)

    def get_pose(self) -> Pose:
        status = self.sdk.get_robot_status()
        pose_data = status.get("pose", {})
        pos = pose_data.get("position", {})
        ori = pose_data.get("orientation", {})
        return Pose(
            position=[pos.get("x", 0), pos.get("y", 0), pos.get("z", 0)],
            orientation=[ori.get("w", 1), ori.get("x", 0), ori.get("y", 0), ori.get("z", 0)],
        )
