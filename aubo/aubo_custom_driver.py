#!/usr/bin/env python3
import sys
import os
import time
import math
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray

# ==========================================================
# 1. 动态加载 libpyauboi5.so 的路径
# 请将这里的路径替换为你 Ubuntu 机器上实际存放 python_linux_lib 的绝对路径
# ==========================================================
SDK_PATH = os.path.expanduser("~/aubo_quick_start/python_linux_lib")
sys.path.append(SDK_PATH)

# ==========================================================
# 2. 尝试导入 SDK (可能存在 Python 版本兼容性问题)
# ==========================================================
try:
    import libpyauboi5 as aubo
    print("[INFO] 成功导入 libpyauboi5 SDK!")
except ImportError as e:
    print(f"[ERROR] 无法导入 libpyauboi5 SDK。错误信息: {e}")
    print("[ERROR] 这通常是因为当前 Ubuntu/ROS2 的 Python 版本 (如 3.10) 与该 .so 编译时的 Python 版本不匹配导致。")
    # 为了演示，如果不成功也先不要让程序崩溃
    aubo = None


class AuboCustomDriverNode(Node):
    def __init__(self):
        super().__init__('aubo_custom_driver')
        
        self.declare_parameter('robot_ip', '192.168.5.103')
        self.declare_parameter('robot_port', 8899)
        
        self.robot_ip = self.get_parameter('robot_ip').value
        self.robot_port = self.get_parameter('robot_port').value
        
        self.robot = None
        self.connected = False
        
        # 发布关节状态 (给 RViz 等显示用)
        self.joint_state_pub = self.create_publisher(JointState, '/joint_states', 10)
        
        # 订阅目标关节角度指令 (接收外部控制)
        # 这里用 Float64MultiArray 简化演示，实际可以使用 trajectory_msgs/JointTrajectory
        self.joint_cmd_sub = self.create_subscription(
            Float64MultiArray, 
            '/aubo/joint_cmds', 
            self.joint_cmd_callback, 
            10
        )
        
        # 连接机器人
        self.connect_to_robot()
        
        # 创建定时器，以 10Hz 频率读取并发布当前机器人状态
        self.timer = self.create_timer(0.1, self.publish_joint_states)

    def connect_to_robot(self):
        if not aubo:
            self.get_logger().error("SDK 未加载，无法连接机器人。")
            return
            
        try:
            # === 以下为 Aubo 老版 Python SDK 的典型初始化流程 (不同版本API可能有细微差别) ===
            aubo.initialize()
            self.robot = aubo.robot()
            
            # 设置连接超时和端口
            self.get_logger().info(f"正在连接到机械臂 {self.robot_ip}:{self.robot_port} ...")
            
            # 这里调用 SDK 的 connect 方法
            ret = self.robot.connect(self.robot_ip, self.robot_port)
            if ret == 0:  # 假设 0 是成功
                self.connected = True
                self.get_logger().info("✅ 成功连接到遨博机械臂！")
            else:
                self.get_logger().error(f"❌ 连接失败，错误码: {ret}")
                
        except Exception as e:
            self.get_logger().error(f"连接过程中发生异常: {e}")

    def publish_joint_states(self):
        """定时读取真实机械臂的关节角度并发布到 ROS2 网络"""
        if not self.connected or not self.robot:
            return
            
        try:
            # 调用 SDK 获取当前关节角 (API 名称需根据实际 SDK 手册调整)
            # 例如: current_joints = self.robot.get_joint_status()
            current_joints = self.robot.get_current_waypoint() 
            
            msg = JointState()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.name = ['shoulder_joint', 'upperArm_joint', 'foreArm_joint', 'wrist1_joint', 'wrist2_joint', 'wrist3_joint']
            # 将获取到的度数或弧度填入
            msg.position = current_joints.joint # 伪代码，取决于实际数据结构
            
            self.joint_state_pub.publish(msg)
            
        except Exception as e:
            pass

    def joint_cmd_callback(self, msg):
        """当接收到 ROS2 话题发来的目标角度时，调用 SDK 让真实机械臂运动"""
        if not self.connected or not self.robot:
            self.get_logger().warn("收到移动指令，但机械臂未连接！")
            return
            
        target_joints = msg.data
        if len(target_joints) != 6:
            self.get_logger().error("目标关节数不等于 6！")
            return
            
        self.get_logger().info(f"发送 MoveJ 指令: {target_joints}")
        try:
            # 调用老版 SDK 的 movej 方法发送运动指令
            self.robot.move_joint(target_joints)
        except Exception as e:
            self.get_logger().error(f"执行 MoveJ 失败: {e}")

def main(args=None):
    rclpy.init(args=args)
    node = AuboCustomDriverNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("节点被手动终止")
    finally:
        # 断开连接
        if node.robot and node.connected:
            node.robot.disconnect()
            aubo.uninitialize()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
