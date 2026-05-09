from __future__ import annotations

import math
import os
import sys
from typing import List

from robot.base import RobotController, Pose


class LocalRobotController(RobotController):
    """Ubuntu 后端：通过 libpyauboi5 本地 SDK 控制机器人。"""

    def __init__(self, config: dict):
        super().__init__(config)
        cfg = config["robot"]["local"]
        self._robot_ip = cfg["robot_ip"]
        self._robot_port = cfg.get("robot_port", 8899)
        self._sdk_path = os.path.expanduser(cfg.get("sdk_path", "~/aubo_quick_start/python_linux_lib"))

        self._aubo = None
        self._robot = None

    def _load_sdk(self):
        if self._aubo is not None:
            return
        if self._sdk_path not in sys.path:
            sys.path.append(self._sdk_path)
        try:
            import libpyauboi5 as aubo
            self._aubo = aubo
        except ImportError as e:
            raise RuntimeError(
                f"Failed to import libpyauboi5 from {self._sdk_path}. "
                f"Ensure the SDK is installed and Python version matches. Error: {e}"
            )

    def connect(self) -> bool:
        self._load_sdk()
        try:
            self._aubo.initialize()
            self._robot = self._aubo.robot()
            ret = self._robot.connect(self._robot_ip, self._robot_port)
            if ret == 0:
                self.connected = True
                # 设置安全运动参数
                max_vel = [v * math.pi / 180.0 for v in self._speed_cfg["max_velocity"]]
                max_acc = [a * math.pi / 180.0 for a in self._speed_cfg["max_acceleration"]]
                self._robot.set_joint_maxvelc(max_vel)
                self._robot.set_joint_maxacc(max_acc)
                return True
            else:
                print(f"[Local] Connection failed, error code: {ret}")
                return False
        except Exception as e:
            print(f"[Local] Connection failed: {e}")
            return False

    def disconnect(self):
        if self.connected and self._robot:
            try:
                self._robot.disconnect()
                self._aubo.uninitialize()
            except Exception:
                pass
            self.connected = False

    def movej(self, joints: List[float], velocity_scale: float = 1.0):
        if not self.connected or not self._robot:
            raise RuntimeError("Robot not connected")
        if len(joints) != 6:
            raise ValueError(f"Expected 6 joints, got {len(joints)}")
        self._robot.move_joint(joints, True)  # 阻塞模式

    def movel(self, pose: Pose, velocity_scale: float = 1.0):
        if not self.connected or not self._robot:
            raise RuntimeError("Robot not connected")
        self._robot.move_line(
            list(pose.position),
            list(pose.orientation),
            0.0, 0.0
        )

    def get_joint_positions(self) -> List[float]:
        if not self.connected or not self._robot:
            return [0.0] * 6
        wp = self._robot.get_current_waypoint()
        if wp and hasattr(wp, 'jointpos'):
            return list(wp.jointpos)
        return [0.0] * 6

    def get_pose(self) -> Pose:
        if not self.connected or not self._robot:
            return Pose(position=[0, 0, 0], orientation=[1, 0, 0, 0])
        wp = self._robot.get_current_waypoint()
        if wp:
            return Pose(
                position=[wp.cartPos.x, wp.cartPos.y, wp.cartPos.z],
                orientation=[wp.orientation.w, wp.orientation.x, wp.orientation.y, wp.orientation.z],
            )
        return Pose(position=[0, 0, 0], orientation=[1, 0, 0, 0])
