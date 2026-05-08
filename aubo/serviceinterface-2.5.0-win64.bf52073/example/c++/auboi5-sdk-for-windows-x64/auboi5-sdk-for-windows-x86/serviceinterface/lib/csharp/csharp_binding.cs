using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Threading.Tasks;


namespace auboi5_sdk_for_windows_x86_csharp {
    public class cSharpBinding {
        const string service_interface_dll = "serviceinterface2.dll";
        //关节个数
        const int ARM_DOF = 6;
        //M_PI
        const double M_PI = 3.14159265358979323846;
        //路点位置信息的表示方法
        [StructLayout (LayoutKind.Sequential)]
        public struct Pos {
            public double x;
            public double y;
            public double z;
        }

        //路点位置信息的表示方法
        [StructLayout (LayoutKind.Sequential)]
        public struct cartesianPos_U {
            // 指定数组尺寸
            [MarshalAs (UnmanagedType.ByValArray, SizeConst = 3)]
            public double[] positionVector;
        };

        //姿态的四元素表示方法
        [StructLayout (LayoutKind.Sequential)]
        public struct Ori {
            public double w;
            public double x;
            public double y;
            public double z;
        };

        //姿态的欧拉角表示方法
        [StructLayout (LayoutKind.Sequential)]
        public struct Rpy {
            public double rx;
            public double ry;
            public double rz;
        };

        //描述机械臂的路点信息
        [StructLayout (LayoutKind.Sequential)]
        public struct wayPoint_S {
            //机械臂的位置信息　X,Y,Z
            public Pos cartPos;
            //机械臂姿态信息
            public Ori orientation;
            //机械臂关节角信息
            [MarshalAs (UnmanagedType.ByValArray, SizeConst = ARM_DOF)]
            public double[] jointpos;
        };

        //机械臂关节速度加速度信息
        [StructLayout (LayoutKind.Sequential)]
        public struct JointVelcAccParam {
            [MarshalAs (UnmanagedType.ByValArray, SizeConst = ARM_DOF)]
            public double[] jointPara;
        };

        //机械臂关节角度
        [StructLayout (LayoutKind.Sequential)]
        public struct JointRadian {
            [MarshalAs (UnmanagedType.ByValArray, SizeConst = ARM_DOF)]
            public double[] jointRadian;
        };

        //机械臂工具端参数
        [StructLayout (LayoutKind.Sequential)]
        public struct ToolInEndDesc {
            //工具相对于末端坐标系的位置
            public Pos cartPos;
            //工具相对于末端坐标系的姿态
            public Ori orientation;
        };
        
        //坐标系结构体
        [StructLayout (LayoutKind.Sequential)]
        public struct CoordCalibrate {
            //坐标系类型：当coordType==BaseCoordinate或者coordType==EndCoordinate是，下面3个参数不做处理
            public int coordType;
            //坐标系标定方法
            public int methods;
            //用于标定坐标系的３个点（关节角），对应于机械臂法兰盘中心点基于基座标系
            [MarshalAs (UnmanagedType.ByValArray, SizeConst = 3)]
            public JointRadian[] jointPara;
            //标定的时候使用的工具描述
            public ToolInEndDesc toolDesc;
        };

        
        //工具标定结构体
        [StructLayout(LayoutKind.Sequential)]
        public struct ToolCalibrate
        {
            //用于位置标定点的数量
            public int posCalibrateNum ;           
            //位置标定点
            [MarshalAs(UnmanagedType.ByValArray, SizeConst = 4)]
            public wayPoint_S[] posCalibrateWaypoint;
            //用于姿态标定点的数量
            public int oriCalibrateNum;
            //姿态标定点
            [MarshalAs(UnmanagedType.ByValArray, SizeConst = 3)]
            public wayPoint_S[] oriCalibrateWaypoint;
            public int CalibMethod;
        };

        //转轴定义
        [StructLayout (LayoutKind.Sequential)]
        public struct MoveRotateAxis {
            [MarshalAs (UnmanagedType.ByValArray, SizeConst = 3)]
            public double[] rotateAxis;
        };

        //描述运动属性中的偏移属性
        [StructLayout (LayoutKind.Sequential)]
        public struct MoveRelative {
            //是否使能偏移
            public byte enable;
            //偏移量 x,y,z
            [MarshalAs (UnmanagedType.ByValArray, SizeConst = 3)]
            public float[] pos;
            //public Pos pos;
            //相对姿态偏移量
            public Ori orientation;
        };

        //该结构体描述工具惯量
        [StructLayout (LayoutKind.Sequential)]
        public struct ToolInertia {
            public double xx;
            public double xy;
            public double xz;
            public double yy;
            public double yz;
            public double zz;
        };

        //动力学参数
        [StructLayout (LayoutKind.Sequential)]
        public struct ToolDynamicsParam {
            public double positionX; //工具重心的X坐标
            public double positionY; //工具重心的Y坐标
            public double positionZ; //工具重心的Z坐标
            public double payload; //工具重量
            public ToolInertia toolInertia; //工具惯量
        };

        //机械臂事件
        [StructLayout (LayoutKind.Sequential)]
        public struct RobotEventInfo {
            public int eventType; //事件类型号
            public int eventCode; //事件代码
            public IntPtr eventContent; //事件内容(std::string)
        };

        //关节状态信息
        [StructLayout(LayoutKind.Sequential)]
        public struct JointStatus
        {
            public int jointCurrentI;       // 关节电流    Current of driver
            public int jointSpeedMoto;      // 关节速度    Speed of driver
            public float jointPosJ;           // 关节角      Current position in radian
            public float jointCurVol;         // 关节电压    Rated voltage of motor. Unit: mV
            public float jointCurTemp;        // 当前温度    Current temprature of joint
            public int jointTagCurrentI;    // 电机目标电流 Target current of motor
            public float jointTagSpeedMoto;   // 电机目标速度 Target speed of motor
            public float jointTagPosJ;        // 目标关节角　 Target position of joint in radian
            public short jointErrorNum;       // 关节错误码   Joint error of joint num
        };
        //机械臂诊断信息
        [StructLayout(LayoutKind.Sequential)]
        public struct RobotDiagnosis
        {
            public Byte armCanbusStatus;                // CAN通信状态:0x01~0x80：关节CAN通信错误（每个关节占用1bit） 0x00：无错误
            public float armPowerCurrent;                // 机械臂48V电源当前电流
            public float armPowerVoltage;                // 机械臂48V电源当前电压
            public Byte armPowerStatus;                 // 机械臂48V电源状态（开、关）
            public Byte contorllerTemp;                 // 控制箱温度
            public Byte contorllerHumidity;             // 控制箱湿度
            public Byte remoteHalt;                     // 远程关机信号
            public Byte softEmergency;                  // 机械臂软急停
            public Byte remoteEmergency;                // 远程急停信号
            public Byte robotCollision;                 // 碰撞检测位
            public Byte forceControlMode;               // 机械臂进入力控模式标志位
            public Byte brakeStuats;                    // 刹车状态
            public float robotEndSpeed;                  // 末端速度
            public int robotMaxAcc;                    // 最大加速度
            public Byte orpeStatus;                     // 上位机软件状态位
            public Byte enableReadPose;                 // 位姿读取使能位
            public Byte robotMountingPoseChanged;       // 安装位置状态
            public Byte encoderErrorStatus;             // 磁编码器错误状态
            public Byte staticCollisionDetect;          // 静止碰撞检测开关
            public Byte jointCollisionDetect;           // 关节碰撞检测 每个关节占用1bit 0-无碰撞 1-存在碰撞
            public Byte encoderLinesError;              // 光电编码器不一致错误 0-无错误 1-有错误
            public Byte jointErrorStatus;               // joint error status
            public Byte singularityOverSpeedAlarm;      // 机械臂奇异点过速警告
            public Byte robotCurrentAlarm;              // 机械臂电流错误警告
            public Byte toolIoError;                    // tool error
            public Byte robotMountingPoseWarning;       // 机械臂安装位置错位（只在力控模式下起作用）
            public ushort macTargetPosBufferSize;         // mac缓冲器长度          预留
            public ushort macTargetPosDataSize;           // mac缓冲器有效数据长度   预留
            public Byte macDataInterruptWarning;        // mac数据中断           预留
            public Byte controlBoardAbnormalStateFlag;  //主控板(接口板)异常状态标志
        };

        //关节版本信息
        [StructLayout(LayoutKind.Sequential)]
        public struct JointVersion
        {
            [MarshalAs(UnmanagedType.ByValArray, SizeConst = 8)]
            char[] hw_version;  //硬件版本信息
            [MarshalAs(UnmanagedType.ByValArray, SizeConst = 16)]
            char[] sw_version; //固件版本信息

        };

        //机械臂ID信息
        [StructLayout(LayoutKind.Sequential)]
        public struct JointProductID
        {
            
            [MarshalAs(UnmanagedType.ByValArray, SizeConst = 16)]
            char[] productID;

        };

        //设备信息
        [StructLayout(LayoutKind.Sequential)]
        public struct RobotDevInfo
        {
            Byte type;                       // 设备型号、芯片型号：上位机主站：0x01  接口板0x02
            [MarshalAs(UnmanagedType.ByValArray, SizeConst = 16)]
            char[] revision;                // 设备版本号，eg:V1.0
            [MarshalAs(UnmanagedType.ByValArray, SizeConst = 16)]
            char[] manu_id;                 // 厂家ID，"OUR "的ASCII码0x4F 55 52 00
            [MarshalAs(UnmanagedType.ByValArray, SizeConst = 16)]
            char[] joint_type;              // 机械臂类型
            [MarshalAs(UnmanagedType.ByValArray, SizeConst = 8)]
            JointVersion[] joint_ver;        // 机械臂关节及工具端信息
            [MarshalAs(UnmanagedType.ByValArray, SizeConst = 64)]
            char[] desc;                    // 设备描述字符串以0x00结束
            [MarshalAs(UnmanagedType.ByValArray, SizeConst = 8)]
            JointProductID[] jointProductID; // 关节ID信息
            [MarshalAs(UnmanagedType.ByValArray, SizeConst = 16)]
            char[] slave_version;           // 从设备版本号 - 字符串表示，如“V1.0.0
            [MarshalAs(UnmanagedType.ByValArray, SizeConst = 16)]
            char[] extio_version;           // IO扩展板版本号 -字符串标志，如“V1.0.0

        };

        //初始化机械臂控制库
        [DllImport (service_interface_dll, EntryPoint = "rs_initialize", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_initialize ();

        //反初始化机械臂控制库
        [DllImport (service_interface_dll, EntryPoint = "rs_uninitialize", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_uninitialize ();

        //创建机械臂控制上下文句柄
        [DllImport (service_interface_dll, EntryPoint = "rs_create_context", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_create_context (ref UInt16 rshd);

        //注销机械臂控制上下文句柄
        [DllImport (service_interface_dll, EntryPoint = "rs_destory_context", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_destory_context (UInt16 rshd);

        //链接机械臂服务器
        [DllImport (service_interface_dll, EntryPoint = "rs_login", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_login (UInt16 rshd, [MarshalAs (UnmanagedType.LPStr)] string addr, int port);

        //断开机械臂服务器链接
        [DllImport (service_interface_dll, EntryPoint = "rs_logout", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_logout (UInt16 rshd);
        
        //初始化全局的运动属性
        [DllImport (service_interface_dll, EntryPoint = "rs_init_global_move_profile", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_init_global_move_profile (UInt16 rshd);

        //设置六个关节轴动的最大速度（最大为180度/秒），注意如果没有特殊需求，6个关节尽量配置成一样！
        [DllImport (service_interface_dll, EntryPoint = "rs_set_global_joint_maxvelc", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_set_global_joint_maxvelc (UInt16 rshd, double[] max_velc);

        //获取六个关节轴动的最大速度
        [DllImport (service_interface_dll, EntryPoint = "rs_get_global_joint_maxvelc", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_get_global_joint_maxvelc (UInt16 rshd, ref JointVelcAccParam max_velc);

        //设置六个关节轴动的最大加速度 （十倍的最大速度），注意如果没有特殊需求，6个关节尽量配置成一样！
        [DllImport (service_interface_dll, EntryPoint = "rs_set_global_joint_maxacc", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_set_global_joint_maxacc (UInt16 rshd, double[] max_acc);

        //获取六个关节轴动的最大加速度
        [DllImport (service_interface_dll, EntryPoint = "rs_get_global_joint_maxacc", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_get_global_joint_maxacc (UInt16 rshd, ref JointVelcAccParam max_acc);

        //设置机械臂末端最大线加速度
        [DllImport (service_interface_dll, EntryPoint = "rs_set_global_end_max_line_acc", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_set_global_end_max_line_acc (UInt16 rshd, double max_acc);

        //设置机械臂末端最大线速度
        [DllImport (service_interface_dll, EntryPoint = "rs_set_global_end_max_line_velc", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_set_global_end_max_line_velc (UInt16 rshd, double max_velc);

        //获取机械臂末端最大线加速度
        [DllImport (service_interface_dll, EntryPoint = "rs_get_global_end_max_line_acc", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_get_global_end_max_line_acc (UInt16 rshd, ref double max_acc);

        //获取机械臂末端最大线速度
        [DllImport (service_interface_dll, EntryPoint = "rs_get_global_end_max_line_velc", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_get_global_end_max_line_velc (UInt16 rshd, ref double max_velc);

        //设置机械臂末端最大角加速度
        [DllImport (service_interface_dll, EntryPoint = "rs_set_global_end_max_angle_acc", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_set_global_end_max_angle_acc (UInt16 rshd, double max_acc);

        //设置机械臂末端最大角速度
        [DllImport (service_interface_dll, EntryPoint = "rs_set_global_end_max_angle_velc", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_set_global_end_max_angle_velc (UInt16 rshd, double max_velc);

        //获取机械臂末端最大角加速度
        [DllImport (service_interface_dll, EntryPoint = "rs_get_global_end_max_angle_acc", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_get_global_end_max_angle_acc (UInt16 rshd, ref double max_acc);

        //获取机械臂末端最大角加速度
        [DllImport (service_interface_dll, EntryPoint = "rs_get_global_end_max_angle_velc", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_get_global_end_max_angle_velc (UInt16 rshd, ref double max_velc);

        //设置用户坐标系
        [DllImport (service_interface_dll, EntryPoint = "rs_set_user_coord", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_set_user_coord (UInt16 rshd, ref CoordCalibrate user_coord);

        //设置基座坐标系
        [DllImport (service_interface_dll, EntryPoint = "rs_set_base_coord", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_set_base_coord (UInt16 rshd);

        //机械臂轴动
        [DllImport (service_interface_dll, EntryPoint = "rs_move_joint", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_move_joint (UInt16 rshd, double[] joint_radia, bool isblock);

        //机械臂直线运动
        [DllImport (service_interface_dll, EntryPoint = "rs_move_line", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_move_line (UInt16 rshd, double[] joint_radia, bool isblock);

        //机械臂直线运动
        [DllImport(service_interface_dll, EntryPoint = "rs_move_rotate_to_waypoint", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_move_rotate_to_waypoint(UInt16 rshd,ref wayPoint_S target_waypoint, bool isblock);

        //保持当前位置变换姿态做旋转运动
        [DllImport (service_interface_dll, EntryPoint = "rs_move_rotate", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_move_rotate (UInt16 rshd, ref CoordCalibrate user_coord, ref MoveRotateAxis rotate_axis, double rotate_angle, bool isblock);

        //根据当前路点信息获取姿态旋转变换目标路点
        [DllImport(service_interface_dll, EntryPoint = "rs_get_rotate_target_waypiont", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_get_rotate_target_waypiont(UInt16 rshd,ref wayPoint_S source_waypoint,double[] rotate_axis_on_basecoord, double rotate_angle, ref wayPoint_S target_waypoint);

        //将用户坐标系下描述的坐标轴变换到基坐标系下描述
        [DllImport(service_interface_dll, EntryPoint = "rs_get_rotateaxis_user_to_Base", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_get_rotateaxis_user_to_Base(UInt16 rshd,ref Ori ori_usercoord, double[] rotate_axis_on_usercoord, double[] rotate_axis_on_basecoord);

        //根据位置获取目标路点信息(获取基于基座标下的目标路点通过基于用户坐标系的位置，目标路点保持起点姿态)
        [DllImport(service_interface_dll, EntryPoint = "rs_get_target_waypoint_by_position", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_get_target_waypoint_by_position(UInt16 rshd, ref wayPoint_S source_waypoint_on_basecoord,ref CoordCalibrate usercoord, ref Pos tool_End_Position, ref ToolInEndDesc toolInEndDesc, ref wayPoint_S target_waypoint_on_basecoord);
        
        //清除所有已经设置的全局路点
        [DllImport (service_interface_dll, EntryPoint = "rs_remove_all_waypoint", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_remove_all_waypoint (UInt16 rshd);

        //添加全局路点用于轨迹运动
        [DllImport (service_interface_dll, EntryPoint = "rs_add_waypoint", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_add_waypoint (UInt16 rshd, double[] joint_radia);

        //设置交融半径
        [DllImport (service_interface_dll, EntryPoint = "rs_set_blend_radius", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_set_blend_radius (UInt16 rshd, double radius);

        //设置圆运动圈数
        [DllImport (service_interface_dll, EntryPoint = "rs_set_circular_loop_times", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_set_circular_loop_times (UInt16 rshd, int times);

        //检查用户坐标系参数设置是否合理
        [DllImport (service_interface_dll, EntryPoint = "rs_check_user_coord", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_check_user_coord (UInt16 rshd, ref CoordCalibrate user_coord);
        
        //用户坐标系标定
        [DllImport(service_interface_dll, EntryPoint = "rs_user_coord_calibrate", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_user_coord_calibrate(UInt16 rshd, ref CoordCalibrate user_coord, double[] bInWPos, double[] bInWOri, double[] wInBPos);

        //工具标定
        [DllImport(service_interface_dll, EntryPoint = "rs_tool_calibration", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_tool_calibration(UInt16 rshd, ref ToolCalibrate toolCalibrate, ref ToolInEndDesc toolInEndDesc);

        //设置基于基座标系运动偏移量
        [DllImport (service_interface_dll, EntryPoint = "rs_set_relative_offset_on_base", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_set_relative_offset_on_base (UInt16 rshd, ref MoveRelative relative);

        //设置基于用户标系运动偏移量
        [DllImport (service_interface_dll, EntryPoint = "rs_set_relative_offset_on_user", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_set_relative_offset_on_user (UInt16 rshd, ref MoveRelative relative, ref CoordCalibrate user_coord);

        //取消提前到位设置
        [DllImport (service_interface_dll, EntryPoint = "rs_set_no_arrival_ahead", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_set_no_arrival_ahead (UInt16 rshd);

        //设置距离模式下的提前到位距离
        [DllImport (service_interface_dll, EntryPoint = "rs_set_arrival_ahead_distance", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_set_arrival_ahead_distance (UInt16 rshd, double distance);

        //设置时间模式下的提前到位时间
        [DllImport (service_interface_dll, EntryPoint = "rs_set_arrival_ahead_time", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_set_arrival_ahead_time (UInt16 rshd, double sec);

        //轨迹运动
        [DllImport (service_interface_dll, EntryPoint = "rs_move_track", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_move_track (UInt16 rshd, int sub_move_mode, bool isblock);

        //保持当前位姿通过直线运动的方式运动到目标位置
        [DllImport (service_interface_dll, EntryPoint = "rs_move_line_to", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_move_line_to (UInt16 rshd, ref Pos target, ref ToolInEndDesc tool, bool isblock);

        //保持当前位姿通过关节运动的方式运动到目标位置
        [DllImport (service_interface_dll, EntryPoint = "rs_move_joint_to", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_move_joint_to (UInt16 rshd, ref Pos target, ref ToolInEndDesc tool, bool isblock);

        //获取机械臂当前位置信息
        [DllImport (service_interface_dll, EntryPoint = "rs_get_current_waypoint", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_get_current_waypoint (UInt16 rshd, ref wayPoint_S waypoint);

        //正解
        [DllImport (service_interface_dll, EntryPoint = "rs_forward_kin", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_forward_kin (UInt16 rshd, double[] joint_radia, ref wayPoint_S waypoint);

        //逆解
        [DllImport (service_interface_dll, EntryPoint = "rs_inverse_kin", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_inverse_kin (UInt16 rshd, double[] joint_radia, ref Pos pos, ref Ori ori, ref wayPoint_S waypoint);

        //四元素转欧拉角
        [DllImport (service_interface_dll, EntryPoint = "rs_rpy_to_quaternion", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_rpy_to_quaternion (UInt16 rshd, ref Rpy rpy, ref Ori ori);

        //欧拉角转四元素
        [DllImport (service_interface_dll, EntryPoint = "rs_quaternion_to_rpy", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_quaternion_to_rpy (UInt16 rshd, ref Ori ori, ref Rpy rpy);

        //基座坐标系转用户坐标系
        [DllImport (service_interface_dll, EntryPoint = "rs_base_to_user", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_base_to_user (UInt16 rshd, ref Pos pos_onbase, ref Ori ori_onbase, ref CoordCalibrate user_coord, ref ToolInEndDesc tool_pos, ref Pos pos_onuser, ref Ori ori_onuser);

        //用户坐标系转基座坐标系
        [DllImport (service_interface_dll, EntryPoint = "rs_user_to_base", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_user_to_base (UInt16 rshd, ref Pos pos_onuser, ref Ori ori_onuser, ref CoordCalibrate user_coord, ref ToolInEndDesc tool_pos, ref Pos pos_onbase, ref Ori ori_onbase);

        //基坐标系转基座标得到工具末端点的位置和姿态
        [DllImport (service_interface_dll, EntryPoint = "rs_base_to_base_additional_tool", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_base_to_base_additional_tool (UInt16 rshd, ref Pos flange_center_pos_onbase, ref Ori flange_center_ori_onbase, ref ToolInEndDesc tool_pos, ref Pos tool_end_pos_onbase, ref Ori tool_end_ori_onbase);

        //设置工具的运动学参数
        [DllImport (service_interface_dll, EntryPoint = "rs_set_tool_end_param", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_set_tool_end_param (UInt16 rshd, ref ToolInEndDesc tool);

        //设置无工具的动力学参数
        [DllImport (service_interface_dll, EntryPoint = "rs_set_none_tool_dynamics_param", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_set_none_tool_dynamics_param (UInt16 rshd);

        //根据接口板IO类型和地址设置IO状态
        [DllImport (service_interface_dll, EntryPoint = "rs_set_board_io_status_by_addr", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_set_board_io_status_by_addr (UInt16 rshd, int io_type, int addr, double val);

        //根据接口板IO类型和地址获取IO状态
        [DllImport (service_interface_dll, EntryPoint = "rs_get_board_io_status_by_addr", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_get_board_io_status_by_addr (UInt16 rshd, int io_type, int addr, ref double val);

        //设置工具端IO状态
        [DllImport (service_interface_dll, EntryPoint = "rs_set_tool_do_status", CharSet = CharSet.Ansi, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_set_tool_do_status (UInt16 rshd, string name, int val);

        //获取工具端IO状态
        [DllImport (service_interface_dll, EntryPoint = "rs_get_tool_io_status", CharSet = CharSet.Ansi, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_get_tool_io_status (UInt16 rshd, string name, ref double val);

        //设置工具端电源电压类型
        [DllImport (service_interface_dll, EntryPoint = "rs_set_tool_power_type", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_set_tool_power_type (UInt16 rshd, int type);

        //获取工具端电源电压类型
        [DllImport (service_interface_dll, EntryPoint = "rs_get_tool_power_type", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_get_tool_power_type (UInt16 rshd, ref int type);

        //设置工具端数字量IO的类型
        [DllImport (service_interface_dll, EntryPoint = "rs_set_tool_io_type", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_set_tool_io_type (UInt16 rshd, int addr, int type);

        //设置工具的动力学参数
        [DllImport (service_interface_dll, EntryPoint = "rs_set_tool_dynamics_param", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_set_tool_dynamics_param (UInt16 rshd, ref ToolDynamicsParam tool);

        //获取工具的动力学参数
        [DllImport (service_interface_dll, EntryPoint = "rs_get_tool_dynamics_param", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_get_tool_dynamics_param (UInt16 rshd, ref ToolDynamicsParam tool);

        //设置无工具运动学参数
        [DllImport (service_interface_dll, EntryPoint = "rs_set_none_tool_kinematics_param", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_set_none_tool_kinematics_param (UInt16 rshd);

        //设置工具的运动学参数
        [DllImport (service_interface_dll, EntryPoint = "rs_set_tool_kinematics_param", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_set_tool_kinematics_param (UInt16 rshd, ref ToolInEndDesc tool);

        //获取工具的运动学参数
        [DllImport (service_interface_dll, EntryPoint = "rs_get_tool_kinematics_param", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_get_tool_kinematics_param (UInt16 rshd, ref ToolInEndDesc tool);

        //启动机械臂
        [DllImport (service_interface_dll, EntryPoint = "rs_robot_startup", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_robot_startup (UInt16 rshd, ref ToolDynamicsParam tool, byte colli_class, bool read_pos, bool static_colli_detect, int board_maxacc, ref int state);

        //关闭机械臂
        [DllImport (service_interface_dll, EntryPoint = "rs_robot_shutdown", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_robot_shutdown (UInt16 rshd);

        //停止机械臂运动
        [DllImport (service_interface_dll, EntryPoint = "rs_move_stop", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_move_stop (UInt16 rshd);

        //停止机械臂运动
        [DllImport (service_interface_dll, EntryPoint = "rs_move_fast_stop", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_move_fast_stop (UInt16 rshd);

        //暂停机械臂运动
        [DllImport (service_interface_dll, EntryPoint = "rs_move_pause", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_move_pause (UInt16 rshd);

        //暂停后回复机械臂运动
        [DllImport (service_interface_dll, EntryPoint = "rs_move_continue", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_move_continue (UInt16 rshd);

        //机械臂碰撞后恢复
        [DllImport (service_interface_dll, EntryPoint = "rs_collision_recover", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_collision_recover (UInt16 rshd);

        //获取机械臂当前状态
        [DllImport (service_interface_dll, EntryPoint = "rs_get_robot_state", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_get_robot_state (UInt16 rshd, ref int state);

        //获取关节状态信息
        [DllImport(service_interface_dll, EntryPoint = "rs_get_joint_status", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_get_joint_status(UInt16 rshd, IntPtr pBuff);

        //获取机械臂诊断信息
        [DllImport(service_interface_dll, EntryPoint = "rs_get_diagnosis_info", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_get_diagnosis_info(UInt16 rshd, ref RobotDiagnosis robotDiagnosis);

        //获取机械臂诊断信息
        [DllImport(service_interface_dll, EntryPoint = "rs_get_device_info", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_get_device_info(UInt16 rshd, ref RobotDevInfo dev);

        //设置机械臂服务器工作模式
        [DllImport (service_interface_dll, EntryPoint = "rs_set_work_mode", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_set_work_mode (UInt16 rshd, int state);

        //获取机械臂服务器当前工作模式
        [DllImport (service_interface_dll, EntryPoint = "rs_get_work_mode", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_get_work_mode (UInt16 rshd, ref int state);

        //设置机械臂碰撞等级
        [DllImport (service_interface_dll, EntryPoint = "rs_set_collision_class", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_set_collision_class (UInt16 rshd, int grade);
        
        //获取当前碰撞等级
        [DllImport(service_interface_dll, EntryPoint = "rs_get_collision_class", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_get_collision_class(UInt16 rshd, ref int grade);
       
        //根据错误号返回错误信息
        [DllImport(service_interface_dll, EntryPoint = "rs_get_error_information_by_errcode", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern IntPtr rs_get_error_information_by_errcode(UInt16 rshd, int err_code);

        //获取socket链接状态
        [DllImport (service_interface_dll, EntryPoint = "rs_get_socket_status", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_get_socket_status (UInt16 rshd, ref byte connected);

        //设置是否允许实时路点信息推送
        [DllImport (service_interface_dll, EntryPoint = "rs_enable_push_realtime_roadpoint", CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl)]
        public static extern int rs_enable_push_realtime_roadpoint (UInt16 rshd, bool enable);

        //实时路点回调函数
        [System.Runtime.InteropServices.UnmanagedFunctionPointerAttribute (System.Runtime.InteropServices.CallingConvention.Cdecl)]
        public delegate void REALTIME_ROADPOINT_CALLBACK (ref wayPoint_S waypoint, IntPtr arg);

        [DllImport (service_interface_dll, CallingConvention = CallingConvention.Cdecl)]
        public static extern void rs_setcallback_realtime_roadpoint (UInt16 rshd, [MarshalAs (UnmanagedType.FunctionPtr)] REALTIME_ROADPOINT_CALLBACK CurrentPositionCallback, IntPtr arg);

        //实时末端速度回调函数
        [System.Runtime.InteropServices.UnmanagedFunctionPointerAttribute(System.Runtime.InteropServices.CallingConvention.Cdecl)]
        public delegate void REALTIME_ENDSPEED_CALLBACK(double speed, IntPtr arg);

        [DllImport(service_interface_dll, CallingConvention = CallingConvention.Cdecl)]
        public static extern void rs_setcallback_realtime_end_speed(UInt16 rshd, [MarshalAs(UnmanagedType.FunctionPtr)] REALTIME_ENDSPEED_CALLBACK CurrentEndSpeedCallback, IntPtr arg);


        //机械臂事件回调
        [System.Runtime.InteropServices.UnmanagedFunctionPointerAttribute (System.Runtime.InteropServices.CallingConvention.Cdecl)]
        public delegate void ROBOT_EVENT_CALLBACK (ref RobotEventInfo rs_event, IntPtr arg);

        [DllImport (service_interface_dll, CallingConvention = CallingConvention.Cdecl)]
        public static extern void rs_setcallback_robot_event (UInt16 rshd, [MarshalAs (UnmanagedType.FunctionPtr)] ROBOT_EVENT_CALLBACK RobotEventCallback, IntPtr arg);

        //机械臂关节状态回调
        [System.Runtime.InteropServices.UnmanagedFunctionPointerAttribute(System.Runtime.InteropServices.CallingConvention.Cdecl)]
        public delegate void ROBOT_JOINT_STATUS_CALLBACK(IntPtr pBuff, int size ,IntPtr arg);

        [DllImport(service_interface_dll, CallingConvention = CallingConvention.Cdecl)]
        public static extern void rs_setcallback_realtime_joint_status(UInt16 rshd, [MarshalAs(UnmanagedType.FunctionPtr)] ROBOT_JOINT_STATUS_CALLBACK RobotJointStatusCallback, IntPtr arg);


        //位置回调
        public static void CurrentPositionCallback (ref wayPoint_S waypoint, IntPtr arg) {
            PrintWaypoint (waypoint);
        }
        //速度回调
        public static void CurrentEndSpeedCallback(double speed, IntPtr arg)
        {
            Console.Out.WriteLine("CurrentSpeed:{0}\n",speed);
        }

        
        //关节状态回调
        public static void CurrentJointStatusCallback(IntPtr pBuff, int size, IntPtr arg)
        {
            cSharpBinding.JointStatus[] jointStatus = new cSharpBinding.JointStatus[6];
            for (int i = 0; i < 6; i++)
            {
                IntPtr pPonitor = new IntPtr(pBuff.ToInt64() + Marshal.SizeOf(typeof(cSharpBinding.JointStatus)) * i);
                jointStatus[i] = (cSharpBinding.JointStatus)Marshal.PtrToStructure(pPonitor, typeof(cSharpBinding.JointStatus));
            }
            for (int i = 0; i < 6; i++)
            {
                Console.Out.WriteLine("jointStatus {0}", i + 1);
                Console.Out.WriteLine("joint I: {0}\njoint Speed: {1}\njoint Angel: {2}", jointStatus[i].jointCurrentI, jointStatus[i].jointSpeedMoto, jointStatus[i].jointPosJ);
                Console.Out.WriteLine("joint vol: {0}\njoint temp: {1}\njoint target I: {2}", jointStatus[i].jointCurVol, jointStatus[i].jointCurTemp, jointStatus[i].jointTagCurrentI);
                Console.Out.WriteLine("joint target Speed: {0}\njoint Target Angel: {1}\njoint Errnum: {2}", jointStatus[i].jointTagSpeedMoto, jointStatus[i].jointTagPosJ, jointStatus[i].jointErrorNum);
                Console.Out.WriteLine("---------------------------------------------------------------------------------------");

            }

        }


        //打印路点信息
        public static void PrintWaypoint (wayPoint_S point) {
            Console.Out.WriteLine ("---------------------------------------------------------------------------------------");
            Console.Out.WriteLine ("pos.x={0} y={1} z={2}", point.cartPos.x, point.cartPos.y, point.cartPos.z);
            Console.Out.WriteLine ("ori.w={0} x={1} y={2} z={3}", point.orientation.w, point.orientation.x, point.orientation.y, point.orientation.z);
            Console.Out.WriteLine ("joint1={0} joint2={1} joint3={2}", point.jointpos[0] * 180 / M_PI, point.jointpos[1] * 180 / M_PI, point.jointpos[2] * 180 / M_PI);
            Console.Out.WriteLine ("joint4={0} joint5={1} joint6={2}", point.jointpos[3] * 180 / M_PI, point.jointpos[4] * 180 / M_PI, point.jointpos[5] * 180 / M_PI);
            Console.Out.WriteLine ("---------------------------------------------------------------------------------------");
        }

        public static void RobotEventCallback (ref RobotEventInfo rs_event, IntPtr arg) {
            Console.Out.WriteLine ("---------------------------------------------------------------------------------------");
            Console.Out.WriteLine ("robot event.type={0}", rs_event.eventType);
            Console.Out.WriteLine ("robot event.eventCode={0}", rs_event.eventCode);
            Console.Out.WriteLine ("robot event.eventContent={0}", Marshal.PtrToStringAnsi (rs_event.eventContent));
            Console.Out.WriteLine ("---------------------------------------------------------------------------------------");
        }

    }
}