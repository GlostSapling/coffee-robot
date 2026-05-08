#!/bin/bash
# 遇到错误即停止执行
set -e

echo "=========================================================="
echo "    开始自动化配置 Aubo ROS2 Humble 工作环境和依赖    "
echo "=========================================================="

# 1. 设置工作空间路径
WS_DIR=~/aubo_ros2_ws
echo ">>> [1/6] 准备工作空间路径: $WS_DIR"
mkdir -p $WS_DIR/src

# 2. 安装系统依赖和构建工具
echo ">>> [2/6] 更新 apt 并安装基础构建工具 (git, pip, colcon, rosdep)..."
sudo apt-get update
sudo apt-get install -y git python3-pip python3-colcon-common-extensions python3-rosdep python3-tk

# 3. 安装 Python 依赖 (驱动指定的库)
echo ">>> [3/6] 安装 Python 依赖 (numpy, pyaubo_sdk)..."
pip3 install numpy pyaubo_sdk

# 4. 初始化和更新 rosdep
echo ">>> [4/6] 初始化和更新 rosdep..."
if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then
    sudo rosdep init || echo "rosdep 已初始化，跳过..."
fi
rosdep update || echo "rosdep update 可能存在部分网络超时，继续执行..."

# 5. 克隆 Aubo ROS2 驱动代码
echo ">>> [5/6] 下载/更新 Aubo ROS2 驱动代码..."
cd $WS_DIR/src
if [ ! -d "aubo_ros2_driver" ]; then
    git clone https://github.com/AuboRobot/aubo_ros2_driver.git
else
    echo "代码库已存在，正在拉取最新代码..."
    cd aubo_ros2_driver
    git pull
    cd ..
fi

# 6. 安装 ROS 依赖并编译
echo ">>> [6/6] 解析依赖并编译工作空间..."
cd $WS_DIR
# 加载底层 ROS2 Humble 环境
source /opt/ros/humble/setup.bash

# 自动安装该包所需的其他 ROS2 依赖库
echo "正在使用 rosdep 安装所需的其他 ROS 包（跳过 docker 和 warehouse-ros-mongo 这种非必需的大型依赖）..."
rosdep install --from-paths src --ignore-src -r -y --rosdistro humble --skip-keys="docker.io ros-humble-warehouse-ros-mongo warehouse_ros_mongo"

# 执行编译
echo "开始 colcon build 编译（仅编译基础驱动和消息包，彻底跳过 gazebo 和 moveit 等复杂依赖）..."
colcon build --packages-select aubo_msgs aubo_dashboard_msgs aubo_hardware aubo_description aubo_ros2_driver

echo "=========================================================="
echo "  配置全部完成！ 🎉"
echo "  你的 Aubo 工作空间已在 $WS_DIR 就绪。"
echo "  "
echo "  你现在可以启动之前打包好的 aubo_gui 控制面板，"
echo "  并确保界面的 [工作空间 setup.bash] 填写为："
echo "  ~/aubo_ros2_ws/install/setup.bash"
echo "=========================================================="
