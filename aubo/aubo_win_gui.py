import sys
import tkinter as tk
from tkinter import messagebox
import ctypes
import os
import threading
import time
import json

# --- ctypes Definitions for Aubo Windows SDK ---
class Pos(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double),
                ("y", ctypes.c_double),
                ("z", ctypes.c_double)]

class Ori(ctypes.Structure):
    _fields_ = [("w", ctypes.c_double),
                ("x", ctypes.c_double),
                ("y", ctypes.c_double),
                ("z", ctypes.c_double)]

class wayPoint_S(ctypes.Structure):
    _fields_ = [("cartPos", Pos),
                ("orientation", Ori),
                ("jointpos", ctypes.c_double * 6)]

class AuboWindowsSDK:
    def __init__(self, dll_path):
        os.environ["PATH"] += os.pathsep + os.path.dirname(dll_path)
        self.dll = ctypes.CDLL(dll_path)
        
        self.dll.rs_initialize.restype = ctypes.c_int
        self.dll.rs_uninitialize.restype = ctypes.c_int
        self.dll.rs_create_context.argtypes = [ctypes.POINTER(ctypes.c_uint16)]
        self.dll.rs_create_context.restype = ctypes.c_int
        self.dll.rs_destory_context.argtypes = [ctypes.c_uint16]
        self.dll.rs_destory_context.restype = ctypes.c_int
        self.dll.rs_login.argtypes = [ctypes.c_uint16, ctypes.c_char_p, ctypes.c_int]
        self.dll.rs_login.restype = ctypes.c_int
        self.dll.rs_logout.argtypes = [ctypes.c_uint16]
        self.dll.rs_logout.restype = ctypes.c_int
        
        self.dll.rs_get_current_waypoint.argtypes = [ctypes.c_uint16, ctypes.POINTER(wayPoint_S)]
        self.dll.rs_get_current_waypoint.restype = ctypes.c_int
        
        self.dll.rs_move_joint.argtypes = [ctypes.c_uint16, ctypes.POINTER(ctypes.c_double * 6), ctypes.c_bool]
        self.dll.rs_move_joint.restype = ctypes.c_int
        
        self.dll.rs_init_global_move_profile.argtypes = [ctypes.c_uint16]
        self.dll.rs_init_global_move_profile.restype = ctypes.c_int
        
        self.dll.rs_set_global_joint_maxvelc.argtypes = [ctypes.c_uint16, ctypes.POINTER(ctypes.c_double * 6)]
        self.dll.rs_set_global_joint_maxvelc.restype = ctypes.c_int
        
        self.dll.rs_set_global_joint_maxacc.argtypes = [ctypes.c_uint16, ctypes.POINTER(ctypes.c_double * 6)]
        self.dll.rs_set_global_joint_maxacc.restype = ctypes.c_int

        self.rshd = ctypes.c_uint16(0)
        self.connected = False
        
        self.dll.rs_initialize()

    def connect(self, ip, port=8899):
        if self.dll.rs_create_context(ctypes.byref(self.rshd)) != 0:
            return False, "无法创建上下文"
            
        ret = self.dll.rs_login(self.rshd.value, ip.encode('utf-8'), port)
        if ret != 0:
            self.dll.rs_destory_context(self.rshd.value)
            return False, f"登录失败，错误码: {ret}"
            
        self.connected = True
        
        # 初始化运动属性
        self.dll.rs_init_global_move_profile(self.rshd.value)
        
        # 设置安全速度和加速度 (限制最大速度防止意外)
        max_vel = (ctypes.c_double * 6)(*[30.0 * 3.1415926 / 180.0] * 6)
        max_acc = (ctypes.c_double * 6)(*[30.0 * 3.1415926 / 180.0 * 10.0] * 6)
        self.dll.rs_set_global_joint_maxvelc(self.rshd.value, max_vel)
        self.dll.rs_set_global_joint_maxacc(self.rshd.value, max_acc)
        
        return True, "连接成功"

    def disconnect(self):
        if self.connected:
            self.dll.rs_logout(self.rshd.value)
            self.dll.rs_destory_context(self.rshd.value)
            self.connected = False
            
    def get_waypoint(self):
        wp = wayPoint_S()
        if self.dll.rs_get_current_waypoint(self.rshd.value, ctypes.byref(wp)) == 0:
            return wp
        return None
        
    def movej(self, joints_rad):
        if len(joints_rad) != 6:
            return False
        j_arr = (ctypes.c_double * 6)(*joints_rad)
        # 阻塞模式执行
        ret = self.dll.rs_move_joint(self.rshd.value, j_arr, True)
        return ret == 0
        
    def __del__(self):
        self.disconnect()
        self.dll.rs_uninitialize()

# --- GUI 界面代码 ---
class AuboWinGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("遨博机器人 Windows 原生控制面板")
        self.root.geometry("680x600")
        
        # 获取当前运行目录（兼容 pyinstaller 打包后的临时目录）
        if getattr(sys, 'frozen', False):
            # 如果是被打包成了 exe
            base_path = sys._MEIPASS
        else:
            # 如果是直接运行 python 脚本
            base_path = os.path.dirname(os.path.abspath(__file__))
            
        # 加载 DLL
        dll_path = os.path.join(base_path, "serviceinterface2.dll")
        try:
            self.robot = AuboWindowsSDK(dll_path)
        except Exception as e:
            messagebox.showerror("SDK 加载失败", f"无法加载 DLL，请确保路径正确: {e}")
            sys.exit(1)
            
        self.status_loop_running = False

        # --- 连接配置区 ---
        conn_frame = tk.LabelFrame(root, text="1. TCP 连接 (端口 8899)", padx=10, pady=10)
        conn_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(conn_frame, text="机械臂 IP:").grid(row=0, column=0, padx=5, pady=5)
        self.ip_entry = tk.Entry(conn_frame)
        self.ip_entry.insert(0, "192.168.5.103")
        self.ip_entry.grid(row=0, column=1, padx=5, pady=5)
        
        self.btn_connect = tk.Button(conn_frame, text="连接实机", command=self.connect, bg="#d9edf7")
        self.btn_connect.grid(row=0, column=2, padx=5, pady=5)

        self.btn_disconnect = tk.Button(conn_frame, text="断开连接", command=self.disconnect, state=tk.DISABLED, bg="#f2dede")
        self.btn_disconnect.grid(row=0, column=3, padx=5, pady=5)
        
        # --- 状态显示区 ---
        status_frame = tk.LabelFrame(root, text="2. 实时状态监控", padx=10, pady=10)
        status_frame.pack(fill="x", padx=10, pady=5)
        
        self.lbl_pos = tk.Label(status_frame, text="末端位置 (XYZ): [等待连接...]", fg="blue")
        self.lbl_pos.pack(anchor="w", pady=2)
        
        self.lbl_ori = tk.Label(status_frame, text="末端姿态 (WXYZ): [等待连接...]", fg="blue")
        self.lbl_ori.pack(anchor="w", pady=2)
        
        self.lbl_joints = tk.Label(status_frame, text="六轴关节角 (Rad): [等待连接...]", fg="green")
        self.lbl_joints.pack(anchor="w", pady=2)

        # --- 运动控制区 ---
        ctrl_frame = tk.LabelFrame(root, text="3. MoveJ 关节运动控制", padx=10, pady=10)
        ctrl_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(ctrl_frame, text="目标关节角 (rad 数组):").pack(anchor="w")
        self.joint_entry = tk.Entry(ctrl_frame, width=60)
        self.joint_entry.insert(0, "[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]")
        self.joint_entry.pack(pady=5)
        
        self.btn_movej = tk.Button(ctrl_frame, text="执行 MoveJ 运动", command=self.movej, state=tk.DISABLED, bg="#dff0d8")
        self.btn_movej.pack(pady=5)
        
        # --- 日志区 ---
        log_frame = tk.LabelFrame(root, text="操作日志", padx=10, pady=10)
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.log_text = tk.Text(log_frame, height=8)
        self.log_text.pack(fill="both", expand=True, side="left")
        
        scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=scrollbar.set)
        
        self.log("[INFO] Windows 原生 SDK 桥接器就绪。请确保机械臂 8899 端口畅通。")

    def log(self, msg):
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)

    def connect(self):
        ip = self.ip_entry.get().strip()
        self.log(f"[INFO] 正在尝试连接 {ip}:8899 ...")
        
        success, msg = self.robot.connect(ip, 8899)
        if success:
            self.log("[SUCCESS] 机械臂连接成功！")
            self.btn_connect.config(state=tk.DISABLED)
            self.btn_disconnect.config(state=tk.NORMAL)
            self.btn_movej.config(state=tk.NORMAL)
            
            # 开启状态刷新线程
            self.status_loop_running = True
            threading.Thread(target=self.status_loop, daemon=True).start()
        else:
            self.log(f"[ERROR] {msg}")
            messagebox.showerror("连接失败", msg)

    def disconnect(self):
        self.status_loop_running = False
        self.robot.disconnect()
        self.log("[INFO] 机械臂连接已断开。")
        self.btn_connect.config(state=tk.NORMAL)
        self.btn_disconnect.config(state=tk.DISABLED)
        self.btn_movej.config(state=tk.DISABLED)
        
        self.lbl_pos.config(text="末端位置 (XYZ): [已断开]")
        self.lbl_ori.config(text="末端姿态 (WXYZ): [已断开]")
        self.lbl_joints.config(text="六轴关节角 (Rad): [已断开]")

    def status_loop(self):
        while self.status_loop_running:
            wp = self.robot.get_waypoint()
            if wp:
                # 在主线程更新 UI
                pos_str = f"[{wp.cartPos.x:.4f}, {wp.cartPos.y:.4f}, {wp.cartPos.z:.4f}]"
                ori_str = f"[{wp.orientation.w:.4f}, {wp.orientation.x:.4f}, {wp.orientation.y:.4f}, {wp.orientation.z:.4f}]"
                j_list = [wp.jointpos[i] for i in range(6)]
                j_str = f"[{j_list[0]:.4f}, {j_list[1]:.4f}, {j_list[2]:.4f}, {j_list[3]:.4f}, {j_list[4]:.4f}, {j_list[5]:.4f}]"
                
                self.root.after(0, lambda p=pos_str, o=ori_str, j=j_str: self.update_labels(p, o, j))
            time.sleep(0.5)

    def update_labels(self, pos, ori, joints):
        self.lbl_pos.config(text=f"末端位置 (XYZ): {pos}")
        self.lbl_ori.config(text=f"末端姿态 (WXYZ): {ori}")
        self.lbl_joints.config(text=f"六轴关节角 (Rad): {joints}")

    def movej(self):
        j_str = self.joint_entry.get().strip()
        try:
            target_joints = json.loads(j_str)
            if not isinstance(target_joints, list) or len(target_joints) != 6:
                raise ValueError
        except Exception:
            messagebox.showerror("格式错误", "请输入有效的包含 6 个浮点数的 JSON 数组！")
            return
            
        self.log(f"[INFO] 正在执行 MoveJ: {target_joints} ...")
        self.btn_movej.config(state=tk.DISABLED)
        
        def run_move():
            success = self.robot.movej(target_joints)
            if success:
                self.root.after(0, self.log, "[SUCCESS] MoveJ 运动完成！")
            else:
                self.root.after(0, self.log, "[ERROR] MoveJ 运动失败！")
            self.root.after(0, lambda: self.btn_movej.config(state=tk.NORMAL))
            
        threading.Thread(target=run_move, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = AuboWinGUI(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.disconnect(), root.destroy()))
    root.mainloop()
