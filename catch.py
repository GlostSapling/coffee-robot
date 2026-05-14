"""
夹爪控制脚本
用法: python catch.py <percent>
参数为夹爪开合百分比 (0-100)

示例:
  python catch.py 100  # 完全张开
  python catch.py 0    # 完全闭合
  python catch.py 50   # 半开
"""

import sys
import os
import requests as http_requests

# 添加配置路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "aubo", "aubo", "aubo_host_workspace"))
from coffee_config import GRIPPER_URL


def main():
    # 检查参数
    if len(sys.argv) != 2:
        print("用法: python catch.py <percent>")
        print("参数为夹爪开合百分比 (0-100)")
        print("\n示例:")
        print("  python catch.py 100  # 完全张开")
        print("  python catch.py 0    # 完全闭合")
        print("  python catch.py 50   # 半开")
        sys.exit(1)

    # 解析百分比
    try:
        percent = int(sys.argv[1])
    except ValueError:
        print("[错误] 百分比参数必须是整数")
        sys.exit(1)

    # 校验范围
    if percent < 0 or percent > 100:
        print("[错误] 百分比必须在 0-100 之间")
        sys.exit(1)

    # 发送控制指令
    print(f"[夹爪] 设置开合度: {percent}%")
    try:
        response = http_requests.get(f"{GRIPPER_URL}/set?percent={percent}", timeout=5)
        if response.status_code == 200:
            print("[夹爪] 控制成功")
        else:
            print(f"[夹爪] 控制失败: HTTP {response.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"[夹爪] 控制失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
