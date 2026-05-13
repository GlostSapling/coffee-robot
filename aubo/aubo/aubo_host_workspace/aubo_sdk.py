import ctypes
import os
import sys
import math

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
    # 软限位（度），用于 GUI/WebAPI 的统一校验。不同机型可按需调整。
    JOINT_LIMITS_DEG = [
        (-175.0, 175.0),  # J1
        (-175.0, 175.0),  # J2
        (-175.0, 175.0),  # J3
        (-175.0, 175.0),  # J4
        (-175.0, 175.0),  # J5
        (-175.0, 175.0),  # J6
    ]
    MAX_SINGLE_STEP_DEG = 90.0

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

        self.dll.rs_move_stop.argtypes = [ctypes.c_uint16]
        self.dll.rs_move_stop.restype = ctypes.c_int
        self.dll.rs_move_fast_stop.argtypes = [ctypes.c_uint16]
        self.dll.rs_move_fast_stop.restype = ctypes.c_int

        self.rshd = ctypes.c_uint16(0)
        self.connected = False
        self.current_ip = ""
        self.current_port = 0
        self.last_error = ""
        
        self.dll.rs_initialize()

    def connect(self, ip, port=8899):
        if self.connected:
            self.disconnect()
            
        if self.dll.rs_create_context(ctypes.byref(self.rshd)) != 0:
            return False, "无法创建上下文"
            
        ret = self.dll.rs_login(self.rshd.value, ip.encode('utf-8'), port)
        if ret != 0:
            self.dll.rs_destory_context(self.rshd.value)
            return False, f"登录失败，错误码: {ret}"
            
        self.connected = True
        self.current_ip = ip
        self.current_port = port
        
        # 初始化运动属性并设置安全速度
        self.dll.rs_init_global_move_profile(self.rshd.value)
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
            self.current_ip = ""
            
    def get_waypoint(self):
        if not self.connected:
            return None
        wp = wayPoint_S()
        if self.dll.rs_get_current_waypoint(self.rshd.value, ctypes.byref(wp)) == 0:
            return wp
        return None

    @staticmethod
    def deg_to_rad(deg):
        return deg * math.pi / 180.0

    @staticmethod
    def rad_to_deg(rad):
        return rad * 180.0 / math.pi

    def validate_joints(self, joints_rad, current_joints_rad=None):
        if len(joints_rad) != 6:
            return False, "目标关节数量必须为 6。"

        for i, val in enumerate(joints_rad):
            if not isinstance(val, (int, float)) or not math.isfinite(float(val)):
                return False, f"J{i + 1} 不是有效数字。"

            deg_val = self.rad_to_deg(float(val))
            low, high = self.JOINT_LIMITS_DEG[i]
            if deg_val < low or deg_val > high:
                return False, (
                    f"J{i + 1} 超出软限位，当前 {deg_val:.2f}°，"
                    f"允许范围 [{low:.1f}°, {high:.1f}°]。"
                )

        if current_joints_rad and len(current_joints_rad) == 6:
            for i in range(6):
                delta_deg = abs(self.rad_to_deg(joints_rad[i] - current_joints_rad[i]))
                if delta_deg > self.MAX_SINGLE_STEP_DEG:
                    return False, (
                        f"J{i + 1} 单次跳变 {delta_deg:.2f}° 过大，"
                        f"建议分步运动（<= {self.MAX_SINGLE_STEP_DEG:.0f}°）。"
                    )

        return True, "校验通过"
        
    def movej(self, joints_rad):
        self.last_error = ""
        if not self.connected:
            self.last_error = "机械臂未连接。"
            return False
        if len(joints_rad) != 6:
            self.last_error = "目标关节数量必须为 6。"
            return False
        j_arr = (ctypes.c_double * 6)(*joints_rad)
        # 阻塞模式执行
        ret = self.dll.rs_move_joint(self.rshd.value, j_arr, True)
        if ret != 0:
            self.last_error = f"SDK 返回错误码: {ret}（目标可能不可达或被控制器拒绝）"
            return False
        return True

    def movej_safe(self, joints_rad):
        current = self.get_waypoint()
        current_joints = list(current.jointpos) if current else None
        ok, msg = self.validate_joints(joints_rad, current_joints)
        if not ok:
            self.last_error = msg
            return False, msg

        success = self.movej(joints_rad)
        if not success:
            if self.last_error:
                return False, self.last_error
            return False, "MoveJ 执行失败，目标点位可能不可达。"
        return True, "MoveJ 执行成功。"

    def stop(self):
        if not self.connected:
            return False
        return self.dll.rs_move_stop(self.rshd.value) == 0

    def fast_stop(self):
        if not self.connected:
            return False
        return self.dll.rs_move_fast_stop(self.rshd.value) == 0

    def set_speed_percent(self, percent):
        percent = max(1, min(100, float(percent)))
        vel_deg = 30.0 * percent / 100.0
        acc_deg = vel_deg * 10.0
        max_vel = (ctypes.c_double * 6)(*[vel_deg * 3.1415926 / 180.0] * 6)
        max_acc = (ctypes.c_double * 6)(*[acc_deg * 3.1415926 / 180.0] * 6)
        self.dll.rs_set_global_joint_maxvelc(self.rshd.value, max_vel)
        self.dll.rs_set_global_joint_maxacc(self.rshd.value, max_acc)

    def __del__(self):
        self.disconnect()
        self.dll.rs_uninitialize()
