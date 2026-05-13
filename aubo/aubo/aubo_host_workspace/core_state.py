# core_state.py
# 全局状态管理：在 GUI / WebAPI / ROS2API 之间共享对象与运行状态

robot = None
camera_service = None
media_store = None

web_api_running = False
web_api_port = 8000
ros2_api_running = False
ros2_api_port = 8001


def set_robot(robot_instance):
    global robot
    robot = robot_instance


def get_robot():
    return robot


def set_camera_service(service):
    global camera_service
    camera_service = service


def get_camera_service():
    return camera_service


def set_media_store(store):
    global media_store
    media_store = store


def get_media_store():
    return media_store
