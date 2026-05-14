"""
关节移动脚本
用法: python move.py <j1> <j2> <j3> <j4> <j5> <j6>
参数为 6 个关节角度（度）

示例:
  python move.py -172.2 -62.5 73.5 120.2 82.9 -0.8
  python move.py 0 0 0 0 0 0  # 回零
"""

import sys
import os
import time
import math
import signal

# 添加 SDK 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "aubo", "aubo", "aubo_host_workspace"))
from aubo_sdk import AuboWindowsSDK
from coffee_config import ROBOT_IP, ROBOT_PORT

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


def main():
    global _robot

    # 检查参数
    if len(sys.argv) != 7:
        print("用法: python move.py <j1> <j2> <j3> <j4> <j5> <j6>")
        print("参数为 6 个关节角度（度）")
        print("\n示例:")
        print("  python move.py -172.2 -62.5 73.5 120.2 82.9 -0.8")
        print("  python move.py 0 0 0 0 0 0")
        sys.exit(1)

    # 解析关节角度
    try:
        joints_deg = [float(arg) for arg in sys.argv[1:7]]
    except ValueError:
        print("[错误] 所有关节参数必须是数字")
        sys.exit(1)

    # 转换为弧度
    joints_rad = [math.radians(d) for d in joints_deg]

    # 注册信号处理
    signal.signal(signal.SIGINT, _cleanup_and_exit)
    signal.signal(signal.SIGTERM, _cleanup_and_exit)

    print("=" * 40)
    print("  关节移动")
    print("  按 Ctrl+C 可随时急停退出")
    print("=" * 40)
    print(f"\n目标关节角度（度）:")
    for i, d in enumerate(joints_deg):
        print(f"  J{i+1}: {d:.1f}°")

    # 初始化并连接机器人
    _robot = init_robot()
    print(f"\n[连接] 正在连接 {ROBOT_IP}:{ROBOT_PORT} ...")
    success, msg = _robot.connect(ROBOT_IP, ROBOT_PORT)
    if not success:
        print(f"[连接] 失败: {msg}")
        sys.exit(1)
    print("[连接] 成功")
    _robot.set_speed_percent(30)

    # 执行移动
    print("\n[移动] 开始移动...")
    success, msg = _robot.movej_safe(joints_rad)
    if success:
        print("[移动] 完成")
    else:
        print(f"[移动] 失败: {msg}")
        _robot.disconnect()
        sys.exit(1)

    # 断开连接
    try:
        _robot.disconnect()
    except Exception:
        pass
    print("\n[断开] 机械臂已断开")


if __name__ == "__main__":
    main()
