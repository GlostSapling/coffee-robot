# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.4.2]

  * 解决逆解失败问题（关节角度限制初始化为0）
  * 增加i20_1650_A机器人型号

## [2.4.1]

  * 修改全局运动属性设置接口，当有多台机器人接入主机时，能够实现分别设置运动属性
  * 修复逆解算法可能引起的程序崩溃问题
  * 解决了C# x86系统无法使用锥形扫描接口的问题

## [2.4.0]

  * 增加绕工具末端固定坐标系旋转功能
  * 增加‘robotServiceGetJointPositionLimit’接口
  * 补充交叉编译protobuf_armv7/armv8,log4cplus_armv8,our_alg_i5p_armv7/armv8库文件(交叉编译器:aarch64_linux_android,arm_linux_androideabi)
  * 增加 i20_1500 dh param and enum

## [2.3.3]

  * 增加i20_1500机器人型号

## [2.3.2]

  * 在end坐标系下的纯转动
  * 解决逆解失败的问题（逆解超出限制 TR313）

## [2.3.1]

  * 合并实时版本SDK
  * 增加protobuf3编译选项
  * Windows编译修复
  * 取消movep关节角度变化限制

## [2.3.0]

  * 合并实时版本SDK

## [2.2.1]

  * 增加ROBOT_I20TD枚举
  * 修复pthread_mutex_init/pthread_create调用顺序引发的错误

## [2.2.0]

  * 修改i20td/i5L参数
  * 修改protobuf中DH参数模型，由定点数改为浮点数，与服务器统一

## [2.1.1]

  * 完成从SVN服务器到gitlab服务器的迁移
