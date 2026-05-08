from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np


@dataclass
class Pose:
    position: np.ndarray      # [x, y, z] in meters
    orientation: np.ndarray   # [w, x, y, z] quaternion


@dataclass
class JointState:
    positions: np.ndarray     # [j1..j6] in radians


class RobotController(ABC):
    """Abstract robot interface. All backends implement this."""

    def __init__(self, config: dict):
        self.config = config
        self.connected = False
        self._speed_cfg = config["robot"]["speed"]

    @abstractmethod
    def connect(self) -> bool:
        """Connect to the robot. Returns True on success."""

    @abstractmethod
    def disconnect(self):
        """Disconnect from the robot."""

    @abstractmethod
    def movej(self, joints: List[float], velocity_scale: float = 1.0):
        """Move to target joint positions (blocking)."""

    @abstractmethod
    def movel(self, pose: Pose, velocity_scale: float = 1.0):
        """Linear move to Cartesian pose (blocking)."""

    @abstractmethod
    def get_joint_positions(self) -> List[float]:
        """Read current joint positions (rad)."""

    @abstractmethod
    def get_pose(self) -> Pose:
        """Read current Cartesian pose."""

    def movej_with_offset(self, joints: List[float], offset: List[float], velocity_scale: float = 1.0):
        """Move to joints then apply a Cartesian offset (for approach/depart)."""
        self.movej(joints, velocity_scale)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.disconnect()
