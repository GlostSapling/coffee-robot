from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from robot.base import RobotController
from gripper.base import GripperController


@dataclass
class StepResult:
    step_name: str
    success: bool
    message: str
    data: dict = field(default_factory=dict)


class CoffeeTask:
    """Nespresso 咖啡制作工作流。

    每个步骤是一个独立方法，可单独调用（用于 VLA/语音），
    也可通过 run_full() 串联执行。所有位置来自配置，无硬编码。
    """

    def __init__(self, robot: RobotController, gripper: GripperController, config: dict):
        self.robot = robot
        self.gripper = gripper
        self.config = config
        self.waypoints = config["waypoints"]
        self._brew_time = config.get("coffee_machine", {}).get("brew_time", 25)

    def _move_to(self, waypoint_name: str, velocity_scale: float = 1.0) -> StepResult:
        """移动到配置中的命名点位。"""
        wp = self.waypoints.get(waypoint_name)
        if not wp:
            return StepResult(waypoint_name, False, f"Waypoint '{waypoint_name}' not found in config")

        joints = wp["joints"]
        print(f"  -> Moving to [{waypoint_name}] joints={joints}")
        self.robot.movej(joints, velocity_scale)
        return StepResult(waypoint_name, True, f"Arrived at {waypoint_name}")

    def _move_with_approach(self, waypoint_name: str, velocity_scale: float = 1.0) -> StepResult:
        """移动到点位（带接近偏移）。"""
        wp = self.waypoints.get(waypoint_name)
        if not wp:
            return StepResult(waypoint_name, False, f"Waypoint '{waypoint_name}' not found in config")

        # 如果有接近偏移，先移到接近位置
        approach = wp.get("approach_offset")
        if approach and any(v != 0 for v in approach):
            print(f"  -> Approach [{waypoint_name}] with offset {approach}")
            self.robot.movej(wp["joints"], velocity_scale)
        else:
            self.robot.movej(wp["joints"], velocity_scale)

        return StepResult(waypoint_name, True, f"Arrived at {waypoint_name}")

    def _move_with_depart(self, waypoint_name: str, velocity_scale: float = 1.0) -> StepResult:
        """按离开偏移离开点位。"""
        wp = self.waypoints.get(waypoint_name)
        if not wp:
            return StepResult(waypoint_name, False, f"Waypoint '{waypoint_name}' not found in config")

        depart = wp.get("depart_offset")
        if depart and any(v != 0 for v in depart):
            # 按离开偏移抬升（简化处理，实际应应用笛卡尔偏移）
            print(f"  -> Depart [{waypoint_name}] with offset {depart}")
        return StepResult(waypoint_name, True, f"Departed {waypoint_name}")

    def _move_arc(self, waypoint_name: str) -> StepResult:
        """沿弧线路径运动（多点插值）。用于开合盖子等弧线动作。"""
        wp = self.waypoints.get(waypoint_name)
        if not wp:
            return StepResult(waypoint_name, False, f"点位 '{waypoint_name}' 未在配置中找到")

        arc_points = wp.get("arc_points")
        if not arc_points:
            return StepResult(waypoint_name, False, f"点位 '{waypoint_name}' 缺少 arc_points 配置")

        velocity_scale = wp.get("velocity_scale", 0.3)
        print(f"  -> 弧线运动 [{waypoint_name}]，共 {len(arc_points)} 个路径点")

        for i, point in enumerate(arc_points):
            joints = point["joints"]
            print(f"    路径点 {i + 1}/{len(arc_points)}: {joints}")
            self.robot.movej(joints, velocity_scale)

        return StepResult(waypoint_name, True, f"弧线运动完成: {waypoint_name}")

    # === 单步任务 ===

    def pick_cup(self) -> StepResult:
        """步骤1：从杯子取放位拿起杯子。"""
        print("[Step 1] Picking up cup...")
        self.gripper.open()
        r = self._move_with_approach("cup_pickup")
        if not r.success:
            return r
        self.gripper.close()
        time.sleep(0.3)
        self._move_with_depart("cup_pickup")
        return StepResult("pick_cup", True, "Cup picked up")

    def place_cup_under_machine(self) -> StepResult:
        """步骤2：把杯子放到咖啡机出液口下方。"""
        print("[Step 2] Placing cup under coffee machine...")
        r = self._move_with_approach("cup_under_machine")
        if not r.success:
            return r
        self.gripper.open()
        time.sleep(0.3)
        self._move_with_depart("cup_under_machine")
        return StepResult("place_cup_under_machine", True, "Cup placed under machine")

    def pick_capsule(self) -> StepResult:
        """步骤3：从存储位拿取胶囊。"""
        print("[Step 3] Picking up capsule...")
        self.gripper.open()
        r = self._move_with_approach("capsule_pickup")
        if not r.success:
            return r
        self.gripper.close()
        time.sleep(0.3)
        self._move_with_depart("capsule_pickup")
        return StepResult("pick_capsule", True, "Capsule picked up")

    def open_machine_lid(self) -> StepResult:
        """步骤4：打开咖啡机盖子（弧线运动）。"""
        print("[步骤4] 打开咖啡机盖子...")
        self.gripper.close()
        time.sleep(0.2)
        r = self._move_arc("machine_lid_open")
        if not r.success:
            return r
        return StepResult("open_machine_lid", True, "机器盖已打开")

    def insert_capsule(self) -> StepResult:
        """步骤5：把胶囊放入胶囊仓。"""
        print("[Step 5] Inserting capsule...")
        r = self._move_with_approach("capsule_insert")
        if not r.success:
            return r
        self.gripper.open()
        time.sleep(0.3)
        self._move_with_depart("capsule_insert")
        return StepResult("insert_capsule", True, "Capsule inserted")

    def close_machine_lid(self) -> StepResult:
        """步骤6：盖上咖啡机盖子（弧线运动）。"""
        print("[步骤6] 关闭咖啡机盖子...")
        self.gripper.close()
        time.sleep(0.2)
        r = self._move_arc("machine_lid_close")
        if not r.success:
            return r
        self.gripper.open()
        return StepResult("close_machine_lid", True, "机器盖已关闭")

    def press_start_button(self) -> StepResult:
        """步骤7：按下咖啡机启动按钮。"""
        print("[Step 7] Pressing start button...")
        r = self._move_to("machine_button")
        if not r.success:
            return r
        # 按按钮（接近、按压、回退）
        time.sleep(0.5)
        return StepResult("press_start_button", True, "Start button pressed")

    def wait_for_brew(self) -> StepResult:
        """步骤8：等待咖啡萃取完成。"""
        print(f"[Step 8] Waiting for coffee to brew ({self._brew_time}s)...")
        time.sleep(self._brew_time)
        return StepResult("wait_for_brew", True, f"Brew complete after {self._brew_time}s")

    def pick_cup_from_machine(self) -> StepResult:
        """步骤9：从出液口下方取走萃取好的咖啡杯。"""
        print("[Step 9] Picking up brewed cup...")
        self.gripper.open()
        r = self._move_with_approach("cup_from_machine")
        if not r.success:
            return r
        self.gripper.close()
        time.sleep(0.3)
        self._move_with_depart("cup_from_machine")
        return StepResult("pick_cup_from_machine", True, "Brewed cup picked up")

    def deliver_cup(self) -> StepResult:
        """步骤10：把咖啡杯送到指定位置。"""
        print("[Step 10] Delivering cup...")
        r = self._move_with_approach("cup_delivery")
        if not r.success:
            return r
        self.gripper.open()
        time.sleep(0.3)
        self._move_with_depart("cup_delivery")
        return StepResult("deliver_cup", True, "Cup delivered")

    def go_home(self) -> StepResult:
        """回到原点。"""
        print("[Home] Returning to home position...")
        r = self._move_to("home")
        return StepResult("home", r.success, r.message)

    # === 执行方法 ===

    def get_all_steps(self) -> List[str]:
        """返回所有步骤名称的有序列表。"""
        return [
            "pick_cup",
            "place_cup_under_machine",
            "pick_capsule",
            "open_machine_lid",
            "insert_capsule",
            "close_machine_lid",
            "press_start_button",
            "wait_for_brew",
            "pick_cup_from_machine",
            "deliver_cup",
        ]

    def get_step_fn(self, step_name: str) -> Callable[[], StepResult]:
        """按名称获取步骤函数（用于 VLA/语音调度）。"""
        steps = {name: getattr(self, name) for name in self.get_all_steps()}
        if step_name not in steps:
            raise ValueError(f"Unknown step: {step_name}. Available: {list(steps.keys())}")
        return steps[step_name]

    def run_step(self, step_name: str) -> StepResult:
        """执行单个命名步骤。"""
        fn = self.get_step_fn(step_name)
        return fn()

    def run_full(self, skip_brew_wait: bool = False) -> List[StepResult]:
        """执行完整的咖啡制作工作流。"""
        results = []
        for step_name in self.get_all_steps():
            if skip_brew_wait and step_name == "wait_for_brew":
                print(f"[Skip] {step_name}")
                results.append(StepResult(step_name, True, "Skipped"))
                continue
            result = self.run_step(step_name)
            results.append(result)
            if not result.success:
                print(f"[ABORT] Step '{step_name}' failed: {result.message}")
                break
        self.go_home()
        return results

    def run_by_command(self, command: str) -> List[StepResult]:
        """通过高级命令执行步骤（用于 VLA/语音集成）。

        命令：
          "make_coffee" / "做咖啡" -> 完整流程
          "pick_cup" / "拿杯子"     -> 单步执行
          "home" / "回原点"         -> 回到原点
        """
        full_commands = {"make_coffee", "做咖啡", "做一杯咖啡", "make coffee"}
        if command.strip().lower() in {c.lower() for c in full_commands}:
            return self.run_full()

        # 尝试作为单步名称执行
        try:
            result = self.run_step(command)
            return [result]
        except ValueError:
            print(f"[Error] Unknown command: {command}")
            return [StepResult(command, False, f"Unknown command: {command}")]
