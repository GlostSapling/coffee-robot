from __future__ import annotations


class GripperController:
    """抽象夹爪接口。基础实现为空操作（仿真模式）。"""

    def __init__(self, config: dict):
        self.config = config
        self._gripping = False

    def open(self):
        """打开夹爪（释放）。"""
        print("[Gripper] Open (dry run)")
        self._gripping = False

    def close(self):
        """闭合夹爪（夹紧）。"""
        print("[Gripper] Close (dry run)")
        self._gripping = True

    def is_gripping(self) -> bool:
        return self._gripping
