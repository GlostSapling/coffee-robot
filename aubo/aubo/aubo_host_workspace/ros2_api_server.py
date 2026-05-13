import logging
from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import core_state

logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

app = FastAPI(
    title="Aubo ROS2 API Host",
    description="给 ROS2 节点调用的独立 API（与 WebAPI 拆分）",
    version="1.0.0",
)


class ConnectRequest(BaseModel):
    ip: str
    port: int = 8899


class MoveJRequest(BaseModel):
    joints: List[float]


def _robot_or_raise():
    robot = core_state.get_robot()
    if not robot:
        raise HTTPException(status_code=500, detail="上位机 SDK 尚未初始化")
    return robot


@app.get("/ros2/info")
def ros2_info():
    robot = core_state.get_robot()
    return {
        "status": "online",
        "robot_connected": robot.connected if robot else False,
        "robot_ip": robot.current_ip if robot and robot.connected else None,
    }


@app.post("/ros2/connect")
def ros2_connect(req: ConnectRequest):
    robot = _robot_or_raise()
    success, msg = robot.connect(req.ip, req.port)
    if not success:
        raise HTTPException(status_code=500, detail=f"连接失败: {msg}")
    return {"status": "success", "message": "已成功连接机械臂"}


@app.post("/ros2/disconnect")
def ros2_disconnect():
    robot = _robot_or_raise()
    if robot.connected:
        robot.disconnect()
        return {"status": "success", "message": "已断开连接"}
    return {"status": "ignored", "message": "机械臂本来就没有连接"}


@app.get("/ros2/status")
def ros2_status():
    robot = _robot_or_raise()
    if not robot.connected:
        raise HTTPException(status_code=400, detail="机械臂未连接")
    wp = robot.get_waypoint()
    if not wp:
        raise HTTPException(status_code=500, detail="无法读取当前位姿，请检查连接")
    return {
        "connected": True,
        "joints": list(wp.jointpos),
        "pose": {
            "position": {"x": wp.cartPos.x, "y": wp.cartPos.y, "z": wp.cartPos.z},
            "orientation": {"w": wp.orientation.w, "x": wp.orientation.x, "y": wp.orientation.y, "z": wp.orientation.z},
        },
    }


@app.post("/ros2/movej")
def ros2_movej(req: MoveJRequest):
    robot = _robot_or_raise()
    if not robot.connected:
        raise HTTPException(status_code=400, detail="机械臂未连接")
    if len(req.joints) != 6:
        raise HTTPException(status_code=400, detail="必须提供正好 6 个关节的数组")
    success, msg = robot.movej_safe(req.joints)
    if not success:
        raise HTTPException(status_code=500, detail=msg)
    return {"status": "success", "message": "MoveJ 运动完成"}
