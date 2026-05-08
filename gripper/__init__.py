from gripper.base import GripperController
from gripper.serial_gripper import SerialGripperController

GRIPPERS = {
    "serial": SerialGripperController,
    "none": GripperController,
}


def create_gripper(config: dict) -> GripperController:
    gripper_type = config["gripper"]["type"]
    if gripper_type not in GRIPPERS:
        raise ValueError(f"Unknown gripper type: {gripper_type}. Choose from: {list(GRIPPERS.keys())}")
    if gripper_type == "none":
        return GripperController(config)
    return GRIPPERS[gripper_type](config)
