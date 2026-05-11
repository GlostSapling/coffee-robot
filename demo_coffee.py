"""
咖啡机器人 Demo
流程: 抓杯子 → 运送到咖啡机 → 放下杯子

直接调用 Aubo SDK，不经过 WebAPI。
"""

import sys
import os
import time
import math
import signal
import requests as http_requests

# 添加 SDK 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "aubo", "aubo", "aubo_host_workspace"))
from aubo_sdk import AuboWindowsSDK
from coffee_config import ROBOT_IP, ROBOT_PORT, GRIPPER_URL, STEPS

# 全局引用，用于信号处理
_robot = None


def _cleanup_and_exit(signum=None, frame=None):
    """Ctrl+C 时急停并断开连接"""
    print("\n[退出] 收到中断信号，正在停止...")
    if _robot and _robot.connected:
        _robot.fast_stop()
        print("[退出] 已发送急停指令")
        time.sleep(0.5)
        try:
            _robot.disconnect()
        except Exception:
            pass
        print("[退出] 机械臂已断开")
    os._exit(0)


def init_robot():
    base = os.path.dirname(os.path.abspath(__file__))
    dll_path = os.path.join(base, "aubo", "aubo", "aubo_host_workspace", "lib", "serviceinterface2.dll")
    if not os.path.exists(dll_path):
        print(f"[错误] 找不到 DLL: {dll_path}")
        sys.exit(1)
    return AuboWindowsSDK(dll_path)


def connect_robot(robot):
    print(f"[连接] 正在连接 {ROBOT_IP}:{ROBOT_PORT} ...")
    success, msg = robot.connect(ROBOT_IP, ROBOT_PORT)
    if success:
        print(f"[连接] 成功")
    else:
        print(f"[连接] 失败: {msg}")
        sys.exit(1)
    robot.set_speed_percent(30)


def movej(robot, joints, label=""):
    deg_vals = [math.degrees(j) for j in joints]
    print(f"[移动] {label} → {[round(d, 1) for d in deg_vals]}°")
    success, msg = robot.movej_safe(joints)
    if success:
        print(f"[移动] {label} 完成")
    else:
        print(f"[移动] {label} 失败: {msg}")
        sys.exit(1)


def gripper_cmd(cmd=None, percent=None):
    try:
        if cmd is not None:
            http_requests.get(f"{GRIPPER_URL}/set?cmd={cmd}", timeout=5)
            print(f"[夹爪] cmd={cmd} ({'闭合' if cmd == 0 else '张开'})")
        if percent is not None:
            http_requests.get(f"{GRIPPER_URL}/set?percent={percent}", timeout=5)
            print(f"[夹爪] percent={percent}%")
    except Exception as e:
        print(f"[夹爪] 控制失败: {e}")


def main():
    global _robot

    signal.signal(signal.SIGINT, _cleanup_and_exit)
    signal.signal(signal.SIGTERM, _cleanup_and_exit)

    print("=" * 40)
    print("  咖啡机器人 Demo 开始")
    print("  按 Ctrl+C 可随时急停退出")
    print("=" * 40)

    _robot = init_robot()
    connect_robot(_robot)
    time.sleep(1)

    for i, (desc, action_type, params) in enumerate(STEPS):
        print(f"\n[步骤 {i+1}/{len(STEPS)}] {desc}")
        if action_type == "movej":
            movej(_robot, params, desc)
        elif action_type == "gripper":
            gripper_cmd(**params)
        elif action_type == "movej+gripper":
            joints, gripper_params = params
            movej(_robot, joints, desc)
            gripper_cmd(**gripper_params)
        time.sleep(1)

    try:
        _robot.disconnect()
    except Exception:
        pass
    print("\n[断开] 机械臂已断开")
    print("=" * 40)
    print("  咖啡机器人 Demo 完成")
    print("=" * 40)
    os._exit(0)


if __name__ == "__main__":
    main()
