import tkinter as tk
from tkinter import messagebox
import subprocess
import threading
import sys
import os

class AuboROS2GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("遨博 ROS2 驱动控制面板")
        self.root.geometry("650x550")
        
        self.driver_process = None
        
        # --- Connection Frame ---
        conn_frame = tk.LabelFrame(root, text="1. 连接配置 (启动驱动)", padx=10, pady=10)
        conn_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(conn_frame, text="机械臂 IP:").grid(row=0, column=0, padx=5, pady=5)
        self.ip_entry = tk.Entry(conn_frame)
        self.ip_entry.insert(0, "192.168.5.103")
        self.ip_entry.grid(row=0, column=1, padx=5, pady=5)
        
        self.launch_btn = tk.Button(conn_frame, text="启动驱动", command=self.launch_driver, bg="#d9edf7")
        self.launch_btn.grid(row=0, column=2, padx=5, pady=5)

        self.stop_btn = tk.Button(conn_frame, text="停止驱动", command=self.stop_driver, state=tk.DISABLED, bg="#f2dede")
        self.stop_btn.grid(row=0, column=3, padx=5, pady=5)
        
        tk.Label(conn_frame, text="工作空间 setup.bash:").grid(row=1, column=0, padx=5, pady=5)
        self.ws_entry = tk.Entry(conn_frame, width=35)
        self.ws_entry.insert(0, "~/aubo_ros2_ws/install/setup.bash")
        self.ws_entry.grid(row=1, column=1, columnspan=2, sticky="w", padx=5, pady=5)
        tk.Label(conn_frame, text="(Linux 下需指定工作空间路径)").grid(row=1, column=3, sticky="w", padx=5)

        # --- Status Frame ---
        status_frame = tk.LabelFrame(root, text="2. 机器人状态 (JSON-RPC)", padx=10, pady=10)
        status_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Button(status_frame, text="获取 TCP 位姿", command=self.get_tcp_pose).grid(row=0, column=0, padx=10, pady=5)
        tk.Button(status_frame, text="获取关节位置", command=self.get_joint_positions).grid(row=0, column=1, padx=10, pady=5)
        
        # --- Control Frame ---
        ctrl_frame = tk.LabelFrame(root, text="3. 基础控制", padx=10, pady=10)
        ctrl_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(ctrl_frame, text="目标关节角 (rad):").grid(row=0, column=0, padx=5, pady=5)
        self.joint_entry = tk.Entry(ctrl_frame, width=40)
        self.joint_entry.insert(0, "[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]")
        self.joint_entry.grid(row=0, column=1, padx=5, pady=5)
        
        tk.Button(ctrl_frame, text="关节运动 (MoveJ)", command=self.move_joints, bg="#dff0d8").grid(row=0, column=2, padx=5, pady=5)
        
        # --- Log Frame ---
        log_frame = tk.LabelFrame(root, text="终端日志", padx=10, pady=10)
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.log_text = tk.Text(log_frame, height=10)
        self.log_text.pack(fill="both", expand=True, side="left")
        
        scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=scrollbar.set)

    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    def _build_cmd(self, base_cmd):
        """将 ROS2 命令与工作空间的 source 命令拼接（Linux专用）"""
        ws_path = self.ws_entry.get().strip()
        if ws_path and sys.platform != "win32":
            ws_path = os.path.expanduser(ws_path)
            # 在 Linux 下，先 source 环境再执行 base_cmd
            return f"source {ws_path} && {base_cmd}"
        return base_cmd

    def launch_driver(self):
        ip = self.ip_entry.get().strip()
        if not ip:
            messagebox.showerror("错误", "请输入机械臂 IP 地址")
            return
        
        base_cmd = f"ros2 launch aubo_ros2_driver aubo_client.launch.py robot_ip:={ip} log_level:=info"
        cmd_str = self._build_cmd(base_cmd)
        
        self.log(f"[信息] 运行命令: {cmd_str}")
        try:
            kwargs = {
                "shell": True,
                "stdout": subprocess.PIPE,
                "stderr": subprocess.STDOUT,
                "text": True
            }
            if sys.platform != "win32":
                kwargs["executable"] = "/bin/bash"

            self.driver_process = subprocess.Popen(cmd_str, **kwargs)
            self.launch_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            
            threading.Thread(target=self.read_output, daemon=True).start()
        except Exception as e:
            self.log(f"[错误] 启动驱动失败: {e}")

    def read_output(self):
        while self.driver_process and self.driver_process.poll() is None:
            line = self.driver_process.stdout.readline()
            if line:
                self.root.after(0, self.log, line.strip())
                
    def stop_driver(self):
        if self.driver_process:
            self.driver_process.terminate()
            self.driver_process = None
            self.log("[信息] 驱动已停止。")
            self.launch_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)

    def call_service(self, cls, func, params="[]"):
        if sys.platform == "win32":
            yaml_str = f"{{cls: '{cls}', func: '{func}', params: '{params}'}}"
            base_cmd = f'ros2 service call /jsonrpc_service aubo_msgs/srv/JsonRpc "{yaml_str}"'
        else:
            yaml_str = f"{{cls: '{cls}', func: '{func}', params: '{params}'}}"
            base_cmd = f"ros2 service call /jsonrpc_service aubo_msgs/srv/JsonRpc \"{yaml_str}\""

        cmd_str = self._build_cmd(base_cmd)
        self.log(f"[信息] 调用 JSON-RPC: {cls}.{func}({params})")
        try:
            kwargs = {
                "shell": True,
                "capture_output": True,
                "text": True,
                "timeout": 10
            }
            if sys.platform != "win32":
                kwargs["executable"] = "/bin/bash"

            result = subprocess.run(cmd_str, **kwargs)
            if result.stdout:
                self.log(f"[响应]\n{result.stdout.strip()}")
            if result.stderr:
                self.log(f"[错误]\n{result.stderr.strip()}")
        except subprocess.TimeoutExpired:
            self.log("[错误] 服务调用超时。")
        except Exception as e:
            self.log(f"[错误] 服务调用失败: {e}")

    def get_tcp_pose(self):
        threading.Thread(target=self.call_service, args=("RobotState", "getTcpPose"), daemon=True).start()

    def get_joint_positions(self):
        threading.Thread(target=self.call_service, args=("RobotState", "getJointPositions"), daemon=True).start()

    def move_joints(self):
        joints_str = self.joint_entry.get().strip()
        if not joints_str.startswith("[") or not joints_str.endswith("]"):
            messagebox.showerror("错误", "关节角必须是 JSON 数组格式，例如 [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]")
            return
            
        params = f"[{joints_str}]"
        threading.Thread(target=self.call_service, args=("RobotControl", "movej", params), daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = AuboROS2GUI(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.stop_driver(), root.destroy()))
    root.mainloop()
