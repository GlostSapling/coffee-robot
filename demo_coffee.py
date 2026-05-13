"""
咖啡机器人 Demo
流程: 抓杯子 → 运送到咖啡机 → 放下杯子

直接调用 Aubo SDK，不经过 WebAPI。
支持分段运行：python demo_coffee.py --step 抓杯子
"""

import sys
import os
import time
import math
import signal
import argparse
import requests as http_requests

# 添加 SDK 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "aubo", "aubo", "aubo_host_workspace"))
from aubo_sdk import AuboWindowsSDK
from coffee_config import ROBOT_IP, ROBOT_PORT, GRIPPER_URL, STEPS

# 全局引用，用于信号处理
_robot = None

# 步骤名称映射（中文/英文 → 步骤索引）
STEP_ALIASES = {
    # 中文名称
    "张开夹爪": 0,
    "抓杯子": 1,
    "夹爪闭合": 2,
    "移动中间": 3,
    "移动咖啡机": 4,
    "放杯子": 5,
    "移出咖啡机": 6,
    "开盖": 7,
    "推盖中间": 8,
    "推盖子": 9,

    # 英文名称
    "open_gripper": 0,
    "pick_cup": 1,
    "close_gripper": 2,
    "move_mid": 3,
    "move_coffee": 4,
    "place_cup": 5,
    "move_out": 6,
    "open_lid": 7,
    "push_mid": 8,
    "push_lid": 9,

    # 简写
    "抓杯": 1,
    "放杯": 5,
    "开盖子": 7,
    "推盖": 9,
}


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


def execute_step(step_index):
    """执行单个步骤"""
    if step_index < 0 or step_index >= len(STEPS):
        print(f"[错误] 步骤索引 {step_index} 超出范围 (0-{len(STEPS)-1})")
        return False

    desc, action_type, params = STEPS[step_index]
    print(f"\n[步骤 {step_index+1}/{len(STEPS)}] {desc}")

    if action_type == "movej":
        movej(_robot, params, desc)
    elif action_type == "gripper":
        gripper_cmd(**params)
    elif action_type == "movej+gripper":
        joints, gripper_params = params
        movej(_robot, joints, desc)
        gripper_cmd(**gripper_params)

    return True


def print_available_steps():
    """打印所有可用的步骤名称"""
    print("\n可用的步骤名称：")
    print("-" * 50)
    for i, (desc, _, _) in enumerate(STEPS):
        print(f"  {i+1:2d}. {desc}")
    print("\n别名映射：")
    print("-" * 50)
    for alias, idx in sorted(STEP_ALIASES.items(), key=lambda x: x[1]):
        print(f"  {alias:15s} → 步骤 {idx+1}")


def parse_step_arg(step_arg):
    """解析步骤参数，支持数字、中文、英文"""
    # 尝试解析为数字
    try:
        idx = int(step_arg) - 1  # 用户输入从1开始
        if 0 <= idx < len(STEPS):
            return idx
    except ValueError:
        pass

    # 尝试匹配别名
    step_lower = step_arg.lower().strip()
    if step_lower in STEP_ALIASES:
        return STEP_ALIASES[step_lower]

    # 模糊匹配：检查输入是否包含在步骤描述中
    for i, (desc, _, _) in enumerate(STEPS):
        if step_arg in desc:
            return i

    return None


def main():
    global _robot

    parser = argparse.ArgumentParser(description="咖啡机器人 Demo")
    parser.add_argument("--step", type=str, help="执行单个步骤（支持数字、中文、英文名称）")
    parser.add_argument("--list", action="store_true", help="列出所有可用步骤")
    parser.add_argument("--from", type=str, dest="from_step", help="从指定步骤开始执行")
    parser.add_argument("--to", type=str, help="执行到指定步骤（配合 --from 使用）")

    args = parser.parse_args()

    # 列出所有步骤
    if args.list:
        print_available_steps()
        return

    signal.signal(signal.SIGINT, _cleanup_and_exit)
    signal.signal(signal.SIGTERM, _cleanup_and_exit)

    print("=" * 40)
    print("  咖啡机器人 Demo")
    print("  按 Ctrl+C 可随时急停退出")
    print("=" * 40)

    _robot = init_robot()
    connect_robot(_robot)
    time.sleep(1)

    # 执行单个步骤
    if args.step:
        step_idx = parse_step_arg(args.step)
        if step_idx is None:
            print(f"[错误] 无法识别步骤: {args.step}")
            print("使用 --list 查看所有可用步骤")
            _robot.disconnect()
            sys.exit(1)

        execute_step(step_idx)

    # 从指定步骤开始执行
    elif args.from_step:
        from_idx = parse_step_arg(args.from_step)
        if from_idx is None:
            print(f"[错误] 无法识别起始步骤: {args.from_step}")
            _robot.disconnect()
            sys.exit(1)

        to_idx = len(STEPS) - 1
        if args.to:
            to_idx = parse_step_arg(args.to)
            if to_idx is None:
                print(f"[错误] 无法识别结束步骤: {args.to}")
                _robot.disconnect()
                sys.exit(1)

        print(f"\n[执行] 从步骤 {from_idx+1} 到步骤 {to_idx+1}")
        for i in range(from_idx, to_idx + 1):
            if not execute_step(i):
                break
            time.sleep(1)

    # 完整执行
    else:
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
