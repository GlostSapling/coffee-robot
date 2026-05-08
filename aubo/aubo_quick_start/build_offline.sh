#!/bin/bash
set -e

# 获取脚本所在绝对路径（当前解压目录）
WS_DIR=$(pwd)
echo "=========================================================="
echo "  [离线版] 遨博 ROS2 Humble 驱动环境编译脚本"
echo "  当前工作空间路径: $WS_DIR"
echo "=========================================================="

# 1. 安装基础工具和依赖
echo ">>> [1/4] 更新并安装必要系统工具包..."
sudo apt-get update
sudo apt-get install -y python3-pip python3-colcon-common-extensions python3-rosdep python3-tk

# 2. 安装 Python 依赖
echo ">>> [2/4] 安装 Python 依赖库 (numpy, pyaubo_sdk)..."
pip3 install numpy pyaubo_sdk

# 3. 使用 rosdep 解决本地包的依赖
echo ">>> [3/4] 检查并安装 ROS2 系统依赖..."
if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then
    sudo rosdep init || echo "rosdep 已初始化"
fi
rosdep update || echo "rosdep update 网络可能超时，忽略"

# 载入 ROS2 环境
source /opt/ros/humble/setup.bash
echo "正在解决 ROS2 包依赖（跳过 docker 和高级规划包）..."
rosdep install --from-paths src --ignore-src -r -y --rosdistro humble --skip-keys="docker.io ros-humble-warehouse-ros-mongo warehouse_ros_mongo"

# 4. 编译核心驱动代码
echo ">>> [4/4] 编译核心驱动代码..."
colcon build --packages-select aubo_msgs aubo_dashboard_msgs aubo_hardware aubo_description aubo_ros2_driver

echo "=========================================================="
echo "  编译全部完成！ 🎉"
echo "  "
echo "  启动控制面板请执行:"
echo "  python3 aubo_gui.py"
echo "  "
echo "  (在面板中，[工作空间 setup.bash] 请填写为: $WS_DIR/install/setup.bash)"
echo "=========================================================="
