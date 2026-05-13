# 咖啡机器人 - Aubo-i10 Nespresso 自动咖啡制作系统

基于遨博 Aubo-i10 机械臂的自动咖啡制作 Demo。机械臂完成从拿杯子、放胶囊、到出杯的全流程自动化操作，支持后续接入 OpenClaw 语音控制。

## 工作流程

```
张开夹爪 → 移动到抓杯点位 → 夹爪闭合抓杯 → 移动到中间姿态 → 移动到咖啡机 → 松开夹爪放杯 → 移出咖啡机 → 开盖+夹爪调整 → 推盖中间 → 推盖子
```

共 10 个步骤，按顺序自动执行。

## 项目结构

```
coffee-robot/
├── aubo/
│   └── aubo/
│       └── aubo_host_workspace/
│           ├── main.py              # Tkinter GUI 主程序
│           ├── aubo_sdk.py          # Aubo SDK 封装
│           ├── coffee_config.py     # 咖啡流程配置（点位、IP）
│           ├── api_server.py        # WebAPI 服务
│           └── lib/                 # DLL 依赖文件
├── demo_coffee.py                   # 咖啡制作 Demo 主入口
├── requirements.txt
├── CLAUDE.md
└── README.md
```

## 环境准备

### Python 依赖

```bash
pip install -r requirements.txt
```

依赖列表：
- `fastapi` - WebAPI 框架
- `uvicorn` - ASGI 服务器
- `pydantic` - 数据验证
- `requests` - HTTP 客户端
- `opencv-python` - 图像处理
- `numpy` - 数值计算
- `pyorbbecsdk` - Orbbec 深度相机 SDK
- `pyserial` - 串口通信
- `pyyaml` - YAML 配置

### 系统要求

- **操作系统**: Windows 10/11（Aubo SDK 仅支持 Windows）
- **Python**: 3.8+（推荐 3.10/3.11）
- **机械臂**: Aubo i10H + 遨博控制器（端口 8899）
- **相机**（可选）: Orbbec 深度相机

### DLL 依赖

所有必需的 DLL 文件已包含在 `aubo/aubo/aubo_host_workspace/lib/` 目录中：
- `serviceinterface2.dll` - Aubo 机器人控制器接口
- `libgcc_s_seh-1.dll`, `libstdc++-6.dll`, `libwinpthread-1.dll` - MinGW 运行时

## 使用方法

### 方式一：直接运行 Demo（推荐）

```bash
python demo_coffee.py
```

这将：
1. 连接到机械臂（IP: 192.168.31.6，端口: 8899）
2. 按顺序执行全部 10 个步骤
3. 完成后自动断开连接

**注意**: 运行前请确保：
- 机械臂已上电并连接到网络
- `aubo/aubo/aubo_host_workspace/coffee_config.py` 中的 IP 地址正确
- 夹爪控制器已连接（IP: 192.168.31.10）

### 方式二：使用 GUI 上位机

```bash
cd aubo/aubo/aubo_host_workspace
python main.py
```

启动 Tkinter 图形界面，可以：
- 手动连接/断开机械臂
- 控制机械臂移动
- 启动 WebAPI 服务（默认端口 8000）
- 捕获相机图像和视频

### 方式三：通过 WebAPI 远程控制

1. 先启动上位机 GUI
2. 在 GUI 中连接机械臂并启动 WebAPI 服务
3. 使用 HTTP 请求控制机械臂：

```bash
# 检查连接状态
curl http://127.0.0.1:8000/api/status

# 连接机械臂
curl -X POST http://127.0.0.1:8000/api/connect \
  -H "Content-Type: application/json" \
  -d '{"ip":"192.168.31.6","port":8899}'

# 移动关节（弧度）
curl -X POST http://127.0.0.1:8000/api/movej \
  -H "Content-Type: application/json" \
  -d '{"joints":[0.3, -0.5, 0.8, 0.0, 0.5, 0.0]}'
```

## 配置说明

### 机械臂配置

在 `aubo/aubo/aubo_host_workspace/coffee_config.py` 中修改：

```python
ROBOT_IP = "192.168.31.6"    # 机械臂控制器 IP
ROBOT_PORT = 8899             # 控制器端口
GRIPPER_IP = "192.168.31.10"  # 夹爪控制器 IP
```

### 点位配置

所有点位以 6 轴关节角（弧度）表示：

```python
POS_HOME = [-3.0075, -0.0247, 2.1940, 2.0989, 1.2444, -0.0142]  # 初始位姿
POS_GRAB = [-2.9943, -1.0912, 1.2830, 2.3219, 1.4476, -0.0142]  # 抓杯子点位
POS_MID = [-2.9077, -0.7870, 1.6746, 2.3219, 1.4476, -0.0142]   # 中间姿态
POS_COFFEE = [-2.7957, -1.1157, 1.2347, 2.3217, 1.2838, -0.0142] # 咖啡机位置
```

> **重要**: 当前配置中的点位是实际测量值，可根据实际情况调整。

### 流程步骤配置

在 `STEPS` 列表中定义执行顺序：

```python
STEPS = [
    ("张开夹爪",          "gripper",  {"percent": 100}),
    ("移动到抓杯点位",    "movej",    POS_GRAB),
    ("夹爪闭合5%抓杯",    "gripper",  {"percent": 5}),
    # ... 更多步骤
]
```

动作类型：
- `"movej"` - 移动关节到指定位置
- `"gripper"` - 控制夹爪（percent: 0-100）
- `"movej+gripper"` - 同时移动和控制夹爪

## ROS2 集成

### 启动 ROS2 桥接节点（Ubuntu）

```bash
source /opt/ros/humble/setup.bash
pip3 install requests
python3 aubo/aubo/aubo_host_workspace/aubo_ros2_http_bridge.py \
  --host_ip <WINDOWS_IP> \
  --host_port 8001
```

这将：
- 订阅 `/aubo/joint_cmds` 话题并转发到 WebAPI
- 发布 `/joint_states` 话题（从 WebAPI 获取状态）

## 故障排除

### 连接失败

1. 检查机械臂 IP 地址是否正确
2. 确认机械臂已上电并连接到网络
3. 检查防火墙设置（端口 8899）
4. 使用 `ping 192.168.31.6` 测试网络连通性

### DLL 加载失败

确保 `aubo/aubo/aubo_host_workspace/lib/` 目录包含所有必需的 DLL 文件。

### 夹爪无响应

1. 检查夹爪控制器 IP 地址（默认 192.168.31.10）
2. 确认夹爪控制器已上电
3. 使用 `curl http://192.168.31.10` 测试连通性

## 后续扩展

### 接入 OpenClaw 语音控制

可以扩展 `demo_coffee.py` 添加语音命令支持：

```python
# 示例：语音命令映射
voice_commands = {
    "做咖啡": "full_flow",
    "拿杯子": "pick_cup",
    "放胶囊": "insert_capsule",
}
```

### 自定义夹爪协议

修改 `demo_coffee.py` 中的 `gripper_cmd()` 函数，或在配置中添加夹爪控制参数。

### 切换机械臂后端

- **Windows**: 使用 WebAPI 远程控制（当前方案）
- **Ubuntu**: 使用 libpyauboi5 本地 SDK 直连

## 许可证

本项目为内部 Demo，仅供学习和研究使用。
