<<<<<<< HEAD
# 咖啡机器人 - Aubo-i10 Nespresso 自动咖啡制作系统

基于遨博 Aubo-i10 机械臂的自动咖啡制作 Demo。机械臂完成从拿杯子、放胶囊、到出杯的全流程自动化操作，支持后续接入 OpenClaw 语音控制。

## 工作流程

```
拿杯子 → 放到咖啡机下 → 拿胶囊 → 打开咖啡机盖子 → 放入胶囊 → 盖上盖子 → 按启动键 → 等待萃取 → 取杯 → 送到指定位置
```

共 10 个步骤，每步可独立调用，也可一键串联执行。

## 项目结构

```
coffee-robot/
├── config/
│   └── coffee_task.yaml       # 所有参数配置（点位、速度、夹爪、咖啡机）
├── robot/
│   ├── base.py                # 抽象机器人接口
│   ├── webapi_backend.py      # Windows WebAPI 后端（HTTP 远程控制）
│   └── local_backend.py       # Ubuntu libpyauboi5 后端（本地 SDK）
├── gripper/
│   ├── base.py                # 抽象夹爪接口
│   └── serial_gripper.py      # 串口夹爪实现（可自定义协议）
├── tasks/
│   └── coffee_task.py         # 咖啡制作工作流（10 步 + 命令分发）
├── coffee_demo.py             # 主入口
├── requirements.txt
└── CLAUDE.md
```

## 环境准备

### Python 依赖

```bash
pip install -r requirements.txt
```

依赖列表：`pyyaml`、`requests`、`numpy`、`pyserial`

### 机械臂后端（二选一）

**Windows（通过 WebAPI 远程控制）：**

1. 先启动上位机：`python main.py`（在 `aubo/aubo_host_workspace/` 目录下）
2. 在上位机 GUI 中连接机械臂，启动 WebAPI 服务（默认端口 8000）
3. 确保 `config/coffee_task.yaml` 中 `robot.backend: webapi`，IP 和端口与上位机一致

**Ubuntu（本地 SDK 直连）：**

1. 确保 `libpyauboi5.so` 已安装在 `~/aubo_quick_start/python_linux_lib/`
2. 确保 `config/coffee_task.yaml` 中 `robot.backend: local`，SDK 路径正确
3. 机械臂 IP 和端口在 `robot.local` 段配置

### 夹爪

默认使用串口控制的夹爪。如暂无夹爪，将配置中 `gripper.type` 改为 `none` 即可跳过夹爪操作（仿真模式）。

串口夹爪的协议字节在 `config/coffee_task.yaml` 的 `gripper.serial` 段配置，需根据实际夹爪型号修改 `open_cmd` 和 `close_cmd`。

## 使用方法

### 仿真模式（不需要连接机器人）

```bash
python3 coffee_demo.py --dry-run
```

打印完整工作流计划和模拟执行日志，用于验证配置和流程。

### 完整执行

```bash
python3 coffee_demo.py
```

连接机器人，按顺序执行全部 10 个步骤，完成后自动回到原点。

### 执行单个步骤

```bash
python3 coffee_demo.py --step pick_cup
python3 coffee_demo.py --step insert_capsule
python3 coffee_demo.py --step deliver_cup
```

可用的步骤名称：

| 步骤 | 名称 | 说明 |
|------|------|------|
| 1 | `pick_cup` | 拿杯子 |
| 2 | `place_cup_under_machine` | 把杯子放到咖啡机下 |
| 3 | `pick_capsule` | 拿胶囊 |
| 4 | `open_machine_lid` | 打开咖啡机盖子 |
| 5 | `insert_capsule` | 把胶囊放进去 |
| 6 | `close_machine_lid` | 盖上盖子 |
| 7 | `press_start_button` | 按启动键 |
| 8 | `wait_for_brew` | 等待萃取 |
| 9 | `pick_cup_from_machine` | 取杯 |
| 10 | `deliver_cup` | 送到指定位置 |

### 交互模式（语音/VLA 测试入口）

```bash
python3 coffee_demo.py --interactive
```

进入命令行交互界面，输入命令即可执行对应操作：

```
> make_coffee       # 执行完整流程
> 做咖啡            # 中文命令同样支持
> pick_cup          # 单步执行
> home              # 回原点
> quit              # 退出
```

### 指定配置文件

```bash
python3 coffee_demo.py --config /path/to/my_config.yaml
```

## 配置说明

所有参数集中在 `config/coffee_task.yaml` 中，**代码中无硬编码值**。

### 点位配置

所有点位以 6 轴关节角（弧度）表示。每个点位可配置：

```yaml
waypoints:
  cup_pickup:
    joints: [0.3, -0.5, 0.8, 0.0, 0.5, 0.0]  # 目标关节角
    approach_offset: [0.0, 0.0, 0.1]            # 接近偏移（先移到上方）
    depart_offset: [0.0, 0.0, 0.1]              # 离开偏移（夹住后抬升）
```

> **重要：** 当前配置中的点位是占位值，必须用示教器实际测量后替换。

### 速度配置

```yaml
robot:
  speed:
    max_velocity: [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]       # 各轴最大速度 (rad/s)
    max_acceleration: [2.0, 2.0, 2.0, 2.0, 2.0, 2.0]    # 各轴最大加速度 (rad/s^2)
```

### 夹爪配置

```yaml
gripper:
  type: serial           # "serial" 或 "none"
  serial:
    port: "/dev/ttyUSB0" # 串口设备
    baudrate: 115200
    open_cmd: [0x01, 0x01, 0x00]   # 松开指令字节
    close_cmd: [0x01, 0x01, 0xFF]  # 夹紧指令字节
    settle_time: 0.5     # 夹爪动作后等待时间（秒）
```

### 咖啡机配置

```yaml
coffee_machine:
  type: nespresso
  brew_time: 25          # 萃取等待时间（秒）
```

## 后续扩展

### 接入 OpenClaw 语音控制

`tasks/coffee_task.py` 中的 `CoffeeTask.run_by_command()` 方法已预留语音/VLA 命令接口：

```python
task = CoffeeTask(robot, gripper, config)
task.run_by_command("做咖啡")        # 完整流程
task.run_by_command("pick_cup")      # 单步
```

只需将 OpenClaw 语音识别结果映射到对应命令字符串即可。

### 自定义夹爪协议

编辑 `gripper/serial_gripper.py` 中的 `_send_command()` 方法，或在 YAML 中修改指令字节适配你的夹爪硬件。

### 切换机械臂后端

在 `config/coffee_task.yaml` 中修改 `robot.backend`：

- `webapi` — 通过 Windows 上位机的 HTTP API 控制（适合 Windows 环境）
- `local` — 通过 libpyauboi5 本地 SDK 直连（适合 Ubuntu 环境）
