from robot.base import RobotController
from robot.webapi_backend import WebAPIRobotController
from robot.local_backend import LocalRobotController

BACKENDS = {
    "webapi": WebAPIRobotController,
    "local": LocalRobotController,
}


def create_robot(config: dict) -> RobotController:
    backend_name = config["robot"]["backend"]
    if backend_name not in BACKENDS:
        raise ValueError(f"Unknown backend: {backend_name}. Choose from: {list(BACKENDS.keys())}")
    return BACKENDS[backend_name](config)
