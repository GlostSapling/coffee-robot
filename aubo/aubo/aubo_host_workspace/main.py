import sys
import os
import math
import json
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import webbrowser
import uvicorn
import requests as http_requests

import core_state
from aubo_sdk import AuboWindowsSDK
import api_server
import ros2_api_server
from camera_orbbec import MediaStore, OrbbecCameraService, CameraFeatureError

# 咖啡流程共享配置
from coffee_config import GRIPPER_IP, STEPS, POS_HOME


class AuboHostApp:
    def __init__(self, root):
        self.root = root
        self.root.title("遨博机器人 Windows 综合上位机 (GUI + WebAPI + ROS2 Gateway)")
        self.root.geometry("860x760")

        self.target_points = {}
        self.slider_vars = []
        self.slider_value_labels = []
        self.status_loop_running = False
        self.media_row_widgets = []
        self.camera_devices = []
        self._pending_logs = []

        # --- 初始化 DLL 和 SDK ---
        if getattr(sys, "frozen", False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))

        dll_path = os.path.join(base_path, "lib", "serviceinterface2.dll")
        if not os.path.exists(dll_path):
            messagebox.showerror("文件缺失", f"找不到 DLL 文件: {dll_path}")
            sys.exit(1)

        try:
            self.robot = AuboWindowsSDK(dll_path)
            core_state.set_robot(self.robot)
        except Exception as e:
            messagebox.showerror("初始化失败", f"SDK 加载异常: {e}")
            sys.exit(1)

        # --- 本地数据目录与相机模块 ---
        if getattr(sys, "frozen", False):
            runtime_dir = os.path.dirname(sys.executable)
        else:
            runtime_dir = os.path.dirname(os.path.abspath(__file__))
        self.app_data_dir = os.path.join(runtime_dir, "app_data")
        os.makedirs(self.app_data_dir, exist_ok=True)
        self.media_store = MediaStore(self.app_data_dir)
        core_state.set_media_store(self.media_store)
        try:
            self.camera_service = OrbbecCameraService()
            self.camera_enabled = True
        except CameraFeatureError as e:
            self.camera_service = None
            self.camera_enabled = False
            self.camera_disabled_reason = str(e)
        core_state.set_camera_service(self.camera_service)

        # --- UI 构建 ---
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=True, fill="both", padx=10, pady=10)

        self.tab_control_host = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_control_host, text="🏠 仪表盘与控制")
        self.tab_control = self._make_scrollable_tab(self.tab_control_host)
        self.build_control_tab()

        self.tab_api_host = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_api_host, text="🌐 WebAPI / ROS2API 服务")
        self.tab_api = self._make_scrollable_tab(self.tab_api_host)
        self.build_api_tab()

        # 底部日志区
        log_frame = tk.LabelFrame(root, text="系统运行日志", padx=5, pady=5)
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.log_text = tk.Text(log_frame, height=8)
        self.log_text.pack(fill="both", expand=True, side="left")
        scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=scrollbar.set)

        # 刷新日志控件创建前的缓存日志
        for msg in self._pending_logs:
            self.log_text.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.log_text.see(tk.END)
        self._pending_logs.clear()

        self._set_joint_controls_state(False)
        self.log("[系统] Aubo Windows 综合上位机启动完毕。")

    def log(self, msg):
        if not hasattr(self, "log_text"):
            self._pending_logs.append(msg)
            return
        self.log_text.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.log_text.see(tk.END)

    def _make_scrollable_tab(self, parent):
        container = ttk.Frame(parent)
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container, highlightthickness=0)
        vbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vbar.set)

        vbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        content = ttk.Frame(canvas)
        window_id = canvas.create_window((0, 0), window=content, anchor="nw")

        def _on_frame_configure(_event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event):
            canvas.itemconfigure(window_id, width=event.width)

        content.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        # 鼠标悬停时支持滚轮滚动
        def _bind_mousewheel(_event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_mousewheel(_event):
            canvas.unbind_all("<MouseWheel>")

        def _on_mousewheel(event):
            # Windows 下 event.delta 一般为 120 的倍数
            canvas.yview_scroll(int(-event.delta / 120), "units")

        canvas.bind("<Enter>", _bind_mousewheel)
        canvas.bind("<Leave>", _unbind_mousewheel)

        return content

    def build_control_tab(self):
        # --- 连接区 ---
        conn_frame = tk.LabelFrame(self.tab_control, text="物理机械臂连接 (端口 8899)", padx=10, pady=10)
        conn_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(conn_frame, text="机械臂 IP:").grid(row=0, column=0, padx=5, pady=5)
        self.ip_entry = tk.Entry(conn_frame, width=18)
        self.ip_entry.insert(0, "192.168.31.6")
        self.ip_entry.grid(row=0, column=1, padx=5, pady=5)

        self.btn_connect = tk.Button(conn_frame, text="连接实机", command=self.connect_robot, bg="#d9edf7")
        self.btn_connect.grid(row=0, column=2, padx=5, pady=5)
        self.btn_disconnect = tk.Button(conn_frame, text="断开连接", command=self.disconnect_robot, state=tk.DISABLED, bg="#f2dede")
        self.btn_disconnect.grid(row=0, column=3, padx=5, pady=5)

        self.btn_stop = tk.Button(conn_frame, text="停止运动", command=self.stop_robot, state=tk.DISABLED, bg="#fff3cd", width=10)
        self.btn_stop.grid(row=0, column=4, padx=5, pady=5)
        self.btn_estop = tk.Button(conn_frame, text="急停 E-STOP", command=self.emergency_stop, state=tk.DISABLED,
                                   bg="#dc3545", fg="white", font=("Arial", 14, "bold"), width=12, height=2)
        self.btn_estop.grid(row=0, column=5, padx=10, pady=5, rowspan=2)

        # --- 夹爪控制 ---
        gripper_frame = tk.LabelFrame(self.tab_control, text="夹爪控制", padx=10, pady=10)
        gripper_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(gripper_frame, text="夹爪 IP:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.gripper_ip_entry = tk.Entry(gripper_frame, width=18)
        self.gripper_ip_entry.insert(0, GRIPPER_IP)
        self.gripper_ip_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        self.btn_gripper_open = tk.Button(
            gripper_frame, text="张开夹爪", command=self.gripper_open, bg="#dff0d8", width=10
        )
        self.btn_gripper_open.grid(row=0, column=2, padx=10, pady=5)

        self.btn_gripper_close = tk.Button(
            gripper_frame, text="闭合夹爪", command=self.gripper_close, bg="#f2dede", width=10
        )
        self.btn_gripper_close.grid(row=0, column=3, padx=10, pady=5)

        tk.Label(gripper_frame, text="百分比 (%):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.gripper_percent_var = tk.IntVar(value=50)
        self.gripper_percent_scale = tk.Scale(
            gripper_frame, from_=0, to=100, orient=tk.HORIZONTAL, length=200,
            variable=self.gripper_percent_var
        )
        self.gripper_percent_scale.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        self.btn_gripper_percent = tk.Button(
            gripper_frame, text="设置百分比", command=self.gripper_set_percent, bg="#e8f4ff"
        )
        self.btn_gripper_percent.grid(row=1, column=2, padx=10, pady=5)

        tk.Label(gripper_frame, text="脉宽 (μs):").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.gripper_us_entry = tk.Entry(gripper_frame, width=10)
        self.gripper_us_entry.insert(0, "1500")
        self.gripper_us_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        self.btn_gripper_us = tk.Button(
            gripper_frame, text="设置脉宽", command=self.gripper_set_us, bg="#e8f4ff"
        )
        self.btn_gripper_us.grid(row=2, column=2, padx=10, pady=5)

        self.lbl_gripper_status = tk.Label(gripper_frame, text="夹爪状态: 未操作", fg="#666")
        self.lbl_gripper_status.grid(row=2, column=3, padx=10, pady=5, sticky="w")

        # --- 咖啡自动流程 ---
        coffee_frame = tk.LabelFrame(self.tab_control, text="咖啡自动流程", padx=10, pady=10)
        coffee_frame.pack(fill="x", padx=10, pady=5)

        self.btn_coffee_run = tk.Button(
            coffee_frame, text="▶ 运行咖啡流程", command=self.run_coffee_demo,
            state=tk.DISABLED, bg="#dff0d8", font=("Arial", 12, "bold"), width=20, height=2
        )
        self.btn_coffee_run.grid(row=0, column=0, padx=10, pady=5)

        self.btn_coffee_stop = tk.Button(
            coffee_frame, text="■ 急停", command=self.coffee_demo_stop,
            state=tk.DISABLED, bg="#dc3545", fg="white", font=("Arial", 12, "bold"), width=10, height=2
        )
        self.btn_coffee_stop.grid(row=0, column=1, padx=10, pady=5)

        self.lbl_coffee_status = tk.Label(coffee_frame, text="状态: 未运行", fg="#666", font=("Arial", 11))
        self.lbl_coffee_status.grid(row=0, column=2, padx=15, pady=5, sticky="w")

        self._coffee_demo_running = False

        # --- 速度控制 ---
        speed_frame = tk.LabelFrame(self.tab_control, text="运动速度控制", padx=10, pady=5)
        speed_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(speed_frame, text="速度倍率:").grid(row=0, column=0, padx=5)
        self.speed_var = tk.IntVar(value=30)
        self.speed_scale = tk.Scale(speed_frame, from_=1, to=100, orient=tk.HORIZONTAL, length=400,
                                    variable=self.speed_var, command=self.on_speed_change)
        self.speed_scale.grid(row=0, column=1, padx=5)
        self.lbl_speed = tk.Label(speed_frame, text="30%", width=8)
        self.lbl_speed.grid(row=0, column=2, padx=5)

        # --- 状态区 ---
        status_frame = tk.LabelFrame(self.tab_control, text="实时位姿监控", padx=10, pady=10)
        status_frame.pack(fill="x", padx=10, pady=5)
        self.lbl_pos = tk.Label(status_frame, text="末端位置 (XYZ): [未连接]", fg="blue")
        self.lbl_pos.pack(anchor="w", pady=2)
        self.lbl_ori = tk.Label(status_frame, text="末端姿态 (WXYZ): [未连接]", fg="blue")
        self.lbl_ori.pack(anchor="w", pady=2)
        self.lbl_joints = tk.Label(status_frame, text="六轴关节角 (Rad): [未连接]", fg="green")
        self.lbl_joints.pack(anchor="w", pady=2)

        # --- 目标点位区 ---
        point_frame = tk.LabelFrame(self.tab_control, text="目标点位管理", padx=10, pady=10)
        point_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(point_frame, text="点位名称:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.point_name_entry = tk.Entry(point_frame, width=18)
        self.point_name_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        self.btn_save_point = tk.Button(point_frame, text="保存当前滑条为点位", command=self.save_target_point)
        self.btn_save_point.grid(row=0, column=2, padx=5, pady=5, sticky="w")

        tk.Label(point_frame, text="已存点位:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.point_combo = ttk.Combobox(point_frame, values=[], state="readonly", width=28)
        self.point_combo.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        self.btn_load_point = tk.Button(point_frame, text="加载点位到滑条", command=self.load_target_point)
        self.btn_load_point.grid(row=1, column=2, padx=5, pady=5, sticky="w")

        self.btn_sync_current = tk.Button(point_frame, text="读取当前姿态到滑条", command=self.sync_current_to_sliders)
        self.btn_sync_current.grid(row=0, column=3, rowspan=2, padx=8, pady=5, sticky="w")

        # --- 一键记录到配置文件 ---
        record_frame = tk.LabelFrame(self.tab_control, text="一键记录到配置文件", padx=10, pady=10)
        record_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(record_frame, text="所属步骤:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.step_choices = [
            ("pick_cup", "拿杯子"),
            ("place_cup_under_machine", "放杯到咖啡机下"),
            ("pick_capsule", "拿胶囊"),
            ("open_machine_lid", "打开盖子"),
            ("insert_capsule", "放胶囊"),
            ("close_machine_lid", "盖上盖子"),
            ("press_start_button", "按启动键"),
            ("wait_for_brew", "等待萃取"),
            ("pick_cup_from_machine", "取杯"),
            ("deliver_cup", "送到指定位置"),
        ]
        self.record_step_var = tk.StringVar(value=self.step_choices[0][0])
        step_combo = ttk.Combobox(
            record_frame,
            values=[f"{name} ({desc})" for name, desc in self.step_choices],
            state="readonly",
            width=24,
            textvariable=self.record_step_var,
        )
        step_combo.current(0)
        step_combo.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.record_step_combo = step_combo

        tk.Label(record_frame, text="子点位描述:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.record_desc_entry = tk.Entry(record_frame, width=12)
        self.record_desc_entry.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        self.btn_record_point = tk.Button(
            record_frame, text="记录当前位置", command=self.record_point_to_config,
            state=tk.DISABLED, bg="#dff0d8"
        )
        self.btn_record_point.grid(row=1, column=0, padx=5, pady=5, sticky="w")

        self.lbl_record_status = tk.Label(record_frame, text="", fg="#666")
        self.lbl_record_status.grid(row=1, column=1, columnspan=3, padx=5, pady=5, sticky="w")

        # --- 关节滑条区 ---
        limits = AuboWindowsSDK.JOINT_LIMITS_DEG
        slider_frame = tk.LabelFrame(self.tab_control, text="关节控制（滑动条，单位°）", padx=10, pady=10)
        slider_frame.pack(fill="x", padx=10, pady=5)

        for i in range(6):
            low, high = limits[i]
            tk.Label(slider_frame, text=f"J{i + 1}").grid(row=i, column=0, padx=5, pady=3, sticky="w")

            var = tk.DoubleVar(value=0.0)
            scale = tk.Scale(
                slider_frame,
                from_=low,
                to=high,
                orient=tk.HORIZONTAL,
                length=500,
                resolution=0.1,
                variable=var,
                command=lambda _v, idx=i: self.on_slider_change(idx)
            )
            scale.grid(row=i, column=1, padx=5, pady=3)
            self.slider_vars.append(var)

            lbl = tk.Label(slider_frame, text="0.0°")
            lbl.grid(row=i, column=2, padx=5, pady=3, sticky="w")
            self.slider_value_labels.append(lbl)

            tk.Label(slider_frame, text=f"[{low:.0f}°, {high:.0f}°]").grid(row=i, column=3, padx=5, pady=3, sticky="w")

        self.btn_move_target = tk.Button(
            slider_frame,
            text="执行到目标点位",
            command=self.execute_target_point,
            state=tk.DISABLED,
            bg="#dff0d8"
        )
        self.btn_move_target.grid(row=6, column=1, sticky="w", pady=8)

        self.lbl_target_tip = tk.Label(slider_frame, text="校验: 未执行", fg="#666")
        self.lbl_target_tip.grid(row=6, column=2, columnspan=2, sticky="w")

        # --- 直接输入执行区（恢复保留） ---
        direct_frame = tk.LabelFrame(self.tab_control, text="点位输入直接执行（rad）", padx=10, pady=10)
        direct_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(direct_frame, text="目标关节角（JSON数组，6轴）:").pack(anchor="w")
        self.direct_input_entry = tk.Entry(direct_frame)
        self.direct_input_entry.insert(0, "[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]")
        self.direct_input_entry.pack(fill="x", pady=5)

        self.btn_direct_execute = tk.Button(
            direct_frame,
            text="按输入直接执行",
            command=self.execute_direct_input,
            state=tk.DISABLED,
            bg="#f5f5dc"
        )
        self.btn_direct_execute.pack(anchor="w")

        # --- 相机影像区 ---
        camera_frame = tk.LabelFrame(self.tab_control, text="Gemini335L 相机影像", padx=10, pady=10)
        camera_frame.pack(fill="x", padx=10, pady=5)

        self.btn_capture_photo = tk.Button(
            camera_frame, text="拍照（1帧）", command=self.capture_photo, bg="#e8f4ff"
        )
        self.btn_capture_photo.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.btn_record_3s = tk.Button(
            camera_frame, text="录像 3 秒（常规画质）", command=lambda: self.capture_video(3), bg="#e8f4ff"
        )
        self.btn_record_3s.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        self.btn_record_5s = tk.Button(
            camera_frame, text="录像 5 秒（常规画质）", command=lambda: self.capture_video(5), bg="#e8f4ff"
        )
        self.btn_record_5s.grid(row=0, column=2, padx=5, pady=5, sticky="w")

        self.btn_record_10s = tk.Button(
            camera_frame, text="录像 10 秒（常规画质）", command=lambda: self.capture_video(10), bg="#e8f4ff"
        )
        self.btn_record_10s.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        self.btn_depth_photo = tk.Button(
            camera_frame, text="深度拍照（1帧）", command=self.capture_depth_photo, bg="#f3e8ff"
        )
        self.btn_depth_photo.grid(row=1, column=0, padx=5, pady=5, sticky="w")

        self.btn_depth_3s = tk.Button(
            camera_frame, text="深度录像 3 秒", command=lambda: self.capture_depth_video(3), bg="#f3e8ff"
        )
        self.btn_depth_3s.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        self.btn_depth_5s = tk.Button(
            camera_frame, text="深度录像 5 秒", command=lambda: self.capture_depth_video(5), bg="#f3e8ff"
        )
        self.btn_depth_5s.grid(row=1, column=2, padx=5, pady=5, sticky="w")

        self.btn_depth_10s = tk.Button(
            camera_frame, text="深度录像 10 秒", command=lambda: self.capture_depth_video(10), bg="#f3e8ff"
        )
        self.btn_depth_10s.grid(row=1, column=3, padx=5, pady=5, sticky="w")

        self.lbl_camera_state = tk.Label(
            camera_frame,
            text=(
                f"相机状态: 可用（模式: {self.camera_service.mode_name}）"
                if self.camera_enabled
                else f"相机状态: 不可用（{self.camera_disabled_reason}）"
            ),
            fg="green" if self.camera_enabled else "red",
        )
        self.lbl_camera_state.grid(row=2, column=0, columnspan=4, padx=5, pady=3, sticky="w")

        tk.Label(camera_frame, text="选择相机:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.camera_select_var = tk.StringVar(value="")
        self.camera_combo = ttk.Combobox(camera_frame, textvariable=self.camera_select_var, width=40, state="readonly")
        self.camera_combo.grid(row=3, column=1, columnspan=2, padx=5, pady=5, sticky="w")
        self.btn_refresh_cams = tk.Button(camera_frame, text="刷新相机列表", command=self.refresh_camera_devices)
        self.btn_refresh_cams.grid(row=3, column=3, padx=5, pady=5, sticky="w")

        self.btn_apply_cam = tk.Button(camera_frame, text="应用所选相机", command=self.apply_selected_camera)
        self.btn_apply_cam.grid(row=4, column=3, padx=5, pady=5, sticky="w")

        media_list_frame = tk.LabelFrame(self.tab_control, text="本地影像列表（SQLite映射）", padx=10, pady=10)
        media_list_frame.pack(fill="x", padx=10, pady=5)
        self.media_list_container = tk.Frame(media_list_frame)
        self.media_list_container.pack(fill="x")
        self.refresh_media_list()
        self.refresh_camera_devices()

    def build_api_tab(self):
        desc = (
            "本页已将 WebAPI 与 ROS2API 拆分为独立服务。\n"
            "WebAPI 用于浏览器测试与前端调用；ROS2API 用于 ROS2 桥接侧调用。\n"
            "建议先在“仪表盘与控制”页完成机械臂连接，再启动服务。"
        )
        tk.Label(self.tab_api, text=desc, justify="left", fg="#666").pack(pady=10, padx=10, anchor="w")

        web_frame = tk.LabelFrame(self.tab_api, text="WebAPI 服务（网页 + API）", padx=10, pady=10)
        web_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(web_frame, text="服务端口:").grid(row=0, column=0, padx=5, pady=5)
        self.web_port_entry = tk.Entry(web_frame, width=10)
        self.web_port_entry.insert(0, "8000")
        self.web_port_entry.grid(row=0, column=1, padx=5, pady=5)
        self.btn_start_web_api = tk.Button(
            web_frame, text="▶ 启动 WebAPI", command=self.start_api_server, bg="#dff0d8"
        )
        self.btn_start_web_api.grid(row=0, column=2, padx=15, pady=5)
        self.lbl_web_api_status = tk.Label(web_frame, text="服务状态: 已停止", fg="red")
        self.lbl_web_api_status.grid(row=0, column=3, padx=15, pady=5)

        ros2_frame = tk.LabelFrame(self.tab_api, text="ROS2API 服务（独立接口）", padx=10, pady=10)
        ros2_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(ros2_frame, text="服务端口:").grid(row=0, column=0, padx=5, pady=5)
        self.ros2_port_entry = tk.Entry(ros2_frame, width=10)
        self.ros2_port_entry.insert(0, "8001")
        self.ros2_port_entry.grid(row=0, column=1, padx=5, pady=5)
        self.btn_start_ros2_api = tk.Button(
            ros2_frame, text="▶ 启动 ROS2API", command=self.start_ros2_api_server, bg="#e8f4ff"
        )
        self.btn_start_ros2_api.grid(row=0, column=2, padx=15, pady=5)
        self.lbl_ros2_api_status = tk.Label(ros2_frame, text="服务状态: 已停止", fg="red")
        self.lbl_ros2_api_status.grid(row=0, column=3, padx=15, pady=5)

        info_frame = tk.LabelFrame(self.tab_api, text="接口文档指南", padx=10, pady=10)
        info_frame.pack(fill="both", expand=True, padx=10, pady=5)
        doc = """支持的接口列表:
- WebAPI:
  GET  http://<这台电脑IP>:8000/            -> Web 控制页面（自动打开）
  GET  http://<这台电脑IP>:8000/api/info    -> 系统状态
  POST http://<这台电脑IP>:8000/api/movej   -> 机械臂运动

- ROS2API:
  GET  http://<这台电脑IP>:8001/ros2/info   -> ROS2 专用状态
  POST http://<这台电脑IP>:8001/ros2/movej  -> ROS2 专用运动接口

* 启动后你可以访问 /docs 查看 Swagger 页面。
"""
        text = tk.Text(info_frame, height=12, bg="#f8f9fa")
        text.insert("1.0", doc)
        text.config(state=tk.DISABLED)
        text.pack(fill="both", expand=True)

    def _set_joint_controls_state(self, connected):
        state = tk.NORMAL if connected else tk.DISABLED
        self.btn_save_point.config(state=state)
        self.btn_load_point.config(state=state)
        self.btn_sync_current.config(state=state)
        self.btn_move_target.config(state=state)
        self.btn_direct_execute.config(state=state)
        self.btn_record_point.config(state=state)
        self.point_name_entry.config(state=state)
        self.record_desc_entry.config(state=state)
        self.direct_input_entry.config(state=state)
        self.point_combo.config(state="readonly" if connected else "disabled")
        self.btn_coffee_run.config(state=state)
        # 相机功能不依赖机械臂连接，但依赖 SDK 可用性
        camera_state = tk.NORMAL if self.camera_enabled else tk.DISABLED
        self.btn_capture_photo.config(state=camera_state)
        self.btn_record_3s.config(state=camera_state)
        self.btn_record_5s.config(state=camera_state)
        self.btn_record_10s.config(state=camera_state)
        # 深度功能仅 pyorbbecsdk 模式可用
        depth_state = tk.NORMAL if self.camera_enabled else tk.DISABLED
        self.btn_depth_photo.config(state=depth_state)
        self.btn_depth_3s.config(state=depth_state)
        self.btn_depth_5s.config(state=depth_state)
        self.btn_depth_10s.config(state=depth_state)
        self.btn_refresh_cams.config(state=camera_state)
        self.btn_apply_cam.config(state=camera_state)
        self.camera_combo.config(state="readonly" if self.camera_enabled else "disabled")

    def on_slider_change(self, idx):
        val = self.slider_vars[idx].get()
        self.slider_value_labels[idx].config(text=f"{val:.1f}°")

    def get_slider_values_deg(self):
        return [v.get() for v in self.slider_vars]

    def get_slider_values_rad(self):
        return [math.radians(v) for v in self.get_slider_values_deg()]

    def refresh_point_combo(self):
        names = sorted(self.target_points.keys())
        self.point_combo["values"] = names
        if names and not self.point_combo.get():
            self.point_combo.set(names[0])

    def save_target_point(self):
        name = self.point_name_entry.get().strip()
        if not name:
            messagebox.showwarning("校验提示", "请先输入点位名称。")
            return
        self.target_points[name] = self.get_slider_values_deg()
        self.refresh_point_combo()
        self.point_combo.set(name)
        self.log(f"[点位] 已保存点位: {name}")

    def record_point_to_config(self):
        """获取当前机械臂关节角，以 POS_{步骤名}_{描述} 格式写入 coffee_config.py"""
        if not self.robot.connected:
            messagebox.showwarning("校验提示", "请先连接机械臂。")
            return

        # 解析选中的步骤名
        step_text = self.record_step_combo.get().strip()
        if not step_text:
            messagebox.showwarning("校验提示", "请选择所属步骤。")
            return
        step_name = step_text.split(" ")[0]  # 取 "pick_cup (拿杯子)" 中的 "pick_cup"

        desc = self.record_desc_entry.get().strip()
        if not desc:
            messagebox.showwarning("校验提示", "请输入子点位描述（如：接近、抓取、提起）。")
            return

        var_name = f"POS_{step_name}_{desc}"

        # 读取当前关节角（弧度）
        wp = self.robot.get_waypoint()
        if not wp:
            messagebox.showerror("读取失败", "无法读取当前姿态，请检查连接。")
            return
        joints = list(wp.jointpos)
        vals = ", ".join(f"{v:.4f}" for v in joints)
        new_line = f"{var_name} = [{vals}]\n"

        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "coffee_config.py")

        # 读取已有内容，替换同名行或追加
        lines = []
        found = False
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not found and (line.strip().startswith(var_name + " ") or line.strip().startswith(var_name + "=")):
                        lines.append(new_line)
                        found = True
                    else:
                        lines.append(line)
        except FileNotFoundError:
            pass

        if not found:
            lines.append(new_line)

        try:
            with open(config_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
        except Exception as e:
            messagebox.showerror("写入失败", f"无法写入配置文件: {e}")
            return

        action = "已覆盖" if found else "已写入"
        self.lbl_record_status.config(text=f"{action} {var_name}", fg="green")
        self.log(f"[点位] {action}到配置文件: {var_name} = [{vals}]")
        self.record_desc_entry.delete(0, tk.END)

    def load_target_point(self):
        name = self.point_combo.get().strip()
        if not name or name not in self.target_points:
            messagebox.showwarning("校验提示", "请选择有效点位。")
            return
        values = self.target_points[name]
        for i, val in enumerate(values):
            self.slider_vars[i].set(val)
            self.on_slider_change(i)
        self.log(f"[点位] 已加载点位: {name}")

    def sync_current_to_sliders(self):
        if not self.robot.connected:
            messagebox.showwarning("校验提示", "请先连接机械臂。")
            return
        wp = self.robot.get_waypoint()
        if not wp:
            messagebox.showerror("读取失败", "无法读取当前姿态，请检查连接。")
            return
        for i in range(6):
            deg = math.degrees(wp.jointpos[i])
            low, high = AuboWindowsSDK.JOINT_LIMITS_DEG[i]
            deg = min(max(deg, low), high)
            self.slider_vars[i].set(deg)
            self.on_slider_change(i)
        self.log("[点位] 当前机械臂姿态已同步到滑条。")

    def connect_robot(self):
        ip = self.ip_entry.get().strip()
        if not ip:
            messagebox.showwarning("校验提示", "IP 不能为空。")
            return

        self.log(f"正在尝试连接 {ip}:8899 ...")
        success, msg = self.robot.connect(ip, 8899)
        if success:
            self.log("[成功] 机械臂连接成功！")
            self.btn_connect.config(state=tk.DISABLED)
            self.btn_disconnect.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.NORMAL)
            self.btn_estop.config(state=tk.NORMAL)
            self._set_joint_controls_state(True)
            self.robot.set_speed_percent(self.speed_var.get())
            self.status_loop_running = True
            threading.Thread(target=self.robot_status_loop, daemon=True).start()
            self.sync_current_to_sliders()
        else:
            self.log(f"[错误] {msg}")
            messagebox.showerror("连接失败", msg)

    def disconnect_robot(self):
        self.status_loop_running = False
        self.robot.disconnect()
        self.log("[系统] 机械臂已断开。")
        self.btn_connect.config(state=tk.NORMAL)
        self.btn_disconnect.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.DISABLED)
        self.btn_estop.config(state=tk.DISABLED)
        self._set_joint_controls_state(False)
        self.lbl_pos.config(text="末端位置 (XYZ): [已断开]")
        self.lbl_ori.config(text="末端姿态 (WXYZ): [已断开]")
        self.lbl_joints.config(text="六轴关节角 (Rad): [已断开]")
        self.lbl_target_tip.config(text="校验: 未执行", fg="#666")

    def emergency_stop(self):
        if self.robot.connected:
            self.robot.fast_stop()
            self.log("[急停] 已触发急停！所有运动立即停止。")

    def stop_robot(self):
        if self.robot.connected:
            self.robot.stop()
            self.log("[停止] 已发送停止指令。")

    def on_speed_change(self, _val=None):
        percent = self.speed_var.get()
        self.lbl_speed.config(text=f"{percent}%")
        if self.robot.connected:
            self.robot.set_speed_percent(percent)

    def robot_status_loop(self):
        while self.status_loop_running:
            wp = self.robot.get_waypoint()
            if wp:
                pos_str = f"[{wp.cartPos.x:.4f}, {wp.cartPos.y:.4f}, {wp.cartPos.z:.4f}]"
                ori_str = f"[{wp.orientation.w:.4f}, {wp.orientation.x:.4f}, {wp.orientation.y:.4f}, {wp.orientation.z:.4f}]"
                j_list = [wp.jointpos[i] for i in range(6)]
                j_str = f"[{j_list[0]:.4f}, {j_list[1]:.4f}, {j_list[2]:.4f}, {j_list[3]:.4f}, {j_list[4]:.4f}, {j_list[5]:.4f}]"
                self.root.after(0, lambda p=pos_str, o=ori_str, j=j_str: self.update_status_labels(p, o, j))
            time.sleep(0.5)

    def update_status_labels(self, pos, ori, joints):
        self.lbl_pos.config(text=f"末端位置 (XYZ): {pos}")
        self.lbl_ori.config(text=f"末端姿态 (WXYZ): {ori}")
        self.lbl_joints.config(text=f"六轴关节角 (Rad): {joints}")

    def execute_target_point(self):
        if not self.robot.connected:
            messagebox.showwarning("校验提示", "机械臂未连接。")
            return

        target_deg = self.get_slider_values_deg()
        target_rad = self.get_slider_values_rad()
        valid, msg = self.robot.validate_joints(target_rad)
        if not valid:
            self.lbl_target_tip.config(text=f"校验失败: {msg}", fg="red")
            messagebox.showerror("限位校验失败", msg)
            return

        confirm_text = (
            "即将执行目标点位（单位°）:\n"
            f"J1={target_deg[0]:.1f}, J2={target_deg[1]:.1f}, J3={target_deg[2]:.1f},\n"
            f"J4={target_deg[3]:.1f}, J5={target_deg[4]:.1f}, J6={target_deg[5]:.1f}\n\n"
            "请确认当前环境安全后继续。"
        )
        if not messagebox.askyesno("执行确认", confirm_text):
            return

        self.btn_move_target.config(state=tk.DISABLED)
        self.lbl_target_tip.config(text="校验通过，执行中...", fg="#333")
        self.log(f"GUI 触发目标点位执行: {target_deg}")

        def run_move():
            success, run_msg = self.robot.movej_safe(target_rad)
            if success:
                self.root.after(0, self.log, "[成功] 目标点位执行完成。")
                self.root.after(0, lambda: self.lbl_target_tip.config(text="执行成功", fg="green"))
            else:
                fail_text = f"{run_msg}"
                if "不可达" not in fail_text:
                    fail_text += "（目标点位可能不可达）"
                self.root.after(0, self.log, f"[错误] {fail_text}")
                self.root.after(0, lambda: self.lbl_target_tip.config(text=f"执行失败: {run_msg}", fg="red"))
                self.root.after(0, lambda: messagebox.showerror("执行失败", fail_text))

            self.root.after(0, lambda: self.btn_move_target.config(state=tk.NORMAL))

        threading.Thread(target=run_move, daemon=True).start()

    def execute_direct_input(self):
        if not self.robot.connected:
            messagebox.showwarning("校验提示", "机械臂未连接。")
            return

        raw = self.direct_input_entry.get().strip()
        try:
            joints = json.loads(raw)
            if not isinstance(joints, list) or len(joints) != 6:
                raise ValueError
            joints = [float(v) for v in joints]
        except Exception:
            messagebox.showerror("格式错误", "请输入有效 JSON 数组，例如: [0, 0, 0, 0, 0, 0]")
            return

        valid, msg = self.robot.validate_joints(joints)
        if not valid:
            self.lbl_target_tip.config(text=f"校验失败: {msg}", fg="red")
            messagebox.showerror("限位校验失败", msg)
            return

        self.btn_direct_execute.config(state=tk.DISABLED)
        self.log(f"GUI 触发直接输入执行: {joints}")

        def run_move():
            success, run_msg = self.robot.movej_safe(joints)
            if success:
                self.root.after(0, self.log, "[成功] 直接输入执行完成。")
                # 同步滑条显示
                deg_vals = [math.degrees(v) for v in joints]
                for i, deg in enumerate(deg_vals):
                    self.root.after(0, lambda idx=i, d=deg: self.slider_vars[idx].set(d))
                    self.root.after(0, lambda idx=i: self.on_slider_change(idx))
            else:
                self.root.after(0, self.log, f"[错误] {run_msg}")
                self.root.after(0, lambda: messagebox.showerror("执行失败", run_msg))

            self.root.after(0, lambda: self.btn_direct_execute.config(state=tk.NORMAL))

        threading.Thread(target=run_move, daemon=True).start()

    def refresh_media_list(self):
        for w in self.media_row_widgets:
            try:
                w.destroy()
            except Exception:
                pass
        self.media_row_widgets.clear()

        records = self.media_store.list_records(limit=50)
        if not records:
            lbl = tk.Label(self.media_list_container, text="暂无影像记录。", fg="#666")
            lbl.pack(anchor="w", pady=3)
            self.media_row_widgets.append(lbl)
            return

        for rec in records:
            rec_id, media_type, file_path, duration_sec, width, height, fps, extra_info, created_at = rec
            row = tk.Frame(self.media_list_container)
            row.pack(fill="x", pady=2)

            name = os.path.basename(file_path)
            info = (
                f"[{rec_id}] {created_at} | {media_type} | {name} | "
                f"{width}x{height} | {duration_sec}s | {fps:.1f}fps"
            )
            if extra_info:
                info += f" | {extra_info}"
            lbl = tk.Label(row, text=info, anchor="w")
            lbl.pack(side="left", fill="x", expand=True)

            btn_play = tk.Button(row, text="播放", width=8, command=lambda p=file_path: self.play_media(p))
            btn_play.pack(side="right", padx=2)
            btn_del = tk.Button(row, text="删除", width=8, command=lambda i=rec_id: self.delete_media(i))
            btn_del.pack(side="right", padx=2)

            self.media_row_widgets.extend([row, lbl, btn_play, btn_del])

    def capture_photo(self):
        if not self.camera_enabled:
            messagebox.showerror("相机不可用", self.camera_disabled_reason)
            return
        self.log("[相机] 正在拍照（1帧）...")
        self._set_camera_buttons_state(False)

        def worker():
            try:
                file_path, w, h = self.camera_service.capture_photo(self.media_store.media_dir)
                self.media_store.add_record("photo", file_path, duration_sec=0, width=w, height=h, fps=0)
                self.root.after(0, self.log, f"[相机] 拍照成功: {file_path}")
                self.root.after(0, self.refresh_media_list)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("拍照失败", str(e)))
                self.root.after(0, self.log, f"[相机] 拍照失败: {e}")
            finally:
                self.root.after(0, lambda: self._set_camera_buttons_state(True))

        threading.Thread(target=worker, daemon=True).start()

    def capture_depth_photo(self):
        if not self.camera_enabled:
            messagebox.showerror("相机不可用", self.camera_disabled_reason)
            return
        self.log("[相机] 正在采集深度拍照（1帧）...")
        self._set_camera_buttons_state(False)

        def worker():
            try:
                file_path, w, h, hint = self.camera_service.capture_depth_photo(self.media_store.media_dir)
                self.media_store.add_record("depth_photo", file_path, duration_sec=0, width=w, height=h, fps=0, extra_info=hint)
                self.root.after(0, self.log, f"[相机] 深度拍照成功: {file_path} | {hint}")
                self.root.after(0, self.refresh_media_list)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("深度拍照失败", str(e)))
                self.root.after(0, self.log, f"[相机] 深度拍照失败: {e}")
            finally:
                self.root.after(0, lambda: self._set_camera_buttons_state(True))

        threading.Thread(target=worker, daemon=True).start()

    def refresh_camera_devices(self):
        if not self.camera_enabled:
            return
        try:
            devices = self.camera_service.list_camera_devices()
        except Exception as e:
            messagebox.showerror("相机检测失败", str(e))
            return

        self.camera_devices = devices
        if not devices:
            self.camera_combo["values"] = ["未检测到可用 Orbbec 设备"]
            self.camera_combo.set("未检测到可用 Orbbec 设备")
            self.log("[相机] 未检测到可用 Orbbec 设备。")
            return

        labels = [f"{idx}: {label}" for idx, _sn, label in devices]
        self.camera_combo["values"] = labels
        # 默认选择当前 serial 对应项，否则第一项
        current_sn = self.camera_service.selected_device_serial
        selected = None
        for idx, sn, label in devices:
            if current_sn and sn == current_sn:
                selected = f"{idx}: {label}"
                break
        self.camera_combo.set(selected or labels[0])
        self.log(f"[相机] 检测到 {len(devices)} 路相机。")

    def apply_selected_camera(self):
        if not self.camera_enabled:
            return
        text = self.camera_combo.get().strip()
        if not text or "未检测到" in text:
            messagebox.showwarning("提示", "请先刷新并选择可用相机。")
            return
        try:
            camera_idx = int(text.split(":")[0].strip())
        except Exception:
            messagebox.showerror("错误", "相机选择解析失败，请重新选择。")
            return
        serial = ""
        for idx, sn, _label in self.camera_devices:
            if idx == camera_idx:
                serial = sn
                break
        self.camera_service.select_camera_by_serial(serial)
        self.lbl_camera_state.config(text=f"相机状态: 可用（模式: {self.camera_service.mode_name}）", fg="green")
        self.log(f"[相机] 已切换到相机 index={camera_idx}, serial={serial}")

    def capture_video(self, duration_sec):
        if not self.camera_enabled:
            messagebox.showerror("相机不可用", self.camera_disabled_reason)
            return
        self.log(f"[相机] 正在录像 {duration_sec} 秒（常规画质）...")
        self._set_camera_buttons_state(False)

        def worker():
            try:
                file_path, w, h, real_duration, real_fps = self.camera_service.capture_video(
                    self.media_store.media_dir, duration_sec=duration_sec, target_fps=20
                )
                self.media_store.add_record(
                    "video", file_path, duration_sec=real_duration, width=w, height=h, fps=real_fps
                )
                self.root.after(0, self.log, f"[相机] 录像完成: {file_path} | 实测 {real_fps:.1f} fps")
                if real_fps < 20:
                    self.root.after(
                        0,
                        lambda: messagebox.showwarning(
                            "帧率偏低",
                            f"本次录像实测仅 {real_fps:.1f} fps。\n"
                            "建议：切换到 USB3.0 口、降低分辨率/关闭其他占用摄像头程序，或更换所选相机。"
                        ),
                    )
                self.root.after(0, self.refresh_media_list)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("录像失败", str(e)))
                self.root.after(0, self.log, f"[相机] 录像失败: {e}")
            finally:
                self.root.after(0, lambda: self._set_camera_buttons_state(True))

        threading.Thread(target=worker, daemon=True).start()

    def capture_depth_video(self, duration_sec):
        if not self.camera_enabled:
            messagebox.showerror("相机不可用", self.camera_disabled_reason)
            return
        self.log(f"[相机] 正在采集深度录像 {duration_sec} 秒...")
        self._set_camera_buttons_state(False)

        def worker():
            try:
                file_path, w, h, real_duration, real_fps, hint = self.camera_service.capture_depth_video(
                    self.media_store.media_dir, duration_sec=duration_sec, target_fps=30
                )
                self.media_store.add_record(
                    "depth_video",
                    file_path,
                    duration_sec=real_duration,
                    width=w,
                    height=h,
                    fps=real_fps,
                    extra_info=hint,
                )
                self.root.after(0, self.log, f"[相机] 深度录像完成: {file_path} | {hint} | {real_fps:.1f}fps")
                self.root.after(0, self.refresh_media_list)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("深度录像失败", str(e)))
                self.root.after(0, self.log, f"[相机] 深度录像失败: {e}")
            finally:
                self.root.after(0, lambda: self._set_camera_buttons_state(True))

        threading.Thread(target=worker, daemon=True).start()

    def _set_camera_buttons_state(self, enabled):
        state = tk.NORMAL if (enabled and self.camera_enabled) else tk.DISABLED
        self.btn_capture_photo.config(state=state)
        self.btn_record_3s.config(state=state)
        self.btn_record_5s.config(state=state)
        self.btn_record_10s.config(state=state)

    def play_media(self, file_path):
        if not self.camera_enabled:
            messagebox.showerror("播放失败", "相机/媒体依赖不可用，请安装 opencv-python。")
            return

        def worker():
            try:
                self.camera_service.play_media(file_path)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("播放失败", str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def delete_media(self, record_id):
        if not messagebox.askyesno("确认删除", "确定删除该影像记录和对应文件吗？"):
            return
        self.media_store.delete_record(record_id)
        self.refresh_media_list()
        self.log(f"[相机] 已删除记录 ID={record_id}")

    def _start_uvicorn_service(self, app_obj, port, service_name, btn, lbl, state_key, open_url=None):
        btn.config(state=tk.DISABLED, text="启动中...")

        def run_uvicorn():
            try:
                setattr(core_state, state_key, True)
                self.root.after(0, self.log, f"[{service_name}] 服务正在 0.0.0.0:{port} 启动...")
                self.root.after(
                    0, lambda: lbl.config(text=f"服务状态: 运行中 (端口: {port})", fg="green")
                )
                if open_url:
                    self.root.after(1200, lambda: webbrowser.open(open_url))
                uvicorn.run(
                    app_obj,
                    host="0.0.0.0",
                    port=port,
                    loop="asyncio",
                    http="h11",
                    ws="none",
                    lifespan="off",
                    access_log=False,
                    log_config=None,
                )
            except Exception as e:
                self.root.after(0, self.log, f"[{service_name} 异常] {e}")
            finally:
                setattr(core_state, state_key, False)
                self.root.after(0, lambda: btn.config(state=tk.NORMAL, text=f"▶ 启动 {service_name}"))
                self.root.after(0, lambda: lbl.config(text="服务状态: 已停止", fg="red"))
                self.root.after(0, self.log, f"[{service_name}] 服务已退出。")

        threading.Thread(target=run_uvicorn, daemon=True).start()

    def start_api_server(self):
        try:
            port = int(self.web_port_entry.get().strip())
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            messagebox.showerror("错误", "端口必须是 1~65535 的数字")
            return

        core_state.web_api_port = port
        self._start_uvicorn_service(
            app_obj=api_server.app,
            port=port,
            service_name="WebAPI",
            btn=self.btn_start_web_api,
            lbl=self.lbl_web_api_status,
            state_key="web_api_running",
            open_url=f"http://127.0.0.1:{port}/",
        )

    def start_ros2_api_server(self):
        try:
            port = int(self.ros2_port_entry.get().strip())
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            messagebox.showerror("错误", "ROS2API 端口必须是 1~65535 的数字")
            return

        core_state.ros2_api_port = port
        self._start_uvicorn_service(
            app_obj=ros2_api_server.app,
            port=port,
            service_name="ROS2API",
            btn=self.btn_start_ros2_api,
            lbl=self.lbl_ros2_api_status,
            state_key="ros2_api_running",
        )

    # ==================== 夹爪控制 ====================
    def _get_gripper_base_url(self):
        ip = self.gripper_ip_entry.get().strip()
        if not ip:
            messagebox.showwarning("校验提示", "请输入夹爪 IP 地址。")
            return None
        return f"http://{ip}"

    def _send_gripper_cmd(self, url, desc):
        def worker():
            try:
                self.root.after(0, lambda: self.lbl_gripper_status.config(text=f"夹爪状态: {desc}中...", fg="#333"))
                resp = http_requests.get(url, timeout=5)
                if resp.ok:
                    self.root.after(0, self.log, f"[夹爪] {desc}成功: {url}")
                    self.root.after(0, lambda: self.lbl_gripper_status.config(text=f"夹爪状态: {desc}成功", fg="green"))
                else:
                    self.root.after(0, self.log, f"[夹爪] {desc}失败: HTTP {resp.status_code}")
                    self.root.after(0, lambda: self.lbl_gripper_status.config(text=f"夹爪状态: {desc}失败", fg="red"))
            except Exception as e:
                self.root.after(0, self.log, f"[夹爪] {desc}异常: {e}")
                self.root.after(0, lambda: self.lbl_gripper_status.config(text=f"夹爪状态: 连接异常", fg="red"))
        threading.Thread(target=worker, daemon=True).start()

    def gripper_open(self):
        base = self._get_gripper_base_url()
        if base:
            self._send_gripper_cmd(f"{base}/set?cmd=1", "张开夹爪")

    def gripper_close(self):
        base = self._get_gripper_base_url()
        if base:
            self._send_gripper_cmd(f"{base}/set?cmd=0", "闭合夹爪")

    def gripper_set_percent(self):
        base = self._get_gripper_base_url()
        if base:
            percent = self.gripper_percent_var.get()
            self._send_gripper_cmd(f"{base}/set?percent={percent}", f"设置夹爪百分比 {percent}%")

    def gripper_set_us(self):
        base = self._get_gripper_base_url()
        if base:
            raw = self.gripper_us_entry.get().strip()
            try:
                us = int(raw)
            except ValueError:
                messagebox.showerror("格式错误", "脉宽必须是整数（单位 μs）")
                return
            self._send_gripper_cmd(f"{base}/set?us={us}", f"设置夹爪脉宽 {us}μs")

    # ==================== 咖啡自动流程 ====================

    def coffee_demo_stop(self):
        self._coffee_demo_running = False
        if self.robot.connected:
            self.robot.fast_stop()
            self.log("[咖啡流程] 已急停！")
            self.root.after(0, lambda: self.lbl_coffee_status.config(text="状态: 已急停", fg="red"))
            self.root.after(0, lambda: self.btn_coffee_run.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.btn_coffee_stop.config(state=tk.DISABLED))

    def _coffee_gripper(self, cmd=None, percent=None):
        base = self._get_gripper_base_url()
        if not base:
            return
        try:
            if cmd is not None:
                http_requests.get(f"{base}/set?cmd={cmd}", timeout=5)
                self.root.after(0, self.log, f"[夹爪] cmd={cmd}")
            if percent is not None:
                http_requests.get(f"{base}/set?percent={percent}", timeout=5)
                self.root.after(0, self.log, f"[夹爪] percent={percent}%")
        except Exception as e:
            self.root.after(0, self.log, f"[夹爪] 控制失败: {e}")

    def _coffee_movej(self, joints, label):
        self.root.after(0, self.log, f"[咖啡流程] {label}")
        self.root.after(0, lambda: self.lbl_coffee_status.config(text=f"状态: {label}", fg="#333"))
        success, msg = self.robot.movej_safe(joints)
        if not success:
            self.root.after(0, self.log, f"[咖啡流程] {label} 失败: {msg}")
            return False
        return True

    def run_coffee_demo(self):
        if not self.robot.connected:
            messagebox.showwarning("校验提示", "请先连接机械臂。")
            return
        if self._coffee_demo_running:
            messagebox.showwarning("提示", "咖啡流程正在运行中。")
            return

        self._coffee_demo_running = True
        self.btn_coffee_run.config(state=tk.DISABLED)
        self.btn_coffee_stop.config(state=tk.NORMAL)

        def worker():
            total = len(STEPS)
            for i, (desc, action_type, params) in enumerate(STEPS):
                if not self._coffee_demo_running:
                    break
                self.root.after(0, self.log, f"[咖啡流程] 步骤 {i+1}/{total}: {desc}")
                if action_type == "movej":
                    self._coffee_movej(params, desc)
                elif action_type == "gripper":
                    self._coffee_gripper(**params)
                elif action_type == "movej+gripper":
                    joints, gripper_params = params
                    self._coffee_movej(joints, desc)
                    self._coffee_gripper(**gripper_params)
                time.sleep(1)

            # 流程结束（完成或急停）后自动回到初始位姿
            self.root.after(0, self.log, "[咖啡流程] 正在回到初始位姿...")
            self.root.after(0, lambda: self.lbl_coffee_status.config(text="状态: 回到初始位姿...", fg="#333"))
            self._coffee_movej(POS_HOME, "回到初始位姿")

            if self._coffee_demo_running:
                self.root.after(0, self.log, "[咖啡流程] 全部完成！")
                self.root.after(0, lambda: self.lbl_coffee_status.config(text="状态: 完成", fg="green"))
            self._coffee_demo_running = False
            self.root.after(0, lambda: self.btn_coffee_run.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.btn_coffee_stop.config(state=tk.DISABLED))

        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    root = tk.Tk()
    app = AuboHostApp(root)

    def on_closing():
        # 先停止咖啡流程
        app._coffee_demo_running = False
        if hasattr(app, 'robot') and app.robot.connected:
            app.robot.fast_stop()
            time.sleep(0.3)
            app.status_loop_running = False
            try:
                app.robot.disconnect()
            except Exception:
                pass
        root.destroy()
        os._exit(0)

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
