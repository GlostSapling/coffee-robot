#!/usr/bin/env python3
"""
ROS2 <-> Windows WebAPI 桥接节点 (在 Ubuntu 的 ROS2 环境下运行)

用法: 
1. 在 Windows 上启动 `aubo_host_app.exe` 并连接机械臂，启动 WebAPI。
2. 记下 Windows 电脑的 IP 地址 (例如: 192.168.1.100)。
3. 在装有 ROS2 的 Ubuntu 终端运行:
   python3 aubo_ros2_http_bridge.py --host_ip 192.168.1.100 --host_port 8001
"""

import sys
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray
import requests
import argparse

class AuboHttpBridgeNode(Node):
    def __init__(self, host_ip, host_port):
        super().__init__('aubo_http_bridge')
        
        self.api_url = f"http://{host_ip}:{host_port}/ros2"
        
        # 测试与 Windows 主机的连接
        try:
            resp = requests.get(f"{self.api_url}/info", timeout=2.0)
            if resp.status_code == 200 and resp.json().get("robot_connected"):
                self.get_logger().info(f"✅ 成功连接到 Windows 上位机 [{host_ip}:{host_port}]，且机械臂在线！")
            else:
                self.get_logger().warn(f"⚠️ 连上了 Windows 上位机，但机械臂当前未连接！")
        except Exception as e:
            self.get_logger().error(f"❌ 无法连接到 Windows 上位机 WebAPI: {e}")
            sys.exit(1)

        # 发布 /joint_states 给 RViz / MoveIt 监控
        self.joint_pub = self.create_publisher(JointState, '/joint_states', 10)
        # 每秒 10 次轮询当前位姿
        self.timer = self.create_timer(0.1, self.timer_callback)

        # 订阅外部 /aubo/joint_cmds 话题，将数据转发给 Windows API
        self.cmd_sub = self.create_subscription(
            Float64MultiArray, 
            '/aubo/joint_cmds', 
            self.cmd_callback, 
            10
        )

        self.joint_names = [
            'shoulder_joint', 'upperArm_joint', 'foreArm_joint', 
            'wrist1_joint', 'wrist2_joint', 'wrist3_joint'
        ]

    def timer_callback(self):
        try:
            resp = requests.get(f"{self.api_url}/status", timeout=0.5)
            if resp.status_code == 200:
                data = resp.json()
                msg = JointState()
                msg.header.stamp = self.get_clock().now().to_msg()
                msg.name = self.joint_names
                msg.position = data.get("joints", [])
                
                self.joint_pub.publish(msg)
        except Exception as e:
            # 防止网络波动刷屏，偶尔超时忽略即可
            pass

    def cmd_callback(self, msg):
        target_joints = msg.data
        if len(target_joints) != 6:
            self.get_logger().error("收到的目标角度不是 6 轴数据！")
            return
            
        self.get_logger().info(f"-> 收到 ROS2 MoveJ 指令，转发至 Windows: {target_joints}")
        try:
            payload = {"joints": list(target_joints)}
            resp = requests.post(f"{self.api_url}/movej", json=payload, timeout=5.0)
            if resp.status_code == 200:
                self.get_logger().info("<- Windows 执行 MoveJ 成功！")
            else:
                self.get_logger().error(f"<- Windows 拒绝或执行失败: {resp.text}")
        except Exception as e:
            self.get_logger().error(f"请求 WebAPI 异常: {e}")


def main(args=None):
    parser = argparse.ArgumentParser(description="Aubo ROS2 HTTP Bridge")
    parser.add_argument('--host_ip', type=str, required=True, help='Windows 上位机电脑的 IP 地址')
    parser.add_argument('--host_port', type=int, default=8001, help='ROS2API 服务端口 (默认 8001)')
    parsed_args, ros_args = parser.parse_known_args()

    rclpy.init(args=ros_args)
    node = AuboHttpBridgeNode(parsed_args.host_ip, parsed_args.host_port)
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("桥接节点已手动关闭")
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
