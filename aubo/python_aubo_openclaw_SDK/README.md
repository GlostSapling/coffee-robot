# python_aubo_openclaw_SDK

这是一个独立的 Python 单文件 SDK，用于调用你当前上位机的两套接口：

- `WebAPI`（默认端口 `8000`）：网页控制与通用业务接口
- `ROS2API`（默认端口 `8001`）：专用于 ROS2 桥接调用

## 1. 目录结构

```text
python_aubo_openclaw_SDK/
├─ aubo_openclaw_sdk.py
└─ README.md
```

## 2. 前置条件

- 你的上位机程序已启动。
- 在 GUI 的 API 页面已分别启动：
  - `WebAPI`
  - `ROS2API`
- Python 环境安装依赖：

```bash
pip install requests
```

## 3. 快速开始

```python
from aubo_openclaw_sdk import AuboOpenclawSDK

sdk = AuboOpenclawSDK(
    host="127.0.0.1",   # 上位机 IP
    webapi_port=8000,   # WebAPI 端口
    ros2api_port=8001   # ROS2API 端口
)

print(sdk.get_system_info())
```

## 4. 机械臂接口（WebAPI）

- `get_system_info()`：获取系统状态
- `connect_robot(ip, port=8899)`：连接机械臂
- `disconnect_robot()`：断开机械臂
- `get_robot_status()`：获取当前关节与位姿
- `movej(joints)`：执行关节运动（`joints` 必须 6 轴）

示例：

```python
sdk.connect_robot("192.168.10.3")
status = sdk.get_robot_status()
print(status)
sdk.movej([0, 0, 0, 0, 0, 0])
```

## 5. 相机接口（WebAPI）

- `list_cameras()`：枚举相机
- `select_camera(serial)`：按序列号切换相机
- `capture_photo()`：RGB 拍照
- `capture_video(duration_sec)`：RGB 录像
- `capture_depth_photo()`：深度拍照
- `capture_depth_video(duration_sec)`：深度录像
- `list_media()`：媒体记录列表
- `delete_media(record_id)`：删除媒体记录
- `get_media_file_url(record_id)`：获取媒体文件下载/打开 URL

示例：

```python
cams = sdk.list_cameras()
print(cams)

sdk.capture_photo()
sdk.capture_depth_video(5)

media = sdk.list_media()
print(media)
```

## 6. ROS2 接口（ROS2API）

- `ros2_info()`
- `ros2_connect(ip, port=8899)`
- `ros2_disconnect()`
- `ros2_status()`
- `ros2_movej(joints)`

示例：

```python
sdk.ros2_connect("192.168.10.3")
print(sdk.ros2_status())
sdk.ros2_movej([0, 0, 0, 0, 0, 0])
```

## 7. 异常处理

SDK 请求失败会抛出 `SDKError`：

```python
from aubo_openclaw_sdk import AuboOpenclawSDK, SDKError

sdk = AuboOpenclawSDK(host="127.0.0.1")
try:
    print(sdk.get_system_info())
except SDKError as e:
    print("调用失败:", e)
```

## 8. 说明

- Web 页面的可视化操作，本质也是调用 WebAPI。
- ROS2 桥接建议只调用 ROS2API，避免和前端业务接口混用。
- 如果你改了端口，初始化 SDK 时同步修改 `webapi_port` 与 `ros2api_port`。
