#!/usr/bin/env python3
"""
咖啡机器人 Demo - Aubo-i10 Nespresso 自动咖啡制作

用法:
    # 仿真模式（不需要连接机器人）
    python coffee_demo.py --dry-run

    # 完整流程（连接机器人）
    python coffee_demo.py

    # 执行单个步骤
    python coffee_demo.py --step pick_cup

    # 指定配置文件
    python coffee_demo.py --config my_config.yaml

    # 交互模式（语音/VLA 测试入口）
    python coffee_demo.py --interactive
"""

import argparse
import sys
import os
import yaml
from typing import List

from robot import create_robot
from gripper import create_gripper
from tasks.coffee_task import CoffeeTask, StepResult


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def print_results(results: List[StepResult]):
    print("\n" + "=" * 50)
    print("  咖啡任务执行结果")
    print("=" * 50)
    for r in results:
        status = "OK" if r.success else "FAIL"
        print(f"  [{status}] {r.step_name}: {r.message}")
    print("=" * 50)


def print_dry_run(config: dict):
    """打印计划动作（不执行）。"""
    print("\n" + "=" * 50)
    print("  仿真模式 - 咖啡工作流计划")
    print("=" * 50)
    wps = config["waypoints"]
    steps = [
        ("1. pick_cup", "cup_pickup"),
        ("2. place_cup_under_machine", "cup_under_machine"),
        ("3. pick_capsule", "capsule_pickup"),
        ("4. open_machine_lid", "machine_lid_open"),
        ("5. insert_capsule", "capsule_insert"),
        ("6. close_machine_lid", "machine_lid_close"),
        ("7. press_start_button", "machine_button"),
        ("8. wait_for_brew", f"wait {config.get('coffee_machine', {}).get('brew_time', 25)}s"),
        ("9. pick_cup_from_machine", "cup_from_machine"),
        ("10. deliver_cup", "cup_delivery"),
    ]
    for step_desc, wp_name in steps:
        if wp_name in wps:
            wp = wps[wp_name]
            if "arc_points" in wp:
                count = len(wp["arc_points"])
                print(f"  {step_desc} -> {wp_name}: 弧线运动（{count} 个路径点）")
            elif "joints" in wp:
                print(f"  {step_desc} -> {wp_name}: {wp['joints']}")
            else:
                print(f"  {step_desc} -> {wp_name}")
        else:
            print(f"  {step_desc} -> {wp_name}")
    print("\n  夹爪：每个取放步骤执行 open/close")
    print("  后端：" + config["robot"]["backend"])
    print("=" * 50)


def run_dry(config: dict):
    """仿真模式：打印计划，用空操作的机器人/夹爪模拟执行。"""
    print_dry_run(config)

    # 创建一个只打印日志的模拟机器人
    class DryRobot:
        connected = False
        def connect(self):
            print("[DryRobot] 已连接（模拟）")
            self.connected = True
            return True
        def disconnect(self):
            print("[DryRobot] 已断开")
            self.connected = False
        def movej(self, joints, vs=1.0):
            print(f"[DryRobot] movej({[round(j, 3) for j in joints]})")
        def movel(self, pose, vs=1.0):
            print(f"[DryRobot] movel({pose})")
        def get_joint_positions(self):
            return [0.0] * 6
        def get_pose(self):
            from robot.base import Pose
            return Pose(position=[0, 0, 0], orientation=[1, 0, 0, 0])

    class DryGripper:
        _gripping = False
        def open(self):
            print("[DryGripper] Open")
            self._gripping = False
        def close(self):
            print("[DryGripper] Close")
            self._gripping = True
        def is_gripping(self):
            return self._gripping

    robot = DryRobot()
    gripper = DryGripper()
    task = CoffeeTask(robot, gripper, config)

    print("\n--- 开始仿真运行 ---\n")
    results = task.run_full()
    print_results(results)


def run_real(config: dict, step: str = None):
    """连接真实机器人执行。"""
    robot = create_robot(config)
    gripper = create_gripper(config)

    print(f"正在连接机器人（{config['robot']['backend']}）...")
    if not robot.connect():
        print("机器人连接失败，退出。")
        sys.exit(1)
    print("机器人已连接。")

    # 如果是串口夹爪则连接
    if hasattr(gripper, "connect"):
        gripper.connect()

    try:
        task = CoffeeTask(robot, gripper, config)

        if step:
            print(f"\n--- 执行单步：{step} ---\n")
            result = task.run_step(step)
            print_results([result])
        else:
            print("\n--- 开始完整咖啡工作流 ---\n")
            results = task.run_full()
            print_results(results)
    finally:
        if hasattr(gripper, "disconnect"):
            gripper.disconnect()
        robot.disconnect()
        print("机器人已断开。")


def run_interactive(config: dict):
    """交互模式：用于 VLA/语音命令测试。"""
    robot = create_robot(config)
    gripper = create_gripper(config)

    print(f"正在连接机器人（{config['robot']['backend']}）...")
    if not robot.connect():
        print("机器人连接失败，退出。")
        sys.exit(1)
    print("机器人已连接。\n")

    if hasattr(gripper, "connect"):
        gripper.connect()

    task = CoffeeTask(robot, gripper, config)

    print("交互式咖啡机器人")
    print("=" * 40)
    print("可用命令：")
    print("  make_coffee / 做咖啡    - 完整流程")
    for name in task.get_all_steps():
        print(f"  {name}")
    print("  home / 回原点           - 回到原点")
    print("  quit / exit              - 退出")
    print("=" * 40)

    try:
        while True:
            try:
                cmd = input("\n> ").strip()
            except EOFError:
                break
            if not cmd:
                continue
            if cmd.lower() in ("quit", "exit", "q"):
                break
            results = task.run_by_command(cmd)
            print_results(results)
    finally:
        if hasattr(gripper, "disconnect"):
            gripper.disconnect()
        robot.disconnect()
        print("机器人已断开。")


def main():
    parser = argparse.ArgumentParser(description="咖啡机器人 Demo - Aubo-i10 Nespresso 自动咖啡制作")
    parser.add_argument(
        "--config", "-c",
        default=os.path.join(os.path.dirname(__file__), "config", "coffee_task.yaml"),
        help="配置文件路径",
    )
    parser.add_argument("--dry-run", "-n", action="store_true", help="仿真模式（不需要连接机器人）")
    parser.add_argument("--step", "-s", type=str, default=None, help="执行单个步骤（按名称）")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互命令模式")
    args = parser.parse_args()

    config = load_config(args.config)

    if args.dry_run:
        run_dry(config)
    elif args.interactive:
        run_interactive(config)
    else:
        run_real(config, step=args.step)


if __name__ == "__main__":
    main()
