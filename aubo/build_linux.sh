#!/bin/bash
echo "开始安装依赖项..."
# 如果你使用的是 Ubuntu/Debian，需要安装 python3-tk 和 pip
sudo apt-get update
sudo apt-get install -y python3-tk python3-pip

echo "安装 PyInstaller..."
pip3 install pyinstaller

echo "开始打包 Linux 可执行文件..."
pyinstaller --onefile --windowed aubo_gui.py

echo "=========================================="
echo "打包完成！"
echo "你的可执行文件位于: dist/aubo_gui"
echo "可以直接通过运行 ./dist/aubo_gui 来启动程序。"
echo "=========================================="
