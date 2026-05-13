"""
python_aubo_openclaw_SDK
========================

单文件 SDK，封装 Aubo Host 的 WebAPI 与 ROS2API 调用。

默认端口:
- WebAPI: 8000
- ROS2API: 8001

快速示例:
    from aubo_openclaw_sdk import AuboOpenclawSDK
    sdk = AuboOpenclawSDK(host="192.168.10.3")
    sdk.connect_robot("192.168.10.3")
    print(sdk.get_robot_status())
    sdk.movej([0, 0, 0, 0, 0, 0])
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests


class SDKError(RuntimeError):
    pass


@dataclass
class AuboOpenclawSDK:
    host: str = "127.0.0.1"
    webapi_port: int = 8000
    ros2api_port: int = 8001
    timeout: float = 10.0

    @property
    def web_base(self) -> str:
        return f"http://{self.host}:{self.webapi_port}"

    @property
    def ros2_base(self) -> str:
        return f"http://{self.host}:{self.ros2api_port}"

    def _request(self, method: str, url: str, payload: Optional[dict] = None) -> Dict[str, Any]:
        try:
            resp = requests.request(method, url, json=payload, timeout=self.timeout)
        except Exception as e:
            raise SDKError(f"请求失败: {e}") from e
        try:
            data = resp.json() if resp.text else {}
        except Exception:
            data = {"raw": resp.text}
        if not resp.ok:
            detail = data.get("detail") if isinstance(data, dict) else None
            raise SDKError(f"HTTP {resp.status_code}: {detail or data}")
        return data if isinstance(data, dict) else {"data": data}

    # ---------------- 机械臂（WebAPI） ----------------
    def get_system_info(self) -> Dict[str, Any]:
        return self._request("GET", f"{self.web_base}/api/info")

    def connect_robot(self, ip: str, port: int = 8899) -> Dict[str, Any]:
        return self._request("POST", f"{self.web_base}/api/connect", {"ip": ip, "port": port})

    def disconnect_robot(self) -> Dict[str, Any]:
        return self._request("POST", f"{self.web_base}/api/disconnect")

    def get_robot_status(self) -> Dict[str, Any]:
        return self._request("GET", f"{self.web_base}/api/status")

    def movej(self, joints: List[float]) -> Dict[str, Any]:
        if len(joints) != 6:
            raise SDKError("joints 必须是 6 轴数组")
        return self._request("POST", f"{self.web_base}/api/movej", {"joints": joints})

    # ---------------- 相机（WebAPI） ----------------
    def list_cameras(self) -> Dict[str, Any]:
        return self._request("GET", f"{self.web_base}/api/cameras")

    def select_camera(self, serial: str) -> Dict[str, Any]:
        return self._request("POST", f"{self.web_base}/api/cameras/select", {"serial": serial})

    def capture_photo(self) -> Dict[str, Any]:
        return self._request("POST", f"{self.web_base}/api/capture/photo")

    def capture_video(self, duration_sec: int = 3) -> Dict[str, Any]:
        return self._request("POST", f"{self.web_base}/api/capture/video", {"duration_sec": int(duration_sec)})

    def capture_depth_photo(self) -> Dict[str, Any]:
        return self._request("POST", f"{self.web_base}/api/capture/depth_photo")

    def capture_depth_video(self, duration_sec: int = 3) -> Dict[str, Any]:
        return self._request("POST", f"{self.web_base}/api/capture/depth_video", {"duration_sec": int(duration_sec)})

    def list_media(self) -> Dict[str, Any]:
        return self._request("GET", f"{self.web_base}/api/media")

    def delete_media(self, record_id: int) -> Dict[str, Any]:
        return self._request("DELETE", f"{self.web_base}/api/media/{int(record_id)}")

    def get_media_file_url(self, record_id: int) -> str:
        return f"{self.web_base}/api/media/{int(record_id)}/file"

    # ---------------- ROS2 API（独立） ----------------
    def ros2_info(self) -> Dict[str, Any]:
        return self._request("GET", f"{self.ros2_base}/ros2/info")

    def ros2_connect(self, ip: str, port: int = 8899) -> Dict[str, Any]:
        return self._request("POST", f"{self.ros2_base}/ros2/connect", {"ip": ip, "port": port})

    def ros2_disconnect(self) -> Dict[str, Any]:
        return self._request("POST", f"{self.ros2_base}/ros2/disconnect")

    def ros2_status(self) -> Dict[str, Any]:
        return self._request("GET", f"{self.ros2_base}/ros2/status")

    def ros2_movej(self, joints: List[float]) -> Dict[str, Any]:
        if len(joints) != 6:
            raise SDKError("joints 必须是 6 轴数组")
        return self._request("POST", f"{self.ros2_base}/ros2/movej", {"joints": joints})


def demo():
    sdk = AuboOpenclawSDK(host="127.0.0.1", webapi_port=8000, ros2api_port=8001)
    print("系统信息:", json.dumps(sdk.get_system_info(), ensure_ascii=False, indent=2))
    print("相机列表:", json.dumps(sdk.list_cameras(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    demo()
