#!/usr/bin/env python3
"""
Coffee Robot Demo - Aubo-i10 Nespresso Coffee Making

Usage:
    # Full workflow (dry run - no robot needed)
    python coffee_demo.py --dry-run

    # Full workflow with robot
    python coffee_demo.py

    # Single step
    python coffee_demo.py --step pick_cup

    # Custom config
    python coffee_demo.py --config my_config.yaml

    # Interactive command mode (for VLA/voice integration)
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
    print("  Coffee Task Results")
    print("=" * 50)
    for r in results:
        status = "OK" if r.success else "FAIL"
        print(f"  [{status}] {r.step_name}: {r.message}")
    print("=" * 50)


def print_dry_run(config: dict):
    """Print planned moves without executing."""
    print("\n" + "=" * 50)
    print("  DRY RUN - Planned Coffee Workflow")
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
            joints = wps[wp_name]["joints"]
            print(f"  {step_desc} -> {wp_name}: {joints}")
        else:
            print(f"  {step_desc} -> {wp_name}")
    print("\n  Gripper: open/close at each pick/place step")
    print("  Config: " + config["robot"]["backend"] + " backend")
    print("=" * 50)


def run_dry(config: dict):
    """Run in dry mode - print plan, then simulate with no-op robot/gripper."""
    print_dry_run(config)

    # Create a mock robot that just prints
    class DryRobot:
        connected = False
        def connect(self):
            print("[DryRobot] Connected (simulated)")
            self.connected = True
            return True
        def disconnect(self):
            print("[DryRobot] Disconnected")
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

    print("\n--- Starting dry run ---\n")
    results = task.run_full()
    print_results(results)


def run_real(config: dict, step: str = None):
    """Run with real robot."""
    robot = create_robot(config)
    gripper = create_gripper(config)

    print(f"Connecting to robot ({config['robot']['backend']})...")
    if not robot.connect():
        print("Failed to connect to robot. Exiting.")
        sys.exit(1)
    print("Robot connected.")

    # Connect gripper if serial
    if hasattr(gripper, "connect"):
        gripper.connect()

    try:
        task = CoffeeTask(robot, gripper, config)

        if step:
            print(f"\n--- Running single step: {step} ---\n")
            result = task.run_step(step)
            print_results([result])
        else:
            print("\n--- Starting full coffee workflow ---\n")
            results = task.run_full()
            print_results(results)
    finally:
        if hasattr(gripper, "disconnect"):
            gripper.disconnect()
        robot.disconnect()
        print("Robot disconnected.")


def run_interactive(config: dict):
    """Interactive mode for VLA/voice command testing."""
    robot = create_robot(config)
    gripper = create_gripper(config)

    print(f"Connecting to robot ({config['robot']['backend']})...")
    if not robot.connect():
        print("Failed to connect to robot. Exiting.")
        sys.exit(1)
    print("Robot connected.\n")

    if hasattr(gripper, "connect"):
        gripper.connect()

    task = CoffeeTask(robot, gripper, config)

    print("Interactive Coffee Robot")
    print("=" * 40)
    print("Commands:")
    print("  make_coffee / 做咖啡    - Full workflow")
    for name in task.get_all_steps():
        print(f"  {name}")
    print("  home / 回原点           - Return home")
    print("  quit / exit              - Exit")
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
        print("Robot disconnected.")


def main():
    parser = argparse.ArgumentParser(description="Coffee Robot Demo - Aubo-i10 Nespresso")
    parser.add_argument(
        "--config", "-c",
        default=os.path.join(os.path.dirname(__file__), "config", "coffee_task.yaml"),
        help="Path to config YAML file",
    )
    parser.add_argument("--dry-run", "-n", action="store_true", help="Dry run (no robot needed)")
    parser.add_argument("--step", "-s", type=str, default=None, help="Run a single step by name")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive command mode")
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
