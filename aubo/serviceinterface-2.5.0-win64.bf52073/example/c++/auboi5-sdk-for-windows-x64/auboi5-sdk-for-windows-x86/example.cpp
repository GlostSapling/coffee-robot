//#include "stdafx.h"
#include "example.h"

#include <Windows.h>   
#include <iostream>  
#include <fstream>
#include <sstream> 
#include <string> 
#include <algorithm>


#define M_PI 3.14159265358979323846

//控制柜用户ＤＩ名称
const char* USER_DI_00 = "U_DI_00";
const char* USER_DI_01 = "U_DI_01";
const char* USER_DI_02 = "U_DI_02";
const char* USER_DI_03 = "U_DI_03";
const char* USER_DI_04 = "U_DI_04";
const char* USER_DI_05 = "U_DI_05";
const char* USER_DI_06 = "U_DI_06";
const char* USER_DI_07 = "U_DI_07";
const char* USER_DI_10 = "U_DI_10";
const char* USER_DI_11 = "U_DI_11";
const char* USER_DI_12 = "U_DI_12";
const char* USER_DI_13 = "U_DI_13";
const char* USER_DI_14 = "U_DI_14";
const char* USER_DI_15 = "U_DI_15";
const char* USER_DI_16 = "U_DI_16";
const char* USER_DI_17 = "U_DI_17";

//控制柜用户ＤＯ名称
const char* USER_DO_00 = "U_DO_00";
const char* USER_DO_01 = "U_DO_01";
const char* USER_DO_02 = "U_DO_02";
const char* USER_DO_03 = "U_DO_03";
const char* USER_DO_04 = "U_DO_04";
const char* USER_DO_05 = "U_DO_05";
const char* USER_DO_06 = "U_DO_06";
const char* USER_DO_07 = "U_DO_07";
const char* USER_DO_10 = "U_DO_10";
const char* USER_DO_11 = "U_DO_11";
const char* USER_DO_12 = "U_DO_12";
const char* USER_DO_13 = "U_DO_13";
const char* USER_DO_14 = "U_DO_14";
const char* USER_DO_15 = "U_DO_15";
const char* USER_DO_16 = "U_DO_16";
const char* USER_DO_17 = "U_DO_17";

const char* TOOL_IO_0 = "T_DI/O_00";
const char* TOOL_IO_1 = "T_DI/O_01"	;
const char* TOOL_IO_2 = "T_DI/O_02"	;
const char* TOOL_IO_3 = "T_DI/O_03"	;


void printRoadPoint(const aubo_robot_namespace::wayPoint_S  *wayPoint)
{
	std::cout << "--------------------------------------------------------------------------------------\n";
	std::cout<<"pos.x="<<wayPoint->cartPos.position.x<<"   ";
	std::cout<<"pos.y="<<wayPoint->cartPos.position.y<< "   ";;
	std::cout<<"pos.z="<<wayPoint->cartPos.position.z<<std::endl;

	std::cout<<"ori.w="<<wayPoint->orientation.w<< "   ";
	std::cout<<"ori.x="<<wayPoint->orientation.x<< "   ";
	std::cout<<"ori.y="<<wayPoint->orientation.y<< "   ";
	std::cout<<"ori.z="<<wayPoint->orientation.z<<std::endl;

	std::cout<<"joint_1="<<wayPoint->jointpos[0]*180.0/M_PI<< "   ";
	std::cout<<"joint_2="<<wayPoint->jointpos[1]*180.0/M_PI<< "   ";
	std::cout<<"joint_3="<<wayPoint->jointpos[2]*180.0/M_PI<< "   ";
	std::cout<<"joint_4="<<wayPoint->jointpos[3]*180.0/M_PI<< "   ";
	std::cout<<"joint_5="<<wayPoint->jointpos[4]*180.0/M_PI<< "   ";
	std::cout<<"joint_6="<<wayPoint->jointpos[5]*180.0/M_PI<<std::endl;
	std::cout << "--------------------------------------------------------------------------------------\n";
}

void callback_RealTimeRoadPoint(const aubo_robot_namespace::wayPoint_S  *wayPoint, void *arg)
{
	printRoadPoint(wayPoint);
}

/************************************************************************/
/* 
   pos 目标位置x,y,z 单位米
   joint6Angle 6轴角度(度)
*/
/************************************************************************/
bool move_to(RSHD rshd, const Pos *pos, double joint6Angle)
{
	bool result = false;

	//首先获取当前路点信息
	aubo_robot_namespace::wayPoint_S wayPoint;

	//逆解位置信息
	aubo_robot_namespace::wayPoint_S targetPoint;

	//目标位置对应的关节角
	double targetRadian[ARM_DOF] = {0};
	
	if (RS_SUCC == rs_get_current_waypoint(rshd, &wayPoint))
	{
		//参考当前姿态逆解得到六个关节角
		if (RS_SUCC == rs_inverse_kin(rshd, wayPoint.jointpos, pos, &wayPoint.orientation, &targetPoint))
		{
			//将得到目标位置,将6关节角度设置为用户给定的角度（必须在+-175度）
			targetRadian[0] = targetPoint.jointpos[0];
			targetRadian[1] = targetPoint.jointpos[1];
			targetRadian[2] = targetPoint.jointpos[2];
			targetRadian[3] = targetPoint.jointpos[3];
			targetRadian[4] = targetPoint.jointpos[4];
			//6轴使用用户给定的关节角度
			targetRadian[5] = joint6Angle/180*M_PI;

			//轴动到目标位置
			if (RS_SUCC == rs_move_joint(rshd, targetRadian))
			{
				std::cout<<"到达目标位置"<<std::endl;

				//获取当前关节角，进行验证
				rs_get_current_waypoint(rshd, &wayPoint);

				printRoadPoint(&wayPoint);
			}
			else
			{
				std::cerr<<"move joint error"<<std::endl;
			}
		}
		else
		{
			std::cerr<<"ik failed"<<std::endl;
		}

	}
	else
	{
		std::cerr<<"get current waypoint error"<<std::endl;
	}

	return result;
}

/********************************************************************
	function:	example_login
	purpose :	登陆机械臂
	param   :	rshd 输出上下文句柄
				addr 机械臂服务器地址
				port 机械臂服务器端口
	return  :	true 成功 false 失败
*********************************************************************/
bool example_login(RSHD &rshd, const char * addr, int port)
{
	bool result = false;

	rshd = RS_FAILED;

	//初始化接口库
	if (rs_initialize() == RS_SUCC)
	{
		//创建上下文
		if (rs_create_context(&rshd)  == RS_SUCC )
		{
			//登陆机械臂服务器
			if (rs_login(rshd, addr, port) == RS_SUCC)
			{
				result = true;
				//登陆成功
				std::cout<<"login succ"<<std::endl;
			}
			else
			{
				//登陆失败
				std::cerr<<"login failed"<<std::endl;				
			}
		}
		else
		{
			//创建上下文失败
			std::cerr<<"rs_create_context error"<<std::endl;
		}
	}
	else
	{
		//初始化接口库失败
		std::cerr<<"rs_initialize error"<<std::endl;
	}

	return result;
}

/********************************************************************
	function:	example_logout
	purpose :	退出登陆
	param   :	rshd 上下文句柄
					
	return  :	true 成功 false 失败
*********************************************************************/
bool example_logout(RSHD rshd)
{
	return rs_logout(rshd)==RS_SUCC ? true : false;
}

/********************************************************************
	function:	example_robotStartup
	purpose :	启动机械臂(必须连接真实机械臂）
	param   :	rshd 上下文句柄
					
	return  :	true 成功 false 失败
*********************************************************************/
bool example_robotStartup(RSHD rshd)
{
	bool result = false;

	//工具的动力学参数和运动学参数
	ToolDynamicsParam tool_dynamics = {0};
	//机械臂碰撞等级
	uint8 colli_class = 6;
	//机械臂启动是否读取姿态（默认开启）
	bool read_pos = true;
	//机械臂静态碰撞检测（默认开启）
	bool static_colli_detect = true;
	//机械臂最大加速度（系统自动控制，默认为30000)
	int board_maxacc = 30000;
	//机械臂服务启动状态
	ROBOT_SERVICE_STATE state = ROBOT_SERVICE_READY;

	if (rs_robot_startup(rshd, &tool_dynamics, colli_class, read_pos, static_colli_detect, board_maxacc, &state)
		== RS_SUCC)
	{
		result = true;
		std::cout<<"call robot startup succ, robot state:"<<state<<std::endl;
	}
	else
	{
		std::cerr<<"robot startup failed"<<std::endl;
	}

	return result;
}

/********************************************************************
	function:	example_robotShutdown
	purpose :	关闭机械臂（必须连接真实机械臂）
	param   :	rshd 上下文句柄
					
	return  :	true 成功 false 失败
*********************************************************************/
bool example_robotShutdown(RSHD rshd)
{
	return rs_robot_shutdown(rshd)==RS_SUCC ? true : false;
}

/********************************************************************
	function:	example_moveJ
	purpose :	机械臂轴动测试
	param   :	rshd 上下文句柄
					
	return  :	true 成功 false 失败
*********************************************************************/
bool example_moveJ(RSHD rshd)
{
	bool result = false;

	//该位置为机械臂的初始位置（提供6个关节角的关节信息（单位：弧度））
	double initPos[6]={
		-0.000172/180*M_PI,
		-7.291862/180*M_PI,
		-75.694718/180*M_PI,
		21.596727/180*M_PI,
		-89.999982/180*M_PI,
		-0.00458/180*M_PI};

	//首先运动到初始位置
	if (rs_move_joint(rshd, initPos) == RS_SUCC)
	{
		result = true;
		std::cout<<"movej succ"<<std::endl;
	}
	else
	{
		std::cerr<<"movej failed!"<<std::endl;
	}

	return result;
}

/********************************************************************
	function:	example_moveL
	purpose :	机械臂保持当前姿态直线运动测试
	param   :	rshd 上下文句柄
					
	return  :	true 成功 false 失败
*********************************************************************/
bool example_moveL(RSHD rshd)
{
	bool result = false;

	//首先移动到初始位置
	example_moveJ(rshd);

	//获取当前路点信息
	aubo_robot_namespace::wayPoint_S wayPoint;

	//逆解位置信息
	aubo_robot_namespace::wayPoint_S targetPoint;

	//目标位置对应的关节角
	double targetRadian[ARM_DOF] = {0};

	//目标位置
	Pos pos = {-0.489605, -0.155672, 0.448430};

	if (RS_SUCC == rs_get_current_waypoint(rshd, &wayPoint))
	{
		//参考当前姿态逆解得到六个关节角
		if (RS_SUCC == rs_inverse_kin(rshd, wayPoint.jointpos, &pos, &wayPoint.orientation, &targetPoint))
		{
			//将得到目标位置,将6关节角度设置为用户给定的角度（必须在+-175度）
			targetRadian[0] = targetPoint.jointpos[0];
			targetRadian[1] = targetPoint.jointpos[1];
			targetRadian[2] = targetPoint.jointpos[2];
			targetRadian[3] = targetPoint.jointpos[3];
			targetRadian[4] = targetPoint.jointpos[4];
			targetRadian[5] = targetPoint.jointpos[5];

			//轴动到目标位置
			if (RS_SUCC == rs_move_line(rshd, targetRadian))
			{
				std::cout<<"at target"<<std::endl;
			}
			else
			{
				std::cerr<<"move joint error"<<std::endl;
			}
			
		}
		else
		{
			std::cerr<<"ik failed"<<std::endl;
		}

	}
	else
	{
		std::cerr<<"get current waypoint error"<<std::endl;
	}


	return result;
}

/********************************************************************
	function:	example_moveP
	purpose :	机械臂轨迹运动测试
	param   :	rshd 上下文句柄
					
	return  :	void
*********************************************************************/
void example_moveP(RSHD rshd)
{
	/** 模拟业务 **/
	/** 接口调用: 初始化运动属性 ***/
	rs_init_global_move_profile(rshd);

	/** 接口调用: 设置关节型运动的最大加速度 ***/
	aubo_robot_namespace::JointVelcAccParam jointMaxAcc;
	jointMaxAcc.jointPara[0] = 50.0/180.0*M_PI;
	jointMaxAcc.jointPara[1] = 50.0/180.0*M_PI;
	jointMaxAcc.jointPara[2] = 50.0/180.0*M_PI;
	jointMaxAcc.jointPara[3] = 50.0/180.0*M_PI;
	jointMaxAcc.jointPara[4] = 50.0/180.0*M_PI;
	jointMaxAcc.jointPara[5] = 50.0/180.0*M_PI;   //接口要求单位是弧度
	rs_set_global_joint_maxacc(rshd, &jointMaxAcc);

	/** 接口调用: 设置关节型运动的最大速度 ***/
	aubo_robot_namespace::JointVelcAccParam jointMaxVelc;
	jointMaxVelc.jointPara[0] = 50.0/180.0*M_PI;
	jointMaxVelc.jointPara[1] = 50.0/180.0*M_PI;
	jointMaxVelc.jointPara[2] = 50.0/180.0*M_PI;
	jointMaxVelc.jointPara[3] = 50.0/180.0*M_PI;
	jointMaxVelc.jointPara[4] = 50.0/180.0*M_PI;
	jointMaxVelc.jointPara[5] = 50.0/180.0*M_PI;   //接口要求单位是弧度
	rs_set_global_joint_maxvelc(rshd, &jointMaxVelc);


	/** 接口调用: 初始化运动属性 ***/
	rs_init_global_move_profile(rshd);

	/** 接口调用: 设置末端型运动的最大加速度 　　直线运动属于末端型运动***/
	double endMoveMaxAcc;
	endMoveMaxAcc = 0.2;   //单位米每秒
	rs_set_global_end_max_line_acc(rshd, endMoveMaxAcc);
	rs_set_global_end_max_angle_acc(rshd, endMoveMaxAcc);

	/** 接口调用: 设置末端型运动的最大速度 直线运动属于末端型运动***/
	double endMoveMaxVelc;
	endMoveMaxVelc = 0.2;   //单位米每秒
	rs_set_global_end_max_line_velc(rshd, endMoveMaxVelc);
	rs_set_global_end_max_angle_velc(rshd, endMoveMaxVelc);

	double jointAngle[aubo_robot_namespace::ARM_DOF] = {0};

	for(int i=0;i<2;i++)
	{
		//准备点  关节运动属于关节型运动
		rs_init_global_move_profile(rshd);
		rs_set_global_joint_maxacc(rshd, &jointMaxAcc);
		rs_set_global_joint_maxvelc(rshd, &jointMaxVelc);

		//关节运动至准备点
		jointAngle[0] = -0.000003;
		jointAngle[1] = -0.127267;
		jointAngle[2] = -1.321122;
		jointAngle[3] = 0.376934;
		jointAngle[4] = -1.570796;
		jointAngle[5] = -0.000008;

		int ret = rs_move_joint(rshd, jointAngle);
		if(ret != RS_SUCC)
		{
			std::cerr<<"JointMove失败.　ret:"<<ret<<std::endl;
		}

		//圆弧
		rs_init_global_move_profile(rshd);

		rs_set_global_end_max_line_acc(rshd, endMoveMaxAcc);
		rs_set_global_end_max_angle_acc(rshd, endMoveMaxAcc);
		rs_set_global_end_max_line_velc(rshd, endMoveMaxVelc);
		rs_set_global_end_max_angle_velc(rshd, endMoveMaxVelc);

		jointAngle[0] = -0.000003;
		jointAngle[1] = -0.127267;
		jointAngle[2] = -1.321122;
		jointAngle[3] = 0.376934;
		jointAngle[4] = -1.570796;
		jointAngle[5] = -0.000008;
		rs_add_waypoint(rshd, jointAngle);

		jointAngle[0] = 0.200000;
		jointAngle[1] = -0.127267;
		jointAngle[2] = -1.321122;
		jointAngle[3] = 0.376934;
		jointAngle[4] = -1.570794;
		jointAngle[5] = -0.000008;
		rs_add_waypoint(rshd, jointAngle);

		jointAngle[0] = 0.600000;
		jointAngle[1] = -0.127267;
		jointAngle[2] = -1.321122;
		jointAngle[3] = 0.376934;
		jointAngle[4] = -1.570796;
		jointAngle[5] = -0.000008;
		rs_add_waypoint(rshd, jointAngle);

		jointAngle[0] = -1.000003;
		jointAngle[1] = -1.327267;
		jointAngle[2] = -1.321122;
		jointAngle[3] = 0.376934;
		jointAngle[4] = -1.570796;
		jointAngle[5] = -0.000008;
		rs_add_waypoint(rshd, jointAngle);
		rs_set_circular_loop_times(rshd, 0);
		if(RS_SUCC !=rs_move_track(rshd, JOINT_GNUBSPLINEINTP,true))
		{
			std::cerr<<"TrackMove failed.　ret:"<<ret<<std::endl;
		}

		////准备点
		//rs_init_global_move_profile(rshd);
		//rs_set_global_joint_maxacc(rshd, &jointMaxAcc);
		//rs_set_global_joint_maxvelc(rshd, &jointMaxVelc);

		//jointAngle[0] = -0.000003;
		//jointAngle[1] = -0.127267;
		//jointAngle[2] = -1.321122;
		//jointAngle[3] = 0.376934;
		//jointAngle[4] = -1.570796;
		//jointAngle[5] = -0.000008;

		////关节运动至准备点
		//ret = rs_move_joint(rshd, jointAngle);
		//if(RS_SUCC != ret)
		//{
		//	std::cerr<<"JointMove失败.　ret:"<<ret<<std::endl;
		//}

		////圆
		//rs_init_global_move_profile(rshd);

		//rs_set_global_end_max_line_acc(rshd, endMoveMaxAcc);
		//rs_set_global_end_max_angle_acc(rshd, endMoveMaxAcc);
		//rs_set_global_end_max_line_velc(rshd, endMoveMaxVelc);
		//rs_set_global_end_max_angle_velc(rshd, endMoveMaxVelc);

		//jointAngle[0] = -0.000003;
		//jointAngle[1] = -0.127267;
		//jointAngle[2] = -1.321122;
		//jointAngle[3] = 0.376934;
		//jointAngle[4] = -1.570796;
		//jointAngle[5] = -0.000008;
		//rs_add_waypoint(rshd, jointAngle);

		//jointAngle[0] = -0.211675;
		//jointAngle[1] = -0.325189;
		//jointAngle[2] = -1.466753;
		//jointAngle[3] = 0.429232;
		//jointAngle[4] = -1.570794;
		//jointAngle[5] = -0.211680;
		//rs_add_waypoint(rshd, jointAngle);

		//jointAngle[0] = -0.037186;
		//jointAngle[1] = -0.224307;
		//jointAngle[2] = -1.398285;
		//jointAngle[3] = 0.396819;
		//jointAngle[4] = -1.570796;
		//jointAngle[5] = -0.037191;
		//rs_add_waypoint(rshd, jointAngle);

		////圆的圈数
		//rs_set_circular_loop_times(rshd, 1);
		//ret = rs_move_track(rshd, ARC_CIR);
		//if(RS_SUCC != ret)
		//{
		//	std::cerr<<"TrackMove failed.　ret:"<<ret<<std::endl;
		//}


		////准备点
		//rs_init_global_move_profile(rshd);

		//rs_set_global_joint_maxacc(rshd, &jointMaxAcc);
		//rs_set_global_joint_maxvelc(rshd, &jointMaxVelc);

		//jointAngle[0] = -0.000003;
		//jointAngle[1] = -0.127267;
		//jointAngle[2] = -1.321122;
		//jointAngle[3] = 0.376934;
		//jointAngle[4] = -1.570796;
		//jointAngle[5] = -0.000008;

		////关节运动至准备点
		//if(RS_SUCC != rs_move_joint(rshd, jointAngle))
		//{
		//	std::cerr<<"JointMove失败.　ret:"<<ret<<std::endl;
		//}

		////MoveP
		//rs_init_global_move_profile(rshd);

		//rs_set_global_end_max_line_acc(rshd, endMoveMaxAcc);
		//rs_set_global_end_max_angle_acc(rshd, endMoveMaxAcc);
		//rs_set_global_end_max_line_velc(rshd, endMoveMaxVelc);
		//rs_set_global_end_max_angle_velc(rshd, endMoveMaxVelc);


		//jointAngle[0] = -0.000003;
		//jointAngle[1] = -0.127267;
		//jointAngle[2] = -1.321122;
		//jointAngle[3] = 0.376934;
		//jointAngle[4] = -1.570796;
		//jointAngle[5] = -0.000008;
		//rs_add_waypoint(rshd, jointAngle);

		//jointAngle[0] = 0.100000;
		//jointAngle[1] = -0.147267;
		//jointAngle[2] = -1.321122;
		//jointAngle[3] = 0.376934;
		//jointAngle[4] = -1.570794;
		//jointAngle[5] = -0.000008;
		//rs_add_waypoint(rshd, jointAngle);

		//jointAngle[0] = 0.200000;
		//jointAngle[1] = -0.167267;
		//jointAngle[2] = -1.321122;
		//jointAngle[3] = 0.376934;
		//jointAngle[4] = -1.570794;
		//jointAngle[5] = -0.000008;
		//rs_add_waypoint(rshd, jointAngle);

		////交融半径
		//rs_set_blend_radius(rshd, 0.03);
		//rs_set_circular_loop_times(rshd, 1);
		//if(RS_SUCC !=rs_move_track(rshd, CARTESIAN_MOVEP))
		//{
		//	std::cerr<<"TrackMove failed.　ret:"<<ret<<std::endl;
		//}
	}
}

/********************************************************************
	function:	example_ik_fk
	purpose :	机械臂正逆解测试
	param   :	
					
	return  :	
*********************************************************************/
void example_ik_fk(RSHD rshd)
{
	aubo_robot_namespace::wayPoint_S wayPoint;

	ik_solutions solutions;

	double jointAngle[aubo_robot_namespace::ARM_DOF] = {-0.000003, -0.127267, -1.321122, 0.376934, -1.570796, -0.000008};
	
	//正解
	if (RS_SUCC == rs_forward_kin(rshd, jointAngle, &wayPoint))
	{
		std::cout<<"fk succ"<<std::endl;

		printRoadPoint(&wayPoint);
	}

	//逆解
	double startPointJointAngle[aubo_robot_namespace::ARM_DOF] = {0.0/180.0*M_PI,  0.0/180.0*M_PI,  0.0/180.0*M_PI, 0.0/180.0*M_PI, 0.0/180.0*M_PI,0.0/180.0*M_PI};

	aubo_robot_namespace::Pos targetPosition;
	targetPosition.x =-0.400;
	targetPosition.y =-0.1215;
	targetPosition.z = 0.5476;

	aubo_robot_namespace::Rpy rpy;
	aubo_robot_namespace::Ori targetOri;

	rpy.rx = 180.0/180.0*M_PI;
	rpy.ry = 0.0/180.0*M_PI;
	rpy.rz = -90.0/180.0*M_PI;

	rs_rpy_to_quaternion(rshd, &rpy, &targetOri);

	if (RS_SUCC == rs_inverse_kin(rshd, startPointJointAngle, &targetPosition, &targetOri, &wayPoint))
	{
		std::cout<<"ik succ"<<std::endl;
		printRoadPoint(&wayPoint);
	}
	else
	{
		std::cerr<<"ik failed"<<std::endl;
	}

	if (RS_SUCC == rs_inverse_kin_closed_form(rshd, &targetPosition, &targetOri, &solutions))
	{
		std::cout<<"ik succ solutions.size="<<solutions.solution_count<<std::endl;
		for (int i=0;i<solutions.solution_count;i++)
		{
			printRoadPoint(&solutions.waypoint[i]);
		}
	}
	else
	{
		std::cerr<<"ik failed"<<std::endl;
	}
}

/********************************************************************
	function:	example_boardIO
	purpose :	机械臂控制柜IO测试(必须连接真实机械臂）
	param   :	rshd 上下文句柄
					
	return  :	void
*********************************************************************/
void example_boardIO(RSHD rshd)
{
	double status = 0;

	if (RS_SUCC == rs_set_board_io_status_by_name(rshd, RobotBoardUserDO, USER_DO_00, IO_STATUS_VALID))
	{
		std::cout<<"set "<<USER_DO_00<<" succ"<<std::endl;

		if (RS_SUCC == rs_get_board_io_status_by_name(rshd, RobotBoardUserDO, USER_DO_00, &status))
		{
			std::cout<<"get "<<USER_DO_00<<"="<<status<<std::endl;
		}
		else
		{
			std::cerr<<"get "<<USER_DO_00<<" failed"<<std::endl;
		}
	}
	else
	{
		std::cerr<<"set "<<USER_DO_00<<" failed"<<std::endl;
	}
}

//机械臂工具端IO测试(必须连接真实机械臂）
void example_ToolIO(RSHD rshd)
{
	double status = 0;

	//首先设置tool_io_0为数字输出
	if (RS_SUCC == rs_set_tool_io_type(rshd, TOOL_DIGITAL_IO_0, IO_OUT))
	{
		//设置tool_io_0数字输出为有效
		if (RS_SUCC == rs_set_tool_do_status(rshd, TOOL_IO_0, IO_STATUS_VALID))
		{
			std::cout<<"set "<<TOOL_IO_0<<" succ"<<std::endl;
		}
		else
		{
			std::cerr<<"set "<<TOOL_IO_0<<" failed"<<std::endl;
		}
		
		//获取tool_io_0数字输出的状态
		if (RS_SUCC == rs_get_tool_io_status(rshd, TOOL_IO_0, &status))
		{
			std::cout<<"get "<<TOOL_IO_0<<"="<<status<<std::endl;
		}
		else
		{
			std::cerr<<"get "<<TOOL_IO_0<<" failed"<<std::endl;
		}
	}
}

/********************************************************************
	function:	example_callbackRobotRoadPoint
	purpose :	实时路点信息回调函数测试
	param   :	rshd 上下文句柄
					
	return  :	true 成功 false 失败
*********************************************************************/
bool example_callbackRobotRoadPoint(RSHD rshd)
{
	bool result = false;
	
	//允许实时路点信息推送
	if (RS_SUCC == rs_enable_push_realtime_roadpoint(rshd, true))
	{
		if (rs_setcallback_realtime_roadpoint(rshd, callback_RealTimeRoadPoint, NULL))
		{
			result = true;
		}
		else
		{
			std::cerr<<"call rs_setcallback_realtime_roadpoint failed"<<std::endl;
		}
	}
	else
		std::cerr<<"call rs_enable_push_realtime_roadpoint failed!"<<std::endl;

	return result;
}

void demo_relativeOri(RSHD rshd)
{
	/** 接口调用: 初始化运动属性 ***/
	rs_init_global_move_profile(rshd);

	/** 接口调用: 设置关节型运动的最大加速度 ***/
	aubo_robot_namespace::JointVelcAccParam jointMaxAcc;
	jointMaxAcc.jointPara[0] = 50.0/180.0*M_PI;
	jointMaxAcc.jointPara[1] = 50.0/180.0*M_PI;
	jointMaxAcc.jointPara[2] = 50.0/180.0*M_PI;
	jointMaxAcc.jointPara[3] = 50.0/180.0*M_PI;
	jointMaxAcc.jointPara[4] = 50.0/180.0*M_PI;
	jointMaxAcc.jointPara[5] = 50.0/180.0*M_PI;   //接口要求单位是弧度
	rs_set_global_joint_maxacc(rshd, &jointMaxAcc);

	/** 接口调用: 设置关节型运动的最大速度 ***/
	aubo_robot_namespace::JointVelcAccParam jointMaxVelc;
	jointMaxVelc.jointPara[0] = 50.0/180.0*M_PI;
	jointMaxVelc.jointPara[1] = 50.0/180.0*M_PI;
	jointMaxVelc.jointPara[2] = 50.0/180.0*M_PI;
	jointMaxVelc.jointPara[3] = 50.0/180.0*M_PI;
	jointMaxVelc.jointPara[4] = 50.0/180.0*M_PI;
	jointMaxVelc.jointPara[5] = 50.0/180.0*M_PI;   //接口要求单位是弧度
	rs_set_global_joint_maxvelc(rshd, &jointMaxVelc);


	//该位置为机械臂的初始位置（提供6个关节角的关节信息（单位：弧度））
	double initPos[6]={
		0/180*M_PI,
		0/180*M_PI,
		90.0/180*M_PI,
		0/180*M_PI,
		90.0/180*M_PI,
		0/180*M_PI};

	//首先运动到初始位置
	rs_move_joint(rshd, initPos);

	double lineMoveMaxAcc = 0.5;   //单位米每秒
	rs_set_global_end_max_line_acc(rshd, lineMoveMaxAcc);
	rs_set_global_end_max_angle_acc(rshd, lineMoveMaxAcc);
	rs_set_global_end_max_line_velc(rshd, lineMoveMaxAcc);
	rs_set_global_end_max_angle_velc(rshd, lineMoveMaxAcc);

	aubo_robot_namespace::ToolInEndDesc toolInEndDesc;
	toolInEndDesc.toolInEndPosition.x=0;
	toolInEndDesc.toolInEndPosition.y=0;
	toolInEndDesc.toolInEndPosition.z=0.1;
	toolInEndDesc.toolInEndOrientation.w=1;
	toolInEndDesc.toolInEndOrientation.x=0;
	toolInEndDesc.toolInEndOrientation.y=0;
	toolInEndDesc.toolInEndOrientation.z=0;

	//首先获取当前路点信息
	aubo_robot_namespace::wayPoint_S wayPoint;

	aubo_robot_namespace::Ori relativeOri;
	aubo_robot_namespace::Rpy relativeRpy;

	relativeRpy.rx=0.1/180.0*M_PI;
	relativeRpy.ry=0.0/180.0*M_PI;
	relativeRpy.rz=0.0/180.0*M_PI;

	//欧拉角转四元素　　求得偏移量的四元素表示
	rs_rpy_to_quaternion(rshd, &relativeRpy, &relativeOri);

	aubo_robot_namespace::MoveRelative relativeMoveOnUserCoord;
	aubo_robot_namespace::CoordCalibrateByJointAngleAndTool userCoord;

	relativeMoveOnUserCoord.ena = true;
	relativeMoveOnUserCoord.relativePosition[0] = 0;
	relativeMoveOnUserCoord.relativePosition[1] = 0;
	relativeMoveOnUserCoord.relativePosition[2] = 0;
	relativeMoveOnUserCoord.relativeOri = relativeOri;

	userCoord.coordType=aubo_robot_namespace::EndCoordinate;
	userCoord.toolDesc=toolInEndDesc;

	//设置偏移
	rs_set_relative_offset_on_user(rshd, &relativeMoveOnUserCoord, &userCoord);
	rs_set_tool_kinematics_param(rshd, &toolInEndDesc);

	rs_get_current_waypoint(rshd, &wayPoint);

	rs_move_line(rshd, wayPoint.jointpos);
}
//void move_rotate(RSHD rshd)
//{
//	//首先获取当前路点信息
//	aubo_robot_namespace::wayPoint_S wayPoint;
//	/** 接口调用: 初始化运动属性 ***/
//	rs_init_global_move_profile(rshd);
//
//	/** 接口调用: 设置关节型运动的最大加速度 ***/
//	aubo_robot_namespace::JointVelcAccParam jointMaxAcc;
//	jointMaxAcc.jointPara[0] = 50.0 / 180.0 * M_PI;
//	jointMaxAcc.jointPara[1] = 50.0 / 180.0 * M_PI;
//	jointMaxAcc.jointPara[2] = 50.0 / 180.0 * M_PI;
//	jointMaxAcc.jointPara[3] = 50.0 / 180.0 * M_PI;
//	jointMaxAcc.jointPara[4] = 50.0 / 180.0 * M_PI;
//	jointMaxAcc.jointPara[5] = 50.0 / 180.0 * M_PI;   //接口要求单位是弧度
//	rs_set_global_joint_maxacc(rshd, &jointMaxAcc);
//
//	/** 接口调用: 设置关节型运动的最大速度 ***/
//	aubo_robot_namespace::JointVelcAccParam jointMaxVelc;
//	jointMaxVelc.jointPara[0] = 50.0 / 180.0 * M_PI;
//	jointMaxVelc.jointPara[1] = 50.0 / 180.0 * M_PI;
//	jointMaxVelc.jointPara[2] = 50.0 / 180.0 * M_PI;
//	jointMaxVelc.jointPara[3] = 50.0 / 180.0 * M_PI;
//	jointMaxVelc.jointPara[4] = 50.0 / 180.0 * M_PI;
//	jointMaxVelc.jointPara[5] = 50.0 / 180.0 * M_PI;   //接口要求单位是弧度
//	rs_set_global_joint_maxvelc(rshd, &jointMaxVelc);
//	aubo_robot_namespace::ToolInEndDesc toolInEndDesc;
//	toolInEndDesc.toolInEndPosition.x = 0;
//	toolInEndDesc.toolInEndPosition.y = 0;
//	toolInEndDesc.toolInEndPosition.z = 0.15;
//	toolInEndDesc.toolInEndOrientation.w = 1;
//	toolInEndDesc.toolInEndOrientation.x = 0;
//	toolInEndDesc.toolInEndOrientation.y = 0;
//	toolInEndDesc.toolInEndOrientation.z = 0;










////}



void example_follow_mode_movej(RSHD rshd)
{
	/** 接口调用: 初始化运动属性 ***/
	rs_init_global_move_profile(rshd);

	double zeroPos[6]={0,0,0,0,0,0};

	//该位置为机械臂的初始位置（提供6个关节角的关节信息（单位：弧度））
	double initPos[6]={
		0/180*M_PI,
		0/180*M_PI,
		90.0/180*M_PI,
		0/180*M_PI,
		90.0/180*M_PI,
		0/180*M_PI};

	int ret = rs_follow_mode_move_joint(rshd, initPos);
	std::cout<<"ret="<<ret<<std::endl;
	//延时1.5秒，紧接着运动到下一个点，此时机械臂动态改变运动方向运到到下一个目标位置
	Sleep(1500);
	ret = rs_follow_mode_move_joint(rshd, zeroPos);
	std::cout<<"ret="<<ret<<std::endl;
}

void example_get_diagnosis(RSHD rshd)
{
	RobotDiagnosis *info = new RobotDiagnosis;  

	while(1)
	{
		memset((void*)info, 0, sizeof(RobotDiagnosis));  

		rs_get_diagnosis_info(rshd, info);

		std::cout<<"info.macTargetPosBufferSize="<<info->macTargetPosBufferSize<<" info.macTargetPosDataSize="<<info->macTargetPosDataSize<<std::endl;

		Sleep(500);
	}
}

int getTrackPointsCount(std::string filePath)
{
	std::string line;
	std::ifstream in(filePath);
	int num = 0;

	if (in) // 有该文件
	{
		while (getline(in, line)) // line中不包括每行的换行符
		{
			num++;
		}
	}

	in.close();

	return num;
}

void logPrintCallback(aubo_robot_namespace::LOG_LEVEL logLevel, const char *str, void *arg)
{
	std::cout << "log Level: [" << logLevel  <<"] "<< str << std::endl;
}

int  example_forceFun(RSHD rshd)
{
	int ret = aubo_robot_namespace::ErrnoSucc;

	//添加日志注册回调,可以放在多线程中，您可以自己实现
	if (rs_setcallback_robot_loginfo(rshd, logPrintCallback, NULL) == aubo_robot_namespace::InterfaceCallSuccCode)
	{
		printf("设置日志注册回调成功！\n");
	}

	//aubo_robot_namespace::RegulateSpeedModeParamConfig_t speedModeParam;
	////第一步得到速度参数
	//if (rs_get_regulate_speed_param(rshd, &speedModeParam) == aubo_robot_namespace::InterfaceCallSuccCode)
	//{
	//	printf("获取调速模式参数成功！\n");
	//}
	////轨迹运动设置这块 m/s
	//speedModeParam.maxTcpAcceleration = 3.0;
	//speedModeParam.maxTcpVelocity = reduce_speed;
	////第二步 设置速度参数
	//if (rs_set_regulate_speed_param(rshd, &speedModeParam) == aubo_robot_namespace::InterfaceCallSuccCode)
	//{
	//	printf("设置调速模式参数成功！\n");
	//}
	////第三步 生效调速模式
	//if (rs_enable_regulate_speed_mode(rshd, true) == aubo_robot_namespace::InterfaceCallSuccCode)
	//{
	//	printf("生效调速模式！\n");
	//}

	aubo_robot_namespace::wayPoint_S firstWayPoint;
	//逆解参考点
	double referPoint[6] = { -0.0614578, -0.284789, -1.76023, -1.34487, -1.56585, -0.259649 };

	aubo_robot_namespace::ToolInEndDesc toolInEndDesc;
	toolInEndDesc.toolInEndPosition.x = 0.00;
	toolInEndDesc.toolInEndPosition.y = 0.00;
	toolInEndDesc.toolInEndPosition.z = 0.09;
	toolInEndDesc.toolInEndOrientation.w = 1.00;
	toolInEndDesc.toolInEndOrientation.x = 0.00;
	toolInEndDesc.toolInEndOrientation.y = 0.00;
	toolInEndDesc.toolInEndOrientation.z = 0.00;


	//设置末端型运动的加速度 units m/s2
	rs_set_global_end_max_line_acc(rshd, 3.0);
	//设置末端型运动的速度  units m/s
	rs_set_global_end_max_line_velc(rshd, 0.05);

	string path_str ;

	rs_move_stop(rshd);
	//保证运动停止
	Sleep(1000);

	//设置工具端运动学参数
	ret = rs_set_tool_kinematics_param(rshd, &toolInEndDesc);
	if (ret != aubo_robot_namespace::ErrnoSucc){
		std::cout << "设置动力学参数失败！" << std::endl;
		return ret;
	}else{
		std::cout << "设置动力学参数成功！" << std::endl;
	}

	ret = rs_remove_all_waypoint(rshd);
	if (ret != aubo_robot_namespace::ErrnoSucc){
		std::cout << "清除路点失败！ ret:"<<ret << std::endl;
		return ret;
	}

	path_str = "C:\\workspace\\trackLib\\trajHelix_53";
	std::cout << "轨迹路点个数：" << getTrackPointsCount(path_str) << std::endl;

	//轨迹文件处理
	ret = rs_parse_roadpoint_file_and_cache_result( rshd, path_str.data(), referPoint, &toolInEndDesc, &firstWayPoint);
	if (ret != aubo_robot_namespace::ErrnoSucc)
	{
		std::cout << "加载路点失败！错误码为：" << ret <<std::endl;
		return ret;
	}

	//移动至轨迹的第一个点

	rs_move_joint(rshd, firstWayPoint.jointpos, true);
	if (ret != aubo_robot_namespace::ErrnoSucc)
	{
		std::cout << "移动到第一个位置失败！ret:"<<ret << std::endl;
		return -1;
	}

	Sleep(1000);

	//运行轨迹
	ret = rs_move_cached_track(rshd);
	if (ret != aubo_robot_namespace::ErrnoSucc)
	{
		std::cout << "移动轨迹失败！错误码：" << ret << std::endl;
		return ret;
	}
	else
	{
		std::cout << "轨迹运行成功" << std::endl;
	}

	return ret;
}

int  example_forceFun_1(RSHD rshd)
{
	int ret = aubo_robot_namespace::ErrnoSucc;

	//添加日志注册回调,可以放在多线程中，您可以自己实现
	if (rs_setcallback_robot_loginfo(rshd, logPrintCallback, NULL) == aubo_robot_namespace::InterfaceCallSuccCode)
	{
		printf("设置日志注册回调成功！\n");
	}


	aubo_robot_namespace::wayPoint_S firstWayPoint;
	////xiuyu 逆解参考点
	double referPoint[6] = { 73.67*M_PI/180, -4.332*M_PI/180, -47.976*M_PI/180, 26.31*M_PI/180, 92.81*M_PI/180, -89.11*M_PI/180 };

	aubo_robot_namespace::ToolInEndDesc toolInEndDesc;
	toolInEndDesc.toolInEndPosition.x = 0.00;
	toolInEndDesc.toolInEndPosition.y = 0.00;
	toolInEndDesc.toolInEndPosition.z = 0.225;
	toolInEndDesc.toolInEndOrientation.w = 1.00;
	toolInEndDesc.toolInEndOrientation.x = 0.00;
	toolInEndDesc.toolInEndOrientation.y = 0.00;
	toolInEndDesc.toolInEndOrientation.z = 0.00;

	rs_init_global_move_profile(rshd);

	/** 接口调用: 设置关节型运动的最大加速度 ***/
	aubo_robot_namespace::JointVelcAccParam jointMaxAcc;
	jointMaxAcc.jointPara[0] = 10.0 / 180.0 * M_PI;
	jointMaxAcc.jointPara[1] = 10.0 / 180.0 * M_PI;
	jointMaxAcc.jointPara[2] = 10.0 / 180.0 * M_PI;
	jointMaxAcc.jointPara[3] = 10.0 / 180.0 * M_PI;
	jointMaxAcc.jointPara[4] = 10.0 / 180.0 * M_PI;
	jointMaxAcc.jointPara[5] = 10.0 / 180.0 * M_PI;   //接口要求单位是弧度
	rs_set_global_joint_maxacc(rshd, &jointMaxAcc);

	/** 接口调用: 设置关节型运动的最大速度 ***/
	aubo_robot_namespace::JointVelcAccParam jointMaxVelc;
	jointMaxVelc.jointPara[0] = 10.0 / 180.0 * M_PI;
	jointMaxVelc.jointPara[1] = 10.0 / 180.0 * M_PI;
	jointMaxVelc.jointPara[2] = 10.0 / 180.0 * M_PI;
	jointMaxVelc.jointPara[3] = 10.0 / 180.0 * M_PI;
	jointMaxVelc.jointPara[4] = 10.0 / 180.0 * M_PI;
	jointMaxVelc.jointPara[5] = 10.0 / 180.0 * M_PI;   //接口要求单位是弧度
	rs_set_global_joint_maxvelc(rshd, &jointMaxVelc);

	////设置末端型运动的加速度 units m/s2
	rs_set_global_end_max_line_acc(rshd, 0.02);
	////设置末端型运动的速度  units m/s
	rs_set_global_end_max_line_velc(rshd, 0.01);
	rs_set_global_joint_maxacc(rshd, &jointMaxAcc);
	rs_set_global_joint_maxvelc(rshd, &jointMaxVelc);

	string path_str ;

	//rs_move_stop(rshd);
	////保证运动停止
	//Sleep(1000);

	////设置工具端运动学参数
	//ret = rs_set_tool_kinematics_param(rshd, &toolInEndDesc);
	//if (ret != aubo_robot_namespace::ErrnoSucc){
	//	std::cout << "设置动力学参数失败！" << std::endl;
	//	return ret;
	//}else{
	//	std::cout << "设置动力学参数成功！" << std::endl;
	//}

	//ret = rs_remove_all_waypoint(rshd);
	//if (ret != aubo_robot_namespace::ErrnoSucc){
	//	std::cout << "清除路点失败！ ret:"<<ret << std::endl;
	//	return ret;
	//}

	//POSITION_MM_AND_RPY_ANGLE_SPACE_SPLIT
	//path_str = "C:\\workspace\\trackLib\\trajHelix_53";  
	//path_str = "C:\\workspace\\trackLib\\Point8TB";
	path_str = "D:\\05202\\myFile_1";
	std::cout << "轨迹路点个数：" << getTrackPointsCount(path_str) << std::endl;

	int sizeReturn;
	aubo_robot_namespace::wayPoint_S *wayPointVector;
	wayPointVector = (aubo_robot_namespace::wayPoint_S *)malloc(sizeof(aubo_robot_namespace::wayPoint_S)*20000);
	//轨迹文件处理
	ret = rs_parse_file_as_roadpoint_collection(rshd, path_str.data(), POSITION_M_AND_QUATERNION_COMMA_SPLIT, referPoint, &toolInEndDesc, &wayPointVector[0], 20000, &sizeReturn);
	if (ret != aubo_robot_namespace::ErrnoSucc)
	{
		std::cout << "解析路点文件失败！错误码为：" << ret <<std::endl;
		return ret;
	}
	std::cout << "解析路点成功  点数：" << sizeReturn <<std::endl;

	firstWayPoint = wayPointVector[0];
	//移动至轨迹的第一个点
	rs_move_joint(rshd, firstWayPoint.jointpos, true);
	if (ret != aubo_robot_namespace::ErrnoSucc)
	{
		std::cout << "移动到第一个位置失败！ret:"<<ret << std::endl;
		return -1;
	}
	rs_enable_force_control_mode(rshd, true);
	rs_set_force_control_mode_explore_force_param(rshd, 20, 0.05);//探寻力0-50N,距离0-0.1m
	rs_remove_all_waypoint(rshd);
	//Sleep(1000);

	//运行轨迹
	for(int i=0;i<sizeReturn;i++)
	{
		rs_add_waypoint(rshd, wayPointVector[i].jointpos);
	}
	

	//交融半径
	rs_set_blend_radius(rshd, 0.03);
	if(RS_SUCC !=rs_move_track(rshd, JOINT_GNUBSPLINEINTP))
	{
		std::cerr<<"TrackMove failed.　ret:"<<ret<<std::endl;
	}

	if (ret != aubo_robot_namespace::ErrnoSucc)
	{
		std::cout << "移动轨迹失败！错误码：" << ret << std::endl;
		return ret;
	}
	else
	{
		std::cout << "轨迹运行成功" << std::endl;
	}
	path_str = "D:\\myFile_d2";
	std::cout << "轨迹路点个数：" << getTrackPointsCount(path_str) << std::endl;


	wayPointVector = (aubo_robot_namespace::wayPoint_S*)malloc(sizeof(aubo_robot_namespace::wayPoint_S) * 20000);
	//轨迹文件处理
	ret = rs_parse_file_as_roadpoint_collection(rshd, path_str.data(), POSITION_M_AND_QUATERNION_COMMA_SPLIT, referPoint, &toolInEndDesc, &wayPointVector[0], 20000, &sizeReturn);
	if (ret != aubo_robot_namespace::ErrnoSucc)
	{
		std::cout << "解析路点文件失败！错误码为：" << ret << std::endl;
		return ret;
	}
	std::cout << "解析路点成功  点数：" << sizeReturn << std::endl;

	firstWayPoint = wayPointVector[0];
	//移动至轨迹的第一个点
	rs_move_joint(rshd, firstWayPoint.jointpos, true);
	if (ret != aubo_robot_namespace::ErrnoSucc)
	{
		std::cout << "移动到第一个位置失败！ret:" << ret << std::endl;
		return -1;
	}
	//rs_enable_force_control_mode(rshd, true);
	//rs_set_force_control_mode_explore_force_param(rshd, 20, 0.05);//探寻力0-50N,距离0-0.1m
	rs_remove_all_waypoint(rshd);
	//Sleep(1000);

	//运行轨迹
	for (int i = 0; i < sizeReturn; i++)
	{
		rs_add_waypoint(rshd, wayPointVector[i].jointpos);
	}


	//交融半径
	rs_set_blend_radius(rshd, 0.03);
	if (RS_SUCC != rs_move_track(rshd, JOINT_GNUBSPLINEINTP))
	{
		std::cerr << "TrackMove failed.　ret:" << ret << std::endl;
	}

	if (ret != aubo_robot_namespace::ErrnoSucc)
	{
		std::cout << "移动轨迹失败！错误码：" << ret << std::endl;
		return ret;
	}
	else
	{
		std::cout << "轨迹运行成功" << std::endl;
	}
	path_str = "D:\\myFile_d3";
	std::cout << "轨迹路点个数：" << getTrackPointsCount(path_str) << std::endl;


	wayPointVector = (aubo_robot_namespace::wayPoint_S*)malloc(sizeof(aubo_robot_namespace::wayPoint_S) * 20000);
	//轨迹文件处理
	ret = rs_parse_file_as_roadpoint_collection(rshd, path_str.data(), POSITION_M_AND_QUATERNION_COMMA_SPLIT, referPoint, &toolInEndDesc, &wayPointVector[0], 20000, &sizeReturn);
	if (ret != aubo_robot_namespace::ErrnoSucc)
	{
		std::cout << "解析路点文件失败！错误码为：" << ret << std::endl;
		return ret;
	}
	std::cout << "解析路点成功  点数：" << sizeReturn << std::endl;

	firstWayPoint = wayPointVector[0];
	//移动至轨迹的第一个点
	rs_move_joint(rshd, firstWayPoint.jointpos, true);
	if (ret != aubo_robot_namespace::ErrnoSucc)
	{
		std::cout << "移动到第一个位置失败！ret:" << ret << std::endl;
		return -1;
	}
	//rs_enable_force_control_mode(rshd, true);
	//rs_set_force_control_mode_explore_force_param(rshd, 20, 0.05);//探寻力0-50N,距离0-0.1m
	rs_remove_all_waypoint(rshd);
	//Sleep(1000);

	//运行轨迹
	for (int i = 0; i < sizeReturn; i++)
	{
		rs_add_waypoint(rshd, wayPointVector[i].jointpos);
	}


	//交融半径
	rs_set_blend_radius(rshd, 0.03);
	if (RS_SUCC != rs_move_track(rshd, JOINT_GNUBSPLINEINTP))
	{
		std::cerr << "TrackMove failed.　ret:" << ret << std::endl;
	}

	if (ret != aubo_robot_namespace::ErrnoSucc)
	{
		std::cout << "移动轨迹失败！错误码：" << ret << std::endl;
		return ret;
	}
	else
	{
		std::cout << "轨迹运行成功" << std::endl;
	}
	path_str = "D:\\myFile_d4";
	std::cout << "轨迹路点个数：" << getTrackPointsCount(path_str) << std::endl;


	wayPointVector = (aubo_robot_namespace::wayPoint_S*)malloc(sizeof(aubo_robot_namespace::wayPoint_S) * 20000);
	//轨迹文件处理
	ret = rs_parse_file_as_roadpoint_collection(rshd, path_str.data(), POSITION_M_AND_QUATERNION_COMMA_SPLIT, referPoint, &toolInEndDesc, &wayPointVector[0], 20000, &sizeReturn);
	if (ret != aubo_robot_namespace::ErrnoSucc)
	{
		std::cout << "解析路点文件失败！错误码为：" << ret << std::endl;
		return ret;
	}
	std::cout << "解析路点成功  点数：" << sizeReturn << std::endl;

	firstWayPoint = wayPointVector[0];
	//移动至轨迹的第一个点
	rs_move_joint(rshd, firstWayPoint.jointpos, true);
	if (ret != aubo_robot_namespace::ErrnoSucc)
	{
		std::cout << "移动到第一个位置失败！ret:" << ret << std::endl;
		return -1;
	}
	//rs_enable_force_control_mode(rshd, true);
	//rs_set_force_control_mode_explore_force_param(rshd, 20, 0.05);//探寻力0-50N,距离0-0.1m
	rs_remove_all_waypoint(rshd);
	//Sleep(1000);

	//运行轨迹
	for (int i = 0; i < sizeReturn; i++)
	{
		rs_add_waypoint(rshd, wayPointVector[i].jointpos);
	}


	//交融半径
	rs_set_blend_radius(rshd, 0.03);
	if (RS_SUCC != rs_move_track(rshd, JOINT_GNUBSPLINEINTP))
	{
		std::cerr << "TrackMove failed.　ret:" << ret << std::endl;
	}

	if (ret != aubo_robot_namespace::ErrnoSucc)
	{
		std::cout << "移动轨迹失败！错误码：" << ret << std::endl;
		return ret;
	}
	else
	{
		std::cout << "轨迹运行成功" << std::endl;
	}
	path_str = "D:\\myFile_d5";
	std::cout << "轨迹路点个数：" << getTrackPointsCount(path_str) << std::endl;


	wayPointVector = (aubo_robot_namespace::wayPoint_S*)malloc(sizeof(aubo_robot_namespace::wayPoint_S) * 20000);
	//轨迹文件处理
	ret = rs_parse_file_as_roadpoint_collection(rshd, path_str.data(), POSITION_M_AND_QUATERNION_COMMA_SPLIT, referPoint, &toolInEndDesc, &wayPointVector[0], 20000, &sizeReturn);
	if (ret != aubo_robot_namespace::ErrnoSucc)
	{
		std::cout << "解析路点文件失败！错误码为：" << ret << std::endl;
		return ret;
	}
	std::cout << "解析路点成功  点数：" << sizeReturn << std::endl;

	firstWayPoint = wayPointVector[0];
	//移动至轨迹的第一个点
	rs_move_joint(rshd, firstWayPoint.jointpos, true);
	if (ret != aubo_robot_namespace::ErrnoSucc)
	{
		std::cout << "移动到第一个位置失败！ret:" << ret << std::endl;
		return -1;
	}
	//rs_enable_force_control_mode(rshd, true);
	//rs_set_force_control_mode_explore_force_param(rshd, 20, 0.05);//探寻力0-50N,距离0-0.1m
	rs_remove_all_waypoint(rshd);
	//Sleep(1000);

	//运行轨迹
	for (int i = 0; i < sizeReturn; i++)
	{
		rs_add_waypoint(rshd, wayPointVector[i].jointpos);
	}


	//交融半径
	rs_set_blend_radius(rshd, 0.03);
	if (RS_SUCC != rs_move_track(rshd, JOINT_GNUBSPLINEINTP))
	{
		std::cerr << "TrackMove failed.　ret:" << ret << std::endl;
	}

	if (ret != aubo_robot_namespace::ErrnoSucc)
	{
		std::cout << "移动轨迹失败！错误码：" << ret << std::endl;
		return ret;
	}
	else
	{
		std::cout << "轨迹运行成功" << std::endl;
	}
	return ret;
}
void example_move_joint_to(RSHD rshd)
{
	Pos targetPos = { -0.489605, -0.155672, 0.548430 };
	ToolInEndDesc tool;
	tool.toolInEndOrientation.w = 1;
	tool.toolInEndOrientation.x = 0;
	tool.toolInEndOrientation.y = 0;
	tool.toolInEndOrientation.z = 0;
	tool.toolInEndPosition.x = 0;
	tool.toolInEndPosition.y = 0;
	tool.toolInEndPosition.z = 0;
	//轴动到目标位置
	if (RS_SUCC == rs_move_line_to(rshd, &targetPos, &tool))
	{
		std::cout << "at target" << std::endl;
	}
	else
	{
		std::cerr << "move joint error" << std::endl;
	}
}