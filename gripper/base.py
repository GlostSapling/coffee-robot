from __future__ import annotations


class GripperController:
    """Abstract gripper interface. Base implementation is a no-op (dry run)."""

    def __init__(self, config: dict):
        self.config = config
        self._gripping = False

    def open(self):
        """Open the gripper (release)."""
        print("[Gripper] Open (dry run)")
        self._gripping = False

    def close(self):
        """Close the gripper (grip)."""
        print("[Gripper] Close (dry run)")
        self._gripping = True

    def is_gripping(self) -> bool:
        return self._gripping
