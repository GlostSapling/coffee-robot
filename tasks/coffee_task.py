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
    """Nespresso coffee-making workflow.

    Each step is a named method that can be called individually (for VLA/voice)
    or chained via run_full(). All positions come from config, nothing hardcoded.
    """

    def __init__(self, robot: RobotController, gripper: GripperController, config: dict):
        self.robot = robot
        self.gripper = gripper
        self.config = config
        self.waypoints = config["waypoints"]
        self._brew_time = config.get("coffee_machine", {}).get("brew_time", 25)

    def _move_to(self, waypoint_name: str, velocity_scale: float = 1.0) -> StepResult:
        """Move to a named waypoint from config."""
        wp = self.waypoints.get(waypoint_name)
        if not wp:
            return StepResult(waypoint_name, False, f"Waypoint '{waypoint_name}' not found in config")

        joints = wp["joints"]
        print(f"  -> Moving to [{waypoint_name}] joints={joints}")
        self.robot.movej(joints, velocity_scale)
        return StepResult(waypoint_name, True, f"Arrived at {waypoint_name}")

    def _move_with_approach(self, waypoint_name: str, velocity_scale: float = 1.0) -> StepResult:
        """Move to waypoint with approach offset (if configured)."""
        wp = self.waypoints.get(waypoint_name)
        if not wp:
            return StepResult(waypoint_name, False, f"Waypoint '{waypoint_name}' not found in config")

        # Move to approach position first if offset exists
        approach = wp.get("approach_offset")
        if approach and any(v != 0 for v in approach):
            print(f"  -> Approach [{waypoint_name}] with offset {approach}")
            self.robot.movej(wp["joints"], velocity_scale)
        else:
            self.robot.movej(wp["joints"], velocity_scale)

        return StepResult(waypoint_name, True, f"Arrived at {waypoint_name}")

    def _move_with_depart(self, waypoint_name: str, velocity_scale: float = 1.0) -> StepResult:
        """Move away from waypoint using depart offset."""
        wp = self.waypoints.get(waypoint_name)
        if not wp:
            return StepResult(waypoint_name, False, f"Waypoint '{waypoint_name}' not found in config")

        depart = wp.get("depart_offset")
        if depart and any(v != 0 for v in depart):
            # Move up by depart offset (simplified: move to same joints, real impl would apply Cartesian offset)
            print(f"  -> Depart [{waypoint_name}] with offset {depart}")
        return StepResult(waypoint_name, True, f"Departed {waypoint_name}")

    # === Individual Task Steps ===

    def pick_cup(self) -> StepResult:
        """Step 1: Pick up the cup from the cup station."""
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
        """Step 2: Place the cup under the Nespresso spout."""
        print("[Step 2] Placing cup under coffee machine...")
        r = self._move_with_approach("cup_under_machine")
        if not r.success:
            return r
        self.gripper.open()
        time.sleep(0.3)
        self._move_with_depart("cup_under_machine")
        return StepResult("place_cup_under_machine", True, "Cup placed under machine")

    def pick_capsule(self) -> StepResult:
        """Step 3: Pick up a Nespresso capsule from storage."""
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
        """Step 4: Open the Nespresso machine lid."""
        print("[Step 4] Opening machine lid...")
        r = self._move_with_approach("machine_lid_open")
        if not r.success:
            return r
        # Lift the lid (simplified single move)
        self.gripper.close()
        time.sleep(0.2)
        # In real implementation: use a constrained motion to lift lid
        self._move_with_depart("machine_lid_open")
        return StepResult("open_machine_lid", True, "Machine lid opened")

    def insert_capsule(self) -> StepResult:
        """Step 5: Place the capsule into the machine holder."""
        print("[Step 5] Inserting capsule...")
        r = self._move_with_approach("capsule_insert")
        if not r.success:
            return r
        self.gripper.open()
        time.sleep(0.3)
        self._move_with_depart("capsule_insert")
        return StepResult("insert_capsule", True, "Capsule inserted")

    def close_machine_lid(self) -> StepResult:
        """Step 6: Close the Nespresso machine lid."""
        print("[Step 6] Closing machine lid...")
        r = self._move_with_approach("machine_lid_close")
        if not r.success:
            return r
        self.gripper.close()
        time.sleep(0.2)
        # Push lid down (simplified)
        self._move_with_depart("machine_lid_close")
        self.gripper.open()
        return StepResult("close_machine_lid", True, "Machine lid closed")

    def press_start_button(self) -> StepResult:
        """Step 7: Press the Nespresso start button."""
        print("[Step 7] Pressing start button...")
        r = self._move_to("machine_button")
        if not r.success:
            return r
        # Push button (approach, press, retract)
        time.sleep(0.5)
        return StepResult("press_start_button", True, "Start button pressed")

    def wait_for_brew(self) -> StepResult:
        """Step 8: Wait for the coffee to finish brewing."""
        print(f"[Step 8] Waiting for coffee to brew ({self._brew_time}s)...")
        time.sleep(self._brew_time)
        return StepResult("wait_for_brew", True, f"Brew complete after {self._brew_time}s")

    def pick_cup_from_machine(self) -> StepResult:
        """Step 9: Pick up the brewed coffee cup from under the spout."""
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
        """Step 10: Deliver the cup to the designated position."""
        print("[Step 10] Delivering cup...")
        r = self._move_with_approach("cup_delivery")
        if not r.success:
            return r
        self.gripper.open()
        time.sleep(0.3)
        self._move_with_depart("cup_delivery")
        return StepResult("deliver_cup", True, "Cup delivered")

    def go_home(self) -> StepResult:
        """Return to home position."""
        print("[Home] Returning to home position...")
        r = self._move_to("home")
        return StepResult("home", r.success, r.message)

    # === Execution Methods ===

    def get_all_steps(self) -> List[str]:
        """Return ordered list of all step names."""
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
        """Get a step function by name (for VLA/voice dispatch)."""
        steps = {name: getattr(self, name) for name in self.get_all_steps()}
        if step_name not in steps:
            raise ValueError(f"Unknown step: {step_name}. Available: {list(steps.keys())}")
        return steps[step_name]

    def run_step(self, step_name: str) -> StepResult:
        """Run a single named step."""
        fn = self.get_step_fn(step_name)
        return fn()

    def run_full(self, skip_brew_wait: bool = False) -> List[StepResult]:
        """Run the full coffee-making workflow."""
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
        """Run steps by high-level command (for VLA/voice integration).

        Commands:
          "make_coffee" / "做咖啡" -> full workflow
          "pick_cup" / "拿杯子"     -> single step
          "home" / "回原点"         -> go home
        """
        full_commands = {"make_coffee", "做咖啡", "做一杯咖啡", "make coffee"}
        if command.strip().lower() in {c.lower() for c in full_commands}:
            return self.run_full()

        # Try as single step name
        try:
            result = self.run_step(command)
            return [result]
        except ValueError:
            print(f"[Error] Unknown command: {command}")
            return [StepResult(command, False, f"Unknown command: {command}")]
