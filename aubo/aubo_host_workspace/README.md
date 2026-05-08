# 遨博机器人 Windows 综合上位机 (Aubo Host Gateway)

本项目用于旧版遨博控制器（`8899` 端口）在 Windows 上实现：

- 本地 GUI 控制（连接、监控、目标点位、滑条控制）
- WebAPI 服务（供外部系统调用）
- ROS2 桥接（Ubuntu/ROS2 通过 HTTP 间接控制实机）

适合“机械臂控制器偏旧 + 上层系统是 ROS2 Humble”的混合环境。

## 1. 目录结构

- `main.py`：GUI 主程序（Tkinter），可启动 WebAPI 服务。
- `aubo_sdk.py`：SDK 封装层，含软限位校验、不可达提示、安全执行。
- `api_server.py`：FastAPI 服务，提供 `/api/*` 接口。
- `core_state.py`：GUI 与 API 共享状态（robot 对象）。
- `aubo_ros2_http_bridge.py`：Ubuntu 侧 ROS2 桥接节点。
- `lib/`：运行所需 DLL（`serviceinterface2.dll` 等）。
- `build_exe.ps1`：Windows 一键打包脚本。

## 2. 环境准备

### 2.1 Windows（上位机）

1. 安装 Python 3.8+（推荐 3.10/3.11）。
2. 进入项目目录安装依赖：

```bash
pip install fastapi uvicorn pydantic requests pyinstaller pyorbbecsdk opencv-python numpy
```

### 2.2 Ubuntu（ROS2 侧）

1. 已安装 ROS2（如 Humble）。
2. 安装 Python 依赖：

```bash
pip3 install requests
```

## 3. GUI 使用说明（完整流程）

### 3.1 启动 GUI

在 Windows 项目目录执行：

```bash
python main.py
```

### 3.2 连接机械臂

1. 在“仪表盘与控制”页输入机械臂 IP。
2. 点击“连接实机”。
3. 连接成功后会显示：
   - 末端位置（XYZ）
   - 末端姿态（WXYZ）
   - 六轴关节角（rad）

### 3.3 目标点位与滑条控制

1. 点击“读取当前姿态到滑条”，将当前关节角同步到 6 轴滑条。
2. 拖动滑条设置目标（单位 `°`）。
3. 如需复用位置：
   - 输入点位名称
   - 点击“保存当前滑条为点位”
   - 后续可在“已存点位”选择并“加载点位到滑条”
4. 点击“执行到目标点位”。
5. 系统会执行前校验：
   - 是否连接机械臂
   - 关节数量是否为 6
   - 是否超软限位
   - 单次跳变是否过大
6. 如被控制器拒绝，会提示“目标点位可能不可达”。

### 3.4 校验与限位逻辑

- 软限位默认在 `aubo_sdk.py` 的 `JOINT_LIMITS_DEG` 中配置（当前每轴 `[-175°, 175°]`）。
- 单次跳变阈值 `MAX_SINGLE_STEP_DEG` 默认 `90°`，超出会建议分步运动。
- 你可以按实际机型修改这两个参数。

### 3.5 相机影像功能（Gemini335L / pyorbbecsdk）

GUI 在“仪表盘与控制”页新增“Gemini335L 相机影像”区域，提供：

- `拍照（1帧）`
- `录像 3 秒（常规画质）`
- `录像 5 秒（常规画质）`
- `录像 10 秒（常规画质）`

执行结果会写入本地 SQLite 数据库并保存媒体文件，随后在“本地影像列表（SQLite映射）”中展示。

本地存储目录：

- `app_data/media/`：图片与视频文件
- `app_data/media.db`：SQLite 映射数据库

列表项右侧操作按钮：

- `播放`：弹出播放窗口（OpenCV 窗口，图片/视频均支持）
- `删除`：删除数据库记录及对应文件

说明：

- 若提示相机不可用，请确认已安装 `pyorbbecsdk/opencv-python/numpy`，并且相机可被系统识别。
- 视频采用常规画质与常规帧率（目标约 20fps，实际以设备输出为准）。

## 4. WebAPI 服务文档

### 4.1 启动方式

在 GUI 第二页“WebAPI 服务”中：

1. 输入端口（默认 `8000`）
2. 点击“启动 WebAPI”
3. 浏览器可打开：
   - `http://127.0.0.1:8000/docs`（Swagger 文档）

### 4.2 接口总览

- `GET /api/info`
- `POST /api/connect`
- `POST /api/disconnect`
- `GET /api/status`
- `POST /api/movej`

### 4.3 请求参数与返回示例

#### 4.3.1 `GET /api/info`

请求：

```bash
curl http://127.0.0.1:8000/api/info
```

成功返回示例：

```json
{
  "status": "online",
  "robot_connected": true,
  "robot_ip": "192.168.5.103"
}
```

#### 4.3.2 `POST /api/connect`

请求：

```bash
curl -X POST http://127.0.0.1:8000/api/connect \
  -H "Content-Type: application/json" \
  -d "{\"ip\":\"192.168.5.103\",\"port\":8899}"
```

成功返回：

```json
{
  "status": "success",
  "message": "已成功连接机械臂"
}
```

失败返回（示例）：

```json
{
  "detail": "连接失败: 登录失败，错误码: -1"
}
```

#### 4.3.3 `POST /api/disconnect`

请求：

```bash
curl -X POST http://127.0.0.1:8000/api/disconnect
```

返回：

```json
{
  "status": "success",
  "message": "已断开连接"
}
```

#### 4.3.4 `GET /api/status`

请求：

```bash
curl http://127.0.0.1:8000/api/status
```

成功返回示例：

```json
{
  "connected": true,
  "joints": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
  "pose": {
    "position": {"x": 0.12, "y": 0.02, "z": 0.35},
    "orientation": {"w": 1.0, "x": 0.0, "y": 0.0, "z": 0.0}
  }
}
```

#### 4.3.5 `POST /api/movej`

请求：

```bash
curl -X POST http://127.0.0.1:8000/api/movej \
  -H "Content-Type: application/json" \
  -d "{\"joints\":[0.1,-0.2,0.3,0.0,0.1,-0.1]}"
```

成功返回：

```json
{
  "status": "success",
  "message": "MoveJ 运动完成"
}
```

失败返回示例（限位/不可达）：

```json
{
  "detail": "J2 超出软限位，当前 190.00°，允许范围 [-175.0°, 175.0°]。"
}
```

或：

```json
{
  "detail": "SDK 返回错误码: -5（目标可能不可达或被控制器拒绝）"
}
```

## 5. ROS2 服务（桥接节点）与执行命令

本项目在 ROS2 侧提供的是“桥接节点服务进程”（非 ROS2 `srv` 接口），用于：

- 从 WebAPI 拉取状态并发布 `/joint_states`
- 订阅 `/aubo/joint_cmds` 并转发到 WebAPI `/api/movej`

### 5.1 启动 ROS2 桥接节点

将 `aubo_ros2_http_bridge.py` 拷贝到 Ubuntu 后执行：

```bash
source /opt/ros/humble/setup.bash
python3 aubo_ros2_http_bridge.py --host_ip 192.168.5.11 --host_port 8000
```

参数说明：

- `--host_ip`：Windows 上位机 IP（运行 GUI + WebAPI 的电脑）
- `--host_port`：WebAPI 端口，默认 `8000`

### 5.2 ROS2 侧常用命令

查看话题：

```bash
ros2 topic list
```

查看关节状态：

```bash
ros2 topic echo /joint_states
```

发送关节目标（示例）：

```bash
ros2 topic pub --once /aubo/joint_cmds std_msgs/msg/Float64MultiArray \
"{data: [0.1, -0.2, 0.3, 0.0, 0.1, -0.1]}"
```

## 6. 推荐启动顺序（非常重要）

1. 启动 Windows GUI：`python main.py`
2. 连接机械臂成功
3. 启动 WebAPI（GUI 第二页）
4. 在 Ubuntu 启动 ROS2 桥接节点
5. 在 ROS2 发送 `/aubo/joint_cmds` 或用 GUI 操作

若顺序打乱，常见问题是：

- ROS2 报“无法连接 WebAPI”
- WebAPI 报“机械臂未连接”
- MoveJ 被拒绝（超限位/不可达/单步过大）

## 7. 打包 EXE

在 Windows 项目目录执行：

```powershell
.\build_exe.ps1
```

产物路径：

- `dist\aubo_host_app.exe`

如果你只想手动打包，也可直接执行 `build_exe.ps1` 中的 `pyinstaller` 命令。
