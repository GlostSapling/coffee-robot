from __future__ import annotations

import time
from gripper.base import GripperController


class SerialGripperController(GripperController):
    """Serial/SDK gripper implementation.

    Protocol is configurable via YAML config.
    Customize the _send_command method for your specific gripper hardware.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        cfg = config["gripper"]["serial"]
        self._port = cfg["port"]
        self._baudrate = cfg.get("baudrate", 115200)
        self._open_cmd = bytes(cfg["open_cmd"])
        self._close_cmd = bytes(cfg["close_cmd"])
        self._settle_time = cfg.get("settle_time", 0.5)
        self._serial = None

    def connect(self):
        try:
            import serial
            self._serial = serial.Serial(self._port, self._baudrate, timeout=1.0)
            time.sleep(0.1)
            print(f"[Gripper] Connected to {self._port} @ {self._baudrate}")
        except Exception as e:
            print(f"[Gripper] Serial connection failed: {e}")
            self._serial = None

    def disconnect(self):
        if self._serial and self._serial.is_open:
            self._serial.close()
            self._serial = None

    def _send_command(self, cmd: bytes):
        """Send raw bytes to gripper. Override for custom protocol."""
        if self._serial and self._serial.is_open:
            self._serial.write(cmd)
            self._serial.flush()
            time.sleep(self._settle_time)

    def open(self):
        """Open gripper via serial command."""
        print(f"[Gripper] Opening (cmd: {self._open_cmd.hex()})")
        self._send_command(self._open_cmd)
        self._gripping = False

    def close(self):
        """Close gripper via serial command."""
        print(f"[Gripper] Closing (cmd: {self._close_cmd.hex()})")
        self._send_command(self._close_cmd)
        self._gripping = True

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.disconnect()
