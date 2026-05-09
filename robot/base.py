from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np


@dataclass
class Pose:
    position: np.ndarray      # [x, y, z] 单位：米
    orientation: np.ndarray   # [w, x, y, z] 四元数


@dataclass
class JointState:
    positions: np.ndarray     # [j1..j6] 单位：弧度


class RobotController(ABC):
    """抽象机器人接口。所有后端实现此接口。"""

    def __init__(self, config: dict):
        self.config = config
        self.connected = False
        self._speed_cfg = config["robot"]["speed"]

    @abstractmethod
    def connect(self) -> bool:
        """连接机器人。成功返回 True。"""

    @abstractmethod
    def disconnect(self):
        """断开机器人连接。"""

    @abstractmethod
    def movej(self, joints: List[float], velocity_scale: float = 1.0):
        """移动到目标关节位置（阻塞）。"""

    @abstractmethod
    def movel(self, pose: Pose, velocity_scale: float = 1.0):
        """直线运动到笛卡尔位姿（阻塞）。"""

    @abstractmethod
    def get_joint_positions(self) -> List[float]:
        """读取当前关节位置（弧度）。"""

    @abstractmethod
    def get_pose(self) -> Pose:
        """读取当前笛卡尔位姿。"""

    def movej_with_offset(self, joints: List[float], offset: List[float], velocity_scale: float = 1.0):
        """移动到关节位置后应用笛卡尔偏移（用于接近/离开）。"""
        self.movej(joints, velocity_scale)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.disconnect()
