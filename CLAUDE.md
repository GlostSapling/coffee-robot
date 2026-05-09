# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Aubo (遨博) robot Windows host application ("上位机") for controlling an Aubo i10H robotic arm via its legacy controller (port 8899). The system provides:
- A Tkinter desktop GUI for direct robot control, camera capture, and media management
- A FastAPI-based WebAPI (default port 8000) for HTTP/REST control
- A separate ROS2API (default port 8001) for ROS2 bridge integration
- A ROS2 HTTP bridge node that runs on Ubuntu to relay `/joint_states` and `/aubo/joint_cmds`

## Important: SDK is Windows-Only

The Aubo SDK (`serviceinterface2.dll`) only supports Windows. **WebAPI is the primary control interface for all non-Windows platforms** (Linux, ROS2, remote clients). When developing Linux-side features, always use the WebAPI HTTP endpoints — do not attempt to call the SDK directly.

## Architecture

The core application lives in `aubo/aubo_host_workspace/`:

```
main.py              → Tkinter GUI entry point; initializes SDK, camera, media store; launches API servers
aubo_sdk.py          → ctypes wrapper around Aubo Windows DLL (serviceinterface2.dll); joint validation, soft limits, movej
core_state.py        → Global singleton state: robot object, camera service, media store, API running flags
api_server.py        → FastAPI app for WebAPI (/api/*) — includes inline HTML/JS web console with Three.js digital twin
ros2_api_server.py   → FastAPI app for ROS2API (/ros2/*) — separate from WebAPI to avoid coupling
camera_orbbec.py     → Orbbec depth camera (pyorbbecsdk) service + SQLite-backed MediaStore for photo/video capture
aubo_ros2_http_bridge.py → ROS2 node (runs on Ubuntu): polls WebAPI status → publishes /joint_states, subscribes /aubo/joint_cmds → forwards to WebAPI
```

**Key design decisions:**
- `core_state.py` is the shared state bus — GUI, WebAPI, and ROS2API all access the same robot/camera/media objects through it
- `aubo_sdk.py` uses ctypes to call the Aubo DLL directly (no Python bindings from vendor); all joint values are in radians internally
- Joint soft limits are defined in `AuboWindowsSDK.JOINT_LIMITS_DEG` (currently `[-175°, 175°]` per axis); `MAX_SINGLE_STEP_DEG = 90°` for single-step safety
- WebAPI and ROS2API are two separate FastAPI instances on different ports to keep ROS2 bridge calls isolated from web UI traffic
- The web console (served by WebAPI at `/`) embeds a full Three.js digital twin that loads segmented GLB models and drives them with joint angles

## Commands

### Run the host application (Windows)
```bash
cd aubo/aubo_host_workspace
pip install fastapi uvicorn pydantic requests pyorbbecsdk opencv-python numpy
python main.py
```

### Run the ROS2 bridge node (Ubuntu)
```bash
source /opt/ros/humble/setup.bash
pip3 install requests
python3 aubo_ros2_http_bridge.py --host_ip <WINDOWS_IP> --host_port 8001
```

### Build Windows EXE
```powershell
cd aubo/aubo_host_workspace
.\build_exe.ps1
# Output: dist\aubo_host_app.exe
```

### Build standalone GUI EXE (older, simpler version)
```bash
cd aubo
pip install pyinstaller pyorbbecsdk opencv-python numpy
pyinstaller aubo_gui.spec   # or aubo_win_gui.spec for Windows-specific
```

### Test robot connection via WebAPI
```bash
curl http://127.0.0.1:8000/api/info
curl -X POST http://127.0.0.1:8000/api/connect -H "Content-Type: application/json" -d '{"ip":"192.168.10.3","port":8899}'
curl http://127.0.0.1:8000/api/status
```

### Generate digital twin link models
```bash
cd aubo/aubo_host_workspace/tools
python convert_step_to_glb.py   # STEP → GLB conversion
python build_twin_links.py      # Split into per-joint link GLBs
```

## Startup Order (Important)

The system requires this sequence:
1. `python main.py` — start the host GUI
2. Connect the robot arm from the GUI
3. Start WebAPI and/or ROS2API from the GUI's second tab
4. On Ubuntu: run the ROS2 bridge node

Starting APIs before connecting the robot will cause "机械臂未连接" errors.

## Dependencies

**Windows host (Python 3.8+, recommended 3.10/3.11):**
```
fastapi uvicorn pydantic requests pyinstaller pyorbbecsdk opencv-python numpy
```

**Ubuntu ROS2 side:**
```
requests  (only dependency beyond ROS2 Humble)
```

**DLLs required at runtime** (in `aubo/aubo_host_workspace/lib/`):
- `serviceinterface2.dll` — Aubo robot controller interface
- `libgcc_s_seh-1.dll`, `libstdc++-6.dll`, `libwinpthread-1.dll` — MinGW runtime

## Data Storage

- `app_data/media/` — captured photos and videos
- `app_data/media.db` — SQLite database mapping media records (auto-migrates schema on startup)
