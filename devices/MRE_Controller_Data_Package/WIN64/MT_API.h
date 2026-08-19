#ifndef _MT_API_
#define _MT_API_
/*
C接口文件
4.4
*/
#include "stdint.h"
#pragma comment(lib,"MT_API.lib")
#ifdef __cplusplus
#define MT_API extern "C" __declspec( dllexport )
#else
#define MT_API __declspec( dllexport )
#endif

#define R_OK   0
#define RUN_OFF   0
#define RUN_ON   1
#define DIR_NEG   0
#define DIR_POS   1
#define LIMIT_ON   1
#define LIMIT_OFF   0
#define RESOURCE_MOTOR   0x00000001
#define RESOURCE_TTL_IN   0x00000002
#define RESOURCE_TTL_OUT   0x00000004
#define RESOURCE_OPTIC_IN   0x00000008
#define RESOURCE_OPTIC_OUT   0x00000010
#define RESOURCE_AD   0x00000020
#define RESOURCE_OC   0x00000040
#define RESOURCE_LINE   0x00000080
#define RESOURCE_CIRCLE   0x00000100
#define RESOURCE_PLC   0x00000200
#define RESOURCE_STREAM   0x00000400
#define RESOURCE_ENCODER   0x00000800
#define RESOURCE_PWM   0x00001000
#define RESOURCE_T   0x00002000
#define RESOURCE_TRIGGER   0x00004000

//**************************************************//
// V4.3 updated 2020-04-24
//**************************************************//
//==================================================
//运行环境
//===================================================
//dll版本
//初始化窗口
MT_API int32_t __stdcall MT_Init(void);

//关闭窗口
MT_API int32_t __stdcall MT_DeInit(void);

//获取dll版本号
MT_API int32_t __stdcall MT_Get_Dll_Version(char** sVer);

//设置线程锁时间
MT_API int32_t __stdcall MT_Set_Thread_Timeout(uint32_t ms);

//======================================================
//通信口
//======================================================
//打开 UART
MT_API int32_t __stdcall MT_Open_UART(char* sCOM);

MT_API int32_t __stdcall MT_Open_UART_Unicode(TCHAR* sCOM);

MT_API int32_t __stdcall MT_M_Open_UART(int32_t ADev,char* sCOM);

MT_API int32_t __stdcall MT_M_Open_UART_Unicode(int32_t ADev,TCHAR* sCOM);

MT_API int32_t __stdcall MT_Open_UART_ID(int32_t AID);

//关闭 UART
MT_API int32_t __stdcall MT_Close_UART(void);

MT_API int32_t __stdcall MT_M_Close_UART(int32_t ADev);

//打开USB,按系统顺序
MT_API int32_t __stdcall MT_Open_USB(void);

MT_API int32_t __stdcall MT_M_Open_USB(int32_t ADev);

//打开USB，按序列号指定
MT_API int32_t __stdcall MT_M_Open_USB_SN(int32_t ADev,TCHAR* ASN);

//关闭USB
MT_API int32_t __stdcall MT_Close_USB(void);

MT_API int32_t __stdcall MT_M_Close_USB(int32_t ADev);

//打开网口
MT_API int32_t __stdcall MT_Open_Net(uint8_t IP0,uint8_t IP1,uint8_t IP2,uint8_t IP3,uint16_t IPPort);

MT_API int32_t __stdcall MT_M_Open_Net(int32_t ADev,uint8_t IP0,uint8_t IP1,uint8_t IP2,uint8_t IP3,uint16_t IPPort);

//2021 04 20 字符串输入IP或者主机名
MT_API int32_t __stdcall MT_Open_Net_Name(char* IP_or_Name,uint16_t IPPort);

MT_API int32_t __stdcall MT_M_Open_Net_Name(int32_t ADev,char* IP_or_Name,uint16_t IPPort);

//关闭网口
MT_API int32_t __stdcall MT_Close_Net(void);

MT_API int32_t __stdcall MT_M_Close_Net(int32_t ADev);

//=====================================================
//板卡检测
//=====================================================
//检测设备
MT_API int32_t __stdcall MT_Check(void);

MT_API int32_t __stdcall MT_M_Check(int32_t ADev);

//读取资源模块
MT_API int32_t __stdcall MT_Get_Product_Resource(int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Product_Resource(int32_t ADev,int32_t* pValue);

//获取ID
MT_API int32_t __stdcall MT_Get_Product_ID(char* sID);

MT_API int32_t __stdcall MT_M_Get_Product_ID(int32_t ADev,char* sID);

//获取SN
MT_API int32_t __stdcall MT_Get_Product_SN(char* sSN);

MT_API int32_t __stdcall MT_M_Get_Product_SN(int32_t ADev,char* sSN);

//获取SN2
MT_API int32_t __stdcall MT_Get_Product_SN2(uint8_t* sSN);

MT_API int32_t __stdcall MT_M_Get_Product_SN2(int32_t ADev,uint8_t* sSN);

//获取SN3
MT_API int32_t __stdcall MT_Get_Product_SN3(char* sSN);

MT_API int32_t __stdcall MT_M_Get_Product_SN3(int32_t ADev,char* sSN);

//读取固件版本号
MT_API int32_t __stdcall MT_Get_Product_Version(int32_t* pMajor,int32_t* pMinor);

MT_API int32_t __stdcall MT_M_Get_Product_Version(int32_t ADev,int32_t* pMajor,int32_t* pMinor);

//读取固件版本号
MT_API int32_t __stdcall MT_Get_Product_Version2(int32_t* pMajor,int32_t* pMinor,int32_t* pRelease,int32_t* pBuild);

MT_API int32_t __stdcall MT_M_Get_Product_Version2(int32_t ADev,int32_t* pMajor,int32_t* pMinor,int32_t* pRelease,int32_t* pBuild);

//===================================================================
//电机相关
//====================================================================
//轴数
MT_API int32_t __stdcall MT_Get_Axis_Num(int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Axis_Num(int32_t ADev,int32_t* pValue);

//读取加速度
MT_API int32_t __stdcall MT_Get_Axis_Acc(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Axis_Acc(int32_t ADev,uint16_t AObj,int32_t* pValue);

//设置加速度
MT_API int32_t __stdcall MT_Set_Axis_Acc(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Axis_Acc(int32_t ADev,uint16_t AObj,int32_t Value);

//读取加速度
MT_API int32_t __stdcall MT_Get_Axis_Dec(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Axis_Dec(int32_t ADev,uint16_t AObj,int32_t* pValue);

//设置加速度
MT_API int32_t __stdcall MT_Set_Axis_Dec(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Axis_Dec(int32_t ADev,uint16_t AObj,int32_t Value);

//读取工作模式
MT_API int32_t __stdcall MT_Get_Axis_Mode(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Axis_Mode(int32_t ADev,uint16_t AObj,int32_t* pValue);

//设置速度模式
MT_API int32_t __stdcall MT_Set_Axis_Mode_Velocity(uint16_t AObj);

MT_API int32_t __stdcall MT_M_Set_Axis_Mode_Velocity(int32_t ADev,uint16_t AObj);

//设置位置模式
MT_API int32_t __stdcall MT_Set_Axis_Mode_Position(uint16_t AObj);

MT_API int32_t __stdcall MT_M_Set_Axis_Mode_Position(int32_t ADev,uint16_t AObj);

MT_API int32_t __stdcall MT_Set_Axis_Mode_Position_Open(uint16_t AObj);

MT_API int32_t __stdcall MT_M_Set_Axis_Mode_Position_Open(int32_t ADev,uint16_t AObj);

MT_API int32_t __stdcall MT_Set_Axis_Mode_Position_Close(uint16_t AObj);

MT_API int32_t __stdcall MT_M_Set_Axis_Mode_Position_Close(int32_t ADev,uint16_t AObj);

//读取速度模式目标速度
MT_API int32_t __stdcall MT_Get_Axis_Velocity_V_Target(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Axis_Velocity_V_Target(int32_t ADev,uint16_t AObj,int32_t* pValue);

//设置速度模式目标速度
MT_API int32_t __stdcall MT_Set_Axis_Velocity_V_Target_Abs(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Axis_Velocity_V_Target_Abs(int32_t ADev,uint16_t AObj,int32_t Value);

//设置速度模式目标速度
MT_API int32_t __stdcall MT_Set_Axis_Velocity_V_Target_Rel(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Axis_Velocity_V_Target_Rel(int32_t ADev,uint16_t AObj,int32_t Value);

//停止速度模式
MT_API int32_t __stdcall MT_Set_Axis_Velocity_Stop(uint16_t AObj);

MT_API int32_t __stdcall MT_M_Set_Axis_Velocity_Stop(int32_t ADev,uint16_t AObj);

//读取位置模式最大速度
MT_API int32_t __stdcall MT_Get_Axis_Position_V_Max(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Axis_Position_V_Max(int32_t ADev,uint16_t AObj,int32_t* pValue);

//设置位置模式最大速度
MT_API int32_t __stdcall MT_Set_Axis_Position_V_Max(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Axis_Position_V_Max(int32_t ADev,uint16_t AObj,int32_t Value);

//读取位置模式目标
MT_API int32_t __stdcall MT_Get_Axis_Position_P_Target(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Axis_Position_P_Target(int32_t ADev,uint16_t AObj,int32_t* pValue);

//设置位置模式目标
MT_API int32_t __stdcall MT_Set_Axis_Position_P_Target_Abs(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Axis_Position_P_Target_Abs(int32_t ADev,uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_Set_Axis_Position_P_Target_Rel(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Axis_Position_P_Target_Rel(int32_t ADev,uint16_t AObj,int32_t Value);

//停止位置模式
MT_API int32_t __stdcall MT_Set_Axis_Position_Stop(uint16_t AObj);

MT_API int32_t __stdcall MT_M_Set_Axis_Position_Stop(int32_t ADev,uint16_t AObj);

//设置编码器比例,用在减速判断上
MT_API int32_t __stdcall MT_Set_Axis_Position_Close_Dec_Factor(uint16_t AObj,float AFactor);

MT_API int32_t __stdcall MT_M_Set_Axis_Position_Close_Dec_Factor(int32_t ADev,uint16_t AObj,float AFactor);

//紧急停止
MT_API int32_t __stdcall MT_Set_Axis_Halt(uint16_t AObj);

MT_API int32_t __stdcall MT_M_Set_Axis_Halt(int32_t ADev,uint16_t AObj);

MT_API int32_t __stdcall MT_Set_Axis_Halt_All(void);

MT_API int32_t __stdcall MT_M_Set_Axis_Halt_All(int32_t ADev);

//////////////////////////////////////////////////////////////
///  状态相关
///  //////////////////////////////////////////////////////
//读取当前速度
MT_API int32_t __stdcall MT_Get_Axis_V_Now(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Axis_V_Now(int32_t ADev,uint16_t AObj,int32_t* pValue);

//读取当前软件位置
MT_API int32_t __stdcall MT_Get_Axis_P_Now(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Axis_P_Now(int32_t ADev,uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_Get_Axis_Software_P_Now(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Axis_Software_P_Now(int32_t ADev,uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_Get_Axis_Software_P(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Axis_Software_P(int32_t ADev,uint16_t AObj,int32_t* pValue);

//设置软件位置
MT_API int32_t __stdcall MT_Set_Axis_P_Now(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Axis_P_Now(int32_t ADev,uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_Set_Axis_Software_P(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Axis_Software_P(int32_t ADev,uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_Set_Axis_Software_P_Now(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Axis_Software_P_Now(int32_t ADev,uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_Get_Axis_Status(uint16_t AObj,uint8_t* pRun,uint8_t* pDir,uint8_t* pNeg,uint8_t* pPos,uint8_t* pZero,uint8_t* pMode);

MT_API int32_t __stdcall MT_M_Get_Axis_Status(int32_t ADev,uint16_t AObj,uint8_t* pRun,uint8_t* pDir,uint8_t* pNeg,uint8_t* pPos,uint8_t* pZero,uint8_t* pMode);

MT_API int32_t __stdcall MT_Get_Axis_Status2(uint16_t AObj,int32_t* pRun,int32_t* pDir,int32_t* pNeg,int32_t* pPos,int32_t* pZero,int32_t* pMode);

MT_API int32_t __stdcall MT_M_Get_Axis_Status2(int32_t ADev,uint16_t AObj,int32_t* pRun,int32_t* pDir,int32_t* pNeg,int32_t* pPos,int32_t* pZero,int32_t* pMode);

MT_API int32_t __stdcall MT_Get_Axis_Status_Run(uint16_t AObj,int32_t* pRun);

MT_API int32_t __stdcall MT_M_Get_Axis_Status_Run(int32_t ADev,uint16_t AObj,int32_t* pRun);

MT_API int32_t __stdcall MT_Get_Axis_Status_Dir(uint16_t AObj,int32_t* pDir);

MT_API int32_t __stdcall MT_M_Get_Axis_Status_Dir(int32_t ADev,uint16_t AObj,int32_t* pDir);

MT_API int32_t __stdcall MT_Get_Axis_Status_Neg(uint16_t AObj,int32_t* pNeg);

MT_API int32_t __stdcall MT_M_Get_Axis_Status_Neg(int32_t ADev,uint16_t AObj,int32_t* pNeg);

MT_API int32_t __stdcall MT_Get_Axis_Status_Pos(uint16_t AObj,int32_t* pPos);

MT_API int32_t __stdcall MT_M_Get_Axis_Status_Pos(int32_t ADev,uint16_t AObj,int32_t* pPos);

MT_API int32_t __stdcall MT_Get_Axis_Status_Zero(uint16_t AObj,int32_t* pZero);

MT_API int32_t __stdcall MT_M_Get_Axis_Status_Zero(int32_t ADev,uint16_t AObj,int32_t* pZero);

MT_API int32_t __stdcall MT_Get_Axis_Status_Mode(uint16_t AObj,int32_t* pMode);

MT_API int32_t __stdcall MT_M_Get_Axis_Status_Mode(int32_t ADev,uint16_t AObj,int32_t* pMode);

//设置0位模式
MT_API int32_t __stdcall MT_Set_Axis_Mode_Home(uint16_t AObj);

MT_API int32_t __stdcall MT_M_Set_Axis_Mode_Home(int32_t ADev,uint16_t AObj);

MT_API int32_t __stdcall MT_Set_Axis_Mode_Home_Home_Switch(uint16_t AObj);

MT_API int32_t __stdcall MT_M_Set_Axis_Mode_Home_Home_Switch(int32_t ADev,uint16_t AObj);

MT_API int32_t __stdcall MT_Set_Axis_Mode_Home_Encoder_Index(uint16_t AObj);

MT_API int32_t __stdcall MT_M_Set_Axis_Mode_Home_Encoder_Index(int32_t ADev,uint16_t AObj);

MT_API int32_t __stdcall MT_Set_Axis_Mode_Home_Encoder_Home_Switch(uint16_t AObj);

MT_API int32_t __stdcall MT_M_Set_Axis_Mode_Home_Encoder_Home_Switch(int32_t ADev,uint16_t AObj);

MT_API int32_t __stdcall MT_Set_Axis_Mode_Home_Home_Zero(uint16_t AObj);

MT_API int32_t __stdcall MT_M_Set_Axis_Mode_Home_Home_Zero(int32_t ADev,uint16_t AObj);

//设置0位模式目标速度
MT_API int32_t __stdcall MT_Set_Axis_Home_V(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Axis_Home_V(int32_t ADev,uint16_t AObj,int32_t Value);

//停止0位模式
MT_API int32_t __stdcall MT_Set_Axis_Home_Stop(uint16_t AObj);

MT_API int32_t __stdcall MT_M_Set_Axis_Home_Stop(int32_t ADev,uint16_t AObj);

//软件限位
//设置软件限位值
MT_API int32_t __stdcall MT_Set_Axis_Software_Limit_Neg_Value(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Axis_Software_Limit_Neg_Value(int32_t ADev,uint16_t AObj,int32_t Value);

//设置软件限位值
MT_API int32_t __stdcall MT_Set_Axis_Software_Limit_Pos_Value(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Axis_Software_Limit_Pos_Value(int32_t ADev,uint16_t AObj,int32_t Value);

//使能软件限位模式
MT_API int32_t __stdcall MT_Set_Axis_Software_Limit_Enable(uint16_t AObj);

MT_API int32_t __stdcall MT_M_Set_Axis_Software_Limit_Enable(int32_t ADev,uint16_t AObj);

//停止软件限位模式
MT_API int32_t __stdcall MT_Set_Axis_Software_Limit_Disable(uint16_t AObj);

MT_API int32_t __stdcall MT_M_Set_Axis_Software_Limit_Disable(int32_t ADev,uint16_t AObj);

////////////////////////////////////////////////////////////////////////
//存储器
//读取存储器长度
MT_API int32_t __stdcall MT_Get_System_Mem_Len(int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_System_Mem_Len(int32_t ADev,int32_t* pValue);

//读取存储器数据
MT_API int32_t __stdcall MT_Get_System_Mem_Data(uint16_t AObj,uint8_t* pValue);

MT_API int32_t __stdcall MT_M_Get_System_Mem_Data(int32_t ADev,uint16_t AObj,uint8_t* pValue);

//设置存储器数据
MT_API int32_t __stdcall MT_Set_System_Mem_Data(uint16_t AObj,uint8_t Value);

MT_API int32_t __stdcall MT_M_Set_System_Mem_Data(int32_t ADev,uint16_t AObj,uint8_t Value);

//====================================================================
// 系统参数存储器
//======================================================================
// 读取存储器长度
MT_API int32_t __stdcall MT_Get_Param_Mem_Len(int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Param_Mem_Len(int32_t ADev,int32_t* pValue);

//读取存储器数据
MT_API int32_t __stdcall MT_Get_Param_Mem_Data(uint16_t AObj,uint8_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Param_Mem_Data(int32_t ADev,uint16_t AObj,uint8_t* pValue);

//设置存储器数据
MT_API int32_t __stdcall MT_Set_Param_Mem_Data(uint16_t AObj,uint8_t Value);

MT_API int32_t __stdcall MT_M_Set_Param_Mem_Data(int32_t ADev,uint16_t AObj,uint8_t Value);

//====================================================================
//光隔输入
//======================================================================
//通道数
MT_API int32_t __stdcall MT_Get_Optic_In_Num(int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Optic_In_Num(int32_t ADev,int32_t* pValue);

//不算复用电机的限位和零位
MT_API int32_t __stdcall MT_Get_Optic_In_Basic_Num(int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Optic_In_Basic_Num(int32_t ADev,int32_t* pValue);

//读取单通道值
MT_API int32_t __stdcall MT_Get_Optic_In_Single(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Optic_In_Single(int32_t ADev,uint16_t AObj,int32_t* pValue);

//读取所有通道值
MT_API int32_t __stdcall MT_Get_Optic_In_All(int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Optic_In_All(int32_t ADev,int32_t* pValue);

//====================================================================
//光隔输出
//======================================================================
//通道数
MT_API int32_t __stdcall MT_Get_Optic_Out_Num(int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Optic_Out_Num(int32_t ADev,int32_t* pValue);

//设置单通道值
MT_API int32_t __stdcall MT_Set_Optic_Out_Single(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Optic_Out_Single(int32_t ADev,uint16_t AObj,int32_t Value);

//设置所有通道值
MT_API int32_t __stdcall MT_Set_Optic_Out_All(int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Optic_Out_All(int32_t ADev,int32_t Value);

//读取单通道值
MT_API int32_t __stdcall MT_Get_Optic_Out_Single(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Optic_Out_Single(int32_t ADev,uint16_t AObj,int32_t* pValue);

//读取所有通道值
MT_API int32_t __stdcall MT_Get_Optic_Out_All(int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Optic_Out_All(int32_t ADev,int32_t* pValue);

//====================================================================
//OC输出
//======================================================================
//通道数
MT_API int32_t __stdcall MT_Get_OC_Out_Num(int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_OC_Out_Num(int32_t ADev,int32_t* pValue);

//设置单通道值
MT_API int32_t __stdcall MT_Set_OC_Out_Single(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_OC_Out_Single(int32_t ADev,uint16_t AObj,int32_t Value);

//设置所有通道值
MT_API int32_t __stdcall MT_Set_OC_Out_All(int32_t Value);

MT_API int32_t __stdcall MT_M_Set_OC_Out_All(int32_t ADev,int32_t Value);

//读取单通道值
MT_API int32_t __stdcall MT_Get_OC_Out_Single(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_OC_Out_Single(int32_t ADev,uint16_t AObj,int32_t* pValue);

//读取所有通道值
MT_API int32_t __stdcall MT_Get_OC_Out_All(int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_OC_Out_All(int32_t ADev,int32_t* pValue);

//直线插补相关
//设置直线插补主轴及速度
MT_API int32_t __stdcall MT_Set_Axis_Line_Axis(uint16_t AObj,int32_t Axis_ID0,int32_t Axis_ID1);

MT_API int32_t __stdcall MT_M_Set_Axis_Line_Axis(int32_t ADev,uint16_t AObj,int32_t Axis_ID0,int32_t Axis_ID1);

//设置直线插补加速度
MT_API int32_t __stdcall MT_Set_Axis_Line_Acc(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Axis_Line_Acc(int32_t ADev,uint16_t AObj,int32_t Value);

//设置直线插补减速度
MT_API int32_t __stdcall MT_Set_Axis_Line_Dec(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Axis_Line_Dec(int32_t ADev,uint16_t AObj,int32_t Value);

//设置直线插补速度
MT_API int32_t __stdcall MT_Set_Axis_Line_V(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Axis_Line_V(int32_t ADev,uint16_t AObj,int32_t Value);

//设置直线插补启动
MT_API int32_t __stdcall MT_Set_Axis_Line_Run(uint16_t AObj);

MT_API int32_t __stdcall MT_M_Set_Axis_Line_Run(int32_t ADev,uint16_t AObj);

//设置直线插补停止
MT_API int32_t __stdcall MT_Set_Axis_Line_Stop(uint16_t AObj);

MT_API int32_t __stdcall MT_M_Set_Axis_Line_Stop(int32_t ADev,uint16_t AObj);

//设置直线插补急停
MT_API int32_t __stdcall MT_Set_Axis_Line_Halt(uint16_t AObj);

MT_API int32_t __stdcall MT_M_Set_Axis_Line_Halt(int32_t ADev,uint16_t AObj);

//设置直线插补相对移动目标
MT_API int32_t __stdcall MT_Set_Axis_Line_Rel(uint16_t AObj,int32_t Axis_Target0,int32_t Axis_Target1);

MT_API int32_t __stdcall MT_M_Set_Axis_Line_Rel(int32_t ADev,uint16_t AObj,int32_t Axis_Target0,int32_t Axis_Target1);

//设置直线插补绝对移动目标
MT_API int32_t __stdcall MT_Set_Axis_Line_Abs(uint16_t AObj,int32_t Axis_Target0,int32_t Axis_Target1);

MT_API int32_t __stdcall MT_M_Set_Axis_Line_Abs(int32_t ADev,uint16_t AObj,int32_t Axis_Target0,int32_t Axis_Target1);

//设置直线插补启动
MT_API int32_t __stdcall MT_Set_Axis_Line_Run_Rel(uint16_t AObj,int32_t Axis_Target0,int32_t Axis_Target1);

MT_API int32_t __stdcall MT_M_Set_Axis_Line_Run_Rel(int32_t ADev,uint16_t AObj,int32_t Axis_Target0,int32_t Axis_Target1);

MT_API int32_t __stdcall MT_Set_Axis_Line_Run_Abs(uint16_t AObj,int32_t Axis_Target0,int32_t Axis_Target1);

MT_API int32_t __stdcall MT_M_Set_Axis_Line_Run_Abs(int32_t ADev,uint16_t AObj,int32_t Axis_Target0,int32_t Axis_Target1);

//读取直线插补模块
MT_API int32_t __stdcall MT_Get_Axis_Line_Num(int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Axis_Line_Num(int32_t ADev,int32_t* pValue);

//插补运动状态
MT_API int32_t __stdcall MT_Get_Axis_Line_Status(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Axis_Line_Status(int32_t ADev,uint16_t AObj,int32_t* pValue);

//插补轴
MT_API int32_t __stdcall MT_Get_Axis_Line_Axis(uint16_t AObj,int32_t* pID0,int32_t* pID1);

MT_API int32_t __stdcall MT_M_Get_Axis_Line_Axis(int32_t ADev,uint16_t AObj,int32_t* pID0,int32_t* pID1);

//插补加速度
MT_API int32_t __stdcall MT_Get_Axis_Line_Acc(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Axis_Line_Acc(int32_t ADev,uint16_t AObj,int32_t* pValue);

//插补减速度
MT_API int32_t __stdcall MT_Get_Axis_Line_Dec(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Axis_Line_Dec(int32_t ADev,uint16_t AObj,int32_t* pValue);

//插补速度
MT_API int32_t __stdcall MT_Get_Axis_Line_V(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Axis_Line_V(int32_t ADev,uint16_t AObj,int32_t* pValue);

//====================================================================
//AD输入
//======================================================================
//通道数
MT_API int32_t __stdcall MT_Get_AD_Num(int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_AD_Num(int32_t ADev,int32_t* pValue);

//读取单通道值
MT_API int32_t __stdcall MT_Get_AD_Data(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_AD_Data(int32_t ADev,uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_Get_Board_T(int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Board_T(int32_t ADev,int32_t* pValue);

//2020 01 05 外部温度传感器
MT_API int32_t __stdcall MT_Get_T_Num(int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_T_Num(int32_t ADev,int32_t* pValue);

MT_API int32_t __stdcall MT_Get_T_Float(uint16_t AObj,float* pValue);

MT_API int32_t __stdcall MT_M_Get_T_Float(int32_t ADev,uint16_t AObj,float* pValue);

MT_API int32_t __stdcall MT_Get_T(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_T(int32_t ADev,uint16_t AObj,int32_t* pValue);

//2020 01 05 PWM设置
MT_API int32_t __stdcall MT_Get_PWM_Num(int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_PWM_Num(int32_t ADev,int32_t* pValue);

MT_API int32_t __stdcall MT_Set_PWM_F(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_PWM_F(int32_t ADev,uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_Get_PWM_F(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_PWM_F(int32_t ADev,uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_Set_PWM_F_Float(uint16_t AObj,float Value);

MT_API int32_t __stdcall MT_M_Set_PWM_F_Float(int32_t ADev,uint16_t AObj,float Value);

MT_API int32_t __stdcall MT_Get_PWM_F_Float(uint16_t AObj,float* pValue);

MT_API int32_t __stdcall MT_M_Get_PWM_F_Float(int32_t ADev,uint16_t AObj,float* pValue);

MT_API int32_t __stdcall MT_Set_PWM01(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_PWM01(int32_t ADev,uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_Get_PWM01(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_PWM01(int32_t ADev,uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_Set_PWM001(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_PWM001(int32_t ADev,uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_Get_PWM001(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_PWM001(int32_t ADev,uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_Set_PWM_Float(uint16_t AObj,float Value);

MT_API int32_t __stdcall MT_M_Set_PWM_Float(int32_t ADev,uint16_t AObj,float Value);

MT_API int32_t __stdcall MT_Get_PWM_Float(uint16_t AObj,float* pValue);

MT_API int32_t __stdcall MT_M_Get_PWM_Float(int32_t ADev,uint16_t AObj,float* pValue);

//================================================================
//圆弧插补
//================================================================
//设置圆弧插补主轴及速度
MT_API int32_t __stdcall MT_Set_Axis_Circle_Axis(uint16_t AObj,int32_t Axis_ID0,int32_t Axis_ID1);

MT_API int32_t __stdcall MT_M_Set_Axis_Circle_Axis(int32_t ADev,uint16_t AObj,int32_t Axis_ID0,int32_t Axis_ID1);

//设置圆弧插补加速度
MT_API int32_t __stdcall MT_Set_Axis_Circle_Acc(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Axis_Circle_Acc(int32_t ADev,uint16_t AObj,int32_t Value);

//设置圆弧插补减速度
MT_API int32_t __stdcall MT_Set_Axis_Circle_Dec(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Axis_Circle_Dec(int32_t ADev,uint16_t AObj,int32_t Value);

//设置圆弧插补速度
MT_API int32_t __stdcall MT_Set_Axis_Circle_V(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Axis_Circle_V(int32_t ADev,uint16_t AObj,int32_t Value);

//设置圆弧插补启动 顺时钟  圆心坐标模式
MT_API int32_t __stdcall MT_Set_Axis_Circle_R_CW_Run_Rel(uint16_t AObj,int32_t AR,int32_t Axis_Target0,int32_t Axis_Target1);

MT_API int32_t __stdcall MT_M_Set_Axis_Circle_R_CW_Run_Rel(int32_t ADev,uint16_t AObj,int32_t AR,int32_t Axis_Target0,int32_t Axis_Target1);

MT_API int32_t __stdcall MT_Set_Axis_Circle_R_CW_Run_Abs(uint16_t AObj,int32_t AR,int32_t Axis_Target0,int32_t Axis_Target1);

MT_API int32_t __stdcall MT_M_Set_Axis_Circle_R_CW_Run_Abs(int32_t ADev,uint16_t AObj,int32_t AR,int32_t Axis_Target0,int32_t Axis_Target1);

//设置圆弧插补启动 逆时钟   圆心坐标
MT_API int32_t __stdcall MT_Set_Axis_Circle_R_CCW_Run_Rel(uint16_t AObj,int32_t AR,int32_t Axis_Target0,int32_t Axis_Target1);

MT_API int32_t __stdcall MT_M_Set_Axis_Circle_R_CCW_Run_Rel(int32_t ADev,uint16_t AObj,int32_t AR,int32_t Axis_Target0,int32_t Axis_Target1);

MT_API int32_t __stdcall MT_Set_Axis_Circle_R_CCW_Run_Abs(uint16_t AObj,int32_t AR,int32_t Axis_Target0,int32_t Axis_Target1);

MT_API int32_t __stdcall MT_M_Set_Axis_Circle_R_CCW_Run_Abs(int32_t ADev,uint16_t AObj,int32_t AR,int32_t Axis_Target0,int32_t Axis_Target1);

//设置圆弧插补停止
MT_API int32_t __stdcall MT_Set_Axis_Circle_Stop(uint16_t AObj);

MT_API int32_t __stdcall MT_M_Set_Axis_Circle_Stop(int32_t ADev,uint16_t AObj);

//设置圆弧插补急停
MT_API int32_t __stdcall MT_Set_Axis_Circle_Halt(uint16_t AObj);

MT_API int32_t __stdcall MT_M_Set_Axis_Circle_Halt(int32_t ADev,uint16_t AObj);

//读取圆弧插补模块
MT_API int32_t __stdcall MT_Get_Axis_Circle_Num(int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Axis_Circle_Num(int32_t ADev,int32_t* pValue);

//插补运动状态
MT_API int32_t __stdcall MT_Get_Axis_Circle_Status(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Axis_Circle_Status(int32_t ADev,uint16_t AObj,int32_t* pValue);

//插补轴
MT_API int32_t __stdcall MT_Get_Axis_Circle_Axis(uint16_t AObj,int32_t* pID0,int32_t* pID1);

MT_API int32_t __stdcall MT_M_Get_Axis_Circle_Axis(int32_t ADev,uint16_t AObj,int32_t* pID0,int32_t* pID1);

//插补加速度
MT_API int32_t __stdcall MT_Get_Axis_Circle_Acc(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Axis_Circle_Acc(int32_t ADev,uint16_t AObj,int32_t* pValue);

//插补减速度
MT_API int32_t __stdcall MT_Get_Axis_Circle_Dec(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Axis_Circle_Dec(int32_t ADev,uint16_t AObj,int32_t* pValue);

//插补速度
MT_API int32_t __stdcall MT_Get_Axis_Circle_V(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Axis_Circle_V(int32_t ADev,uint16_t AObj,int32_t* pValue);

//2014 04 09补充定义 增加起始速度修改 增加多轴联动直线插补
MT_API int32_t __stdcall MT_Set_Axis_Home_V_Start(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Axis_Home_V_Start(int32_t ADev,uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_Set_Axis_Home_Acc(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Axis_Home_Acc(int32_t ADev,uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_Set_Axis_Home_Dec(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Axis_Home_Dec(int32_t ADev,uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_Get_Axis_Home_Acc(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Axis_Home_Acc(int32_t ADev,uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_Get_Axis_Home_Dec(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Axis_Home_Dec(int32_t ADev,uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_Set_Axis_Velocity_V_Start(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Axis_Velocity_V_Start(int32_t ADev,uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_Set_Axis_Velocity_Acc(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Axis_Velocity_Acc(int32_t ADev,uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_Set_Axis_Velocity_Dec(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Axis_Velocity_Dec(int32_t ADev,uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_Get_Axis_Velocity_Acc(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Axis_Velocity_Acc(int32_t ADev,uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_Get_Axis_Velocity_Dec(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Axis_Velocity_Dec(int32_t ADev,uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_Set_Axis_Position_V_Start(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Axis_Position_V_Start(int32_t ADev,uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_Set_Axis_Position_Acc(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Axis_Position_Acc(int32_t ADev,uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_Set_Axis_Position_Dec(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Axis_Position_Dec(int32_t ADev,uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_Get_Axis_Position_Acc(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Axis_Position_Acc(int32_t ADev,uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_Get_Axis_Position_Dec(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Axis_Position_Dec(int32_t ADev,uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_Set_Axis_Line_V_Start(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Axis_Line_V_Start(int32_t ADev,uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_Set_Axis_Circle_V_Start(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Axis_Circle_V_Start(int32_t ADev,uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_Set_Axis_Line_X_Run_Rel(uint16_t AObj,int32_t AAxis_Num,int32_t* pAxis,int32_t* pTarget);

MT_API int32_t __stdcall MT_M_Set_Axis_Line_X_Run_Rel(int32_t ADev,uint16_t AObj,int32_t AAxis_Num,int32_t* pAxis,int32_t* pTarget);

MT_API int32_t __stdcall MT_Set_Axis_Line_X_Run_Abs(uint16_t AObj,int32_t AAxis_Num,int32_t* pAxis,int32_t* pTarget);

MT_API int32_t __stdcall MT_M_Set_Axis_Line_X_Run_Abs(int32_t ADev,uint16_t AObj,int32_t AAxis_Num,int32_t* pAxis,int32_t* pTarget);

MT_API int32_t __stdcall MT_Set_Axis_Line_X_Target_Rel(uint16_t AObj,int32_t AAxisID,int32_t ATarget);

MT_API int32_t __stdcall MT_M_Set_Axis_Line_X_Target_Rel(int32_t ADev,uint16_t AObj,int32_t AAxisID,int32_t ATarget);

MT_API int32_t __stdcall MT_Set_Axis_Line_X_Target_Abs(uint16_t AObj,int32_t AAxisID,int32_t ATarget);

MT_API int32_t __stdcall MT_M_Set_Axis_Line_X_Target_Abs(int32_t ADev,uint16_t AObj,int32_t AAxisID,int32_t ATarget);

MT_API int32_t __stdcall MT_Set_Axis_Line_X_Axis(uint16_t AObj,int32_t AAxisID,int32_t AAxis);

MT_API int32_t __stdcall MT_M_Set_Axis_Line_X_Axis(int32_t ADev,uint16_t AObj,int32_t AAxisID,int32_t AAxis);

MT_API int32_t __stdcall MT_Set_Axis_Line_X_Count(uint16_t AObj,int32_t ANum);

MT_API int32_t __stdcall MT_M_Set_Axis_Line_X_Count(int32_t ADev,uint16_t AObj,int32_t ANum);

//PLC相关的函数
//PLC相关的指令码
//读变量存储器大小
MT_API int32_t __stdcall MT_Get_PLC_Var_Num(int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_PLC_Var_Num(int32_t ADev,int32_t* pValue);

//读变量
MT_API int32_t __stdcall MT_Get_PLC_Var_Data(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_PLC_Var_Data(int32_t ADev,uint16_t AObj,int32_t* pValue);

//写变量
MT_API int32_t __stdcall MT_Set_PLC_Var_Data(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_PLC_Var_Data(int32_t ADev,uint16_t AObj,int32_t Value);

//暂停PLC
MT_API int32_t __stdcall MT_Set_PLC_Pause(void);

MT_API int32_t __stdcall MT_M_Set_PLC_Pause(int32_t ADev);

//停止PLC
MT_API int32_t __stdcall MT_Set_PLC_Stop(void);

MT_API int32_t __stdcall MT_M_Set_PLC_Stop(int32_t ADev);

//启动PLC程序
MT_API int32_t __stdcall MT_Set_PLC_Run(void);

MT_API int32_t __stdcall MT_M_Set_PLC_Run(int32_t ADev);

//设置PLC程序代码
MT_API int32_t __stdcall MT_Set_PLC_Data(uint16_t AObj,uint8_t Value);

MT_API int32_t __stdcall MT_M_Set_PLC_Data(int32_t ADev,uint16_t AObj,uint8_t Value);

//读取PLC程序代码大小
MT_API int32_t __stdcall MT_Get_PLC_Code_Size(int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_PLC_Code_Size(int32_t ADev,int32_t* pValue);

//2017 01 30 PLC V6 Add
//读取任务个数
//PLC任务数
MT_API int32_t __stdcall MT_Get_PLC_Task_Count(int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_PLC_Task_Count(int32_t ADev,int32_t* pValue);

//PLC任务状态
MT_API int32_t __stdcall MT_Get_PLC_Task_Status(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_PLC_Task_Status(int32_t ADev,uint16_t AObj,int32_t* pValue);

//变量分割
MT_API int32_t __stdcall MT_Get_PLC_Var_Seg(int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_PLC_Var_Seg(int32_t ADev,int32_t* pValue);

//变量个数
MT_API int32_t __stdcall MT_Get_PLC_Var_Used(int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_PLC_Var_Used(int32_t ADev,int32_t* pValue);

//PLC状态
MT_API int32_t __stdcall MT_Get_PLC_Status(int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_PLC_Status(int32_t ADev,int32_t* pValue);

//全局状态
MT_API int32_t __stdcall MT_Get_PLC_Tasks_Status(int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_PLC_Tasks_Status(int32_t ADev,int32_t* pValue);

//Axis Ratio
MT_API int32_t __stdcall MT_Get_PLC_Axis_Ratio(uint16_t AObj,float* pValue);

MT_API int32_t __stdcall MT_M_Get_PLC_Axis_Ratio(int32_t ADev,uint16_t AObj,float* pValue);

MT_API int32_t __stdcall MT_Get_PLC_Encoder_Ratio(uint16_t AObj,float* pValue);

MT_API int32_t __stdcall MT_M_Get_PLC_Encoder_Ratio(int32_t ADev,uint16_t AObj,float* pValue);

//流指令模式
//启动Stream
MT_API int32_t __stdcall MT_Set_Stream_Run(void);

MT_API int32_t __stdcall MT_M_Set_Stream_Run(int32_t ADev);

//停止Stream
MT_API int32_t __stdcall MT_Set_Stream_Stop(void);

MT_API int32_t __stdcall MT_M_Set_Stream_Stop(int32_t ADev);

//暂停Stream
MT_API int32_t __stdcall MT_Set_Stream_Pause(void);

MT_API int32_t __stdcall MT_M_Set_Stream_Pause(int32_t ADev);

//清除Stream
MT_API int32_t __stdcall MT_Set_Stream_Clear(void);

MT_API int32_t __stdcall MT_M_Set_Stream_Clear(int32_t ADev);

//读取剩余空间
MT_API int32_t __stdcall MT_Get_Stream_Space(int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Stream_Space(int32_t ADev,int32_t* pValue);

//读取总空间
MT_API int32_t __stdcall MT_Get_Stream_Total(int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Stream_Total(int32_t ADev,int32_t* pValue);

//读取总空间
MT_API int32_t __stdcall MT_Get_Stream_Count(int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Stream_Count(int32_t ADev,int32_t* pValue);

//以下指令在broadcast中存储并由Stream处理
MT_API int32_t __stdcall MT_Set_Stream_Delay(int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Stream_Delay(int32_t ADev,int32_t Value);

//直线插补运动
//设置直线插补加速度
MT_API int32_t __stdcall MT_Set_Stream_Line_Acc(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Stream_Line_Acc(int32_t ADev,uint16_t AObj,int32_t Value);

//设置直线插补减速度
MT_API int32_t __stdcall MT_Set_Stream_Line_Dec(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Stream_Line_Dec(int32_t ADev,uint16_t AObj,int32_t Value);

//设置直线插补速度
MT_API int32_t __stdcall MT_Set_Stream_Line_V_Max(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Stream_Line_V_Max(int32_t ADev,uint16_t AObj,int32_t Value);

//设置直线插补启动速度
MT_API int32_t __stdcall MT_Set_Stream_Line_V_Start(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Stream_Line_V_Start(int32_t ADev,uint16_t AObj,int32_t Value);

//设置直线插补停止
MT_API int32_t __stdcall MT_Set_Stream_Line_Stop(uint16_t AObj);

MT_API int32_t __stdcall MT_M_Set_Stream_Line_Stop(int32_t ADev,uint16_t AObj);

//设置直线插补急停
MT_API int32_t __stdcall MT_Set_Stream_Line_Halt(uint16_t AObj);

MT_API int32_t __stdcall MT_M_Set_Stream_Line_Halt(int32_t ADev,uint16_t AObj);

//启动直线插补
MT_API int32_t __stdcall MT_Set_Stream_Line_X_Run_Rel(uint16_t AObj,int32_t AAxis_Num,int32_t* pAxis,int32_t* pTarget);

MT_API int32_t __stdcall MT_M_Set_Stream_Line_X_Run_Rel(int32_t ADev,uint16_t AObj,int32_t AAxis_Num,int32_t* pAxis,int32_t* pTarget);

MT_API int32_t __stdcall MT_Set_Stream_Line_X_Run_Abs(uint16_t AObj,int32_t AAxis_Num,int32_t* pAxis,int32_t* pTarget);

MT_API int32_t __stdcall MT_M_Set_Stream_Line_X_Run_Abs(int32_t ADev,uint16_t AObj,int32_t AAxis_Num,int32_t* pAxis,int32_t* pTarget);

//设置圆弧插补主轴及速度
MT_API int32_t __stdcall MT_Set_Stream_Circle_Axis(uint16_t AObj,int32_t Axis_ID0,int32_t Axis_ID1);

MT_API int32_t __stdcall MT_M_Set_Stream_Circle_Axis(int32_t ADev,uint16_t AObj,int32_t Axis_ID0,int32_t Axis_ID1);

//设置圆弧插补加速度
MT_API int32_t __stdcall MT_Set_Stream_Circle_Acc(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Stream_Circle_Acc(int32_t ADev,uint16_t AObj,int32_t Value);

//设置圆弧插补减速度
MT_API int32_t __stdcall MT_Set_Stream_Circle_Dec(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Stream_Circle_Dec(int32_t ADev,uint16_t AObj,int32_t Value);

//设置圆弧插补速度
MT_API int32_t __stdcall MT_Set_Stream_Circle_V_Max(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Stream_Circle_V_Max(int32_t ADev,uint16_t AObj,int32_t Value);

//设置圆弧插补启动速度
MT_API int32_t __stdcall MT_Set_Stream_Circle_V_Start(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Stream_Circle_V_Start(int32_t ADev,uint16_t AObj,int32_t Value);

//设置圆弧插补启动 顺时钟  圆心坐标模式
MT_API int32_t __stdcall MT_Set_Stream_Circle_R_CW_Run_Rel(uint16_t AObj,int32_t AR,int32_t Axis_Target0,int32_t Axis_Target1);

MT_API int32_t __stdcall MT_M_Set_Stream_Circle_R_CW_Run_Rel(int32_t ADev,uint16_t AObj,int32_t AR,int32_t Axis_Target0,int32_t Axis_Target1);

MT_API int32_t __stdcall MT_Set_Stream_Circle_R_CW_Run_Abs(uint16_t AObj,int32_t AR,int32_t Axis_Target0,int32_t Axis_Target1);

MT_API int32_t __stdcall MT_M_Set_Stream_Circle_R_CW_Run_Abs(int32_t ADev,uint16_t AObj,int32_t AR,int32_t Axis_Target0,int32_t Axis_Target1);

//设置圆弧插补启动 逆时钟   圆心坐标
MT_API int32_t __stdcall MT_Set_Stream_Circle_R_CCW_Run_Rel(uint16_t AObj,int32_t AR,int32_t Axis_Target0,int32_t Axis_Target1);

MT_API int32_t __stdcall MT_M_Set_Stream_Circle_R_CCW_Run_Rel(int32_t ADev,uint16_t AObj,int32_t AR,int32_t Axis_Target0,int32_t Axis_Target1);

MT_API int32_t __stdcall MT_Set_Stream_Circle_R_CCW_Run_Abs(uint16_t AObj,int32_t AR,int32_t Axis_Target0,int32_t Axis_Target1);

MT_API int32_t __stdcall MT_M_Set_Stream_Circle_R_CCW_Run_Abs(int32_t ADev,uint16_t AObj,int32_t AR,int32_t Axis_Target0,int32_t Axis_Target1);

//设置圆弧插补停止
MT_API int32_t __stdcall MT_Set_Stream_Circle_Stop(uint16_t AObj);

MT_API int32_t __stdcall MT_M_Set_Stream_Circle_Stop(int32_t ADev,uint16_t AObj);

//设置圆弧插补急停
MT_API int32_t __stdcall MT_Set_Stream_Circle_Halt(uint16_t AObj);

MT_API int32_t __stdcall MT_M_Set_Stream_Circle_Halt(int32_t ADev,uint16_t AObj);

MT_API int32_t __stdcall MT_Set_Stream_Wait_Line(uint16_t AObj);

MT_API int32_t __stdcall MT_M_Set_Stream_Wait_Line(int32_t ADev,uint16_t AObj);

MT_API int32_t __stdcall MT_Set_Stream_Wait_Circle(uint16_t AObj);

MT_API int32_t __stdcall MT_M_Set_Stream_Wait_Circle(int32_t ADev,uint16_t AObj);

//设置单通道值
MT_API int32_t __stdcall MT_Set_Stream_OC_Out_Single(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Stream_OC_Out_Single(int32_t ADev,uint16_t AObj,int32_t Value);

//设置所有通道值
MT_API int32_t __stdcall MT_Set_Stream_OC_Out_All(int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Stream_OC_Out_All(int32_t ADev,int32_t Value);

//设置单通道值
MT_API int32_t __stdcall MT_Set_Stream_Optic_Out_Single(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Stream_Optic_Out_Single(int32_t ADev,uint16_t AObj,int32_t Value);

//设置所有通道值
MT_API int32_t __stdcall MT_Set_Stream_Optic_Out_All(int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Stream_Optic_Out_All(int32_t ADev,int32_t Value);

//减速功能
MT_API int32_t __stdcall MT_Set_Stream_Dec_Enable(void);

MT_API int32_t __stdcall MT_M_Set_Stream_Dec_Enable(int32_t ADev);

MT_API int32_t __stdcall MT_Set_Stream_Dec_Disable(void);

MT_API int32_t __stdcall MT_M_Set_Stream_Dec_Disable(int32_t ADev);

//2016 08 20 增加等待输入功能
//等待Optic_In状态
MT_API int32_t __stdcall MT_Set_Stream_Wait_Optic_In(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Stream_Wait_Optic_In(int32_t ADev,uint16_t AObj,int32_t Value);

//启动Stream,带密码校验功能
MT_API int32_t __stdcall MT_Set_Stream_Run_Check(void);

MT_API int32_t __stdcall MT_M_Set_Stream_Run_Check(int32_t ADev);

//2019 09 15 running id for UI
MT_API int32_t __stdcall MT_Set_Stream_Run_ID(int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Stream_Run_ID(int32_t ADev,int32_t Value);

MT_API int32_t __stdcall MT_Get_Stream_Run_ID(int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Stream_Run_ID(int32_t ADev,int32_t* pValue);

//编码器功能
MT_API int32_t __stdcall MT_Get_Encoder_Num(int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Encoder_Num(int32_t ADev,int32_t* pValue);

MT_API int32_t __stdcall MT_Get_Encoder_Pos(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Encoder_Pos(int32_t ADev,uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_Set_Encoder_Pos(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Encoder_Pos(int32_t ADev,uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_Set_Encoder_Z_Polarity(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Encoder_Z_Polarity(int32_t ADev,uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_Set_Encoder_Dir_Polarity(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Encoder_Dir_Polarity(int32_t ADev,uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_Get_Encoder_Index_Line_Count(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Encoder_Index_Line_Count(int32_t ADev,uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_Set_Encoder_Over_Enable(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Encoder_Over_Enable(int32_t ADev,uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_Set_Encoder_Over_Max(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Encoder_Over_Max(int32_t ADev,uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_Set_Encoder_Over_Stable(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Encoder_Over_Stable(int32_t ADev,uint16_t AObj,int32_t Value);

//高速主动数据上传
MT_API int32_t __stdcall MT_Get_Push_Data(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Push_Data(int32_t ADev,uint16_t AObj,int32_t* pValue);

//2021 04 24  同步触发相关接口
MT_API int32_t __stdcall MT_Set_Trigger_Enable(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Trigger_Enable(int32_t ADev,uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_Set_Trigger_Start(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Trigger_Start(int32_t ADev,uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_Set_Trigger_End(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Trigger_End(int32_t ADev,uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_Set_Trigger_Step(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Trigger_Step(int32_t ADev,uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_Set_Trigger_Width(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Trigger_Width(int32_t ADev,uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_Set_Trigger_Channel(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Trigger_Channel(int32_t ADev,uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_Set_Trigger_Polarity(uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_M_Set_Trigger_Polarity(int32_t ADev,uint16_t AObj,int32_t Value);

MT_API int32_t __stdcall MT_Get_Trigger_Enable(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Trigger_Enable(int32_t ADev,uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_Get_Trigger_Start(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Trigger_Start(int32_t ADev,uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_Get_Trigger_End(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Trigger_End(int32_t ADev,uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_Get_Trigger_Step(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Trigger_Step(int32_t ADev,uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_Get_Trigger_Width(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Trigger_Width(int32_t ADev,uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_Get_Trigger_Channel(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Trigger_Channel(int32_t ADev,uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_Get_Trigger_Polarity(uint16_t AObj,int32_t* pValue);

MT_API int32_t __stdcall MT_M_Get_Trigger_Polarity(int32_t ADev,uint16_t AObj,int32_t* pValue);

//辅助计算公式
//mm to pluse
MT_API int32_t __stdcall MT_Help_Step_Line_Real_To_Steps(double AStepAngle,int32_t ADiv,double APitch,double ALineRatio,double AValue);

MT_API int32_t __stdcall MT_Help_Step_Circle_Real_To_Steps(double AStepAngle,int32_t ADiv,double ACircleRatio,double AValue);

//pluse to mm
MT_API double __stdcall MT_Help_Step_Line_Steps_To_Real(double AStepAngle,int32_t ADiv,double APitch,double ALineRatio,int32_t AValue);

MT_API double __stdcall MT_Help_Step_Circle_Steps_To_Real(double AStepAngle,int32_t ADiv,double ACircleRatio,int32_t AValue);

//Encoder
//物理量到单位脉冲
MT_API int32_t __stdcall MT_Help_Encoder_Line_Real_To_Steps(double APitch,double ALineRatio,int32_t ALineCount,double AValue);

MT_API int32_t __stdcall MT_Help_Encoder_Circle_Real_To_Steps(double ACircleRatio,int32_t ALineCount,double AValue);

//pluse to mm
MT_API double __stdcall MT_Help_Encoder_Line_Steps_To_Real(double APitch,double ALineRatio,int32_t ALineCount,int32_t AValue);

MT_API double __stdcall MT_Help_Encoder_Circle_Steps_To_Real(double ACircleRatio,int32_t ALineCount,int32_t AValue);

//Grating
//物理量到单位脉冲
MT_API int32_t __stdcall MT_Help_Grating_Line_Real_To_Steps(double AUnit_um,double AValue);

MT_API int32_t __stdcall MT_Help_Grating_Circle_Real_To_Steps(int32_t ALineCount,double AValue);

//pluse to mm
MT_API double __stdcall MT_Help_Grating_Line_Steps_To_Real(double AUnit_um,int32_t AValue);

MT_API double __stdcall MT_Help_Grating_Circle_Steps_To_Real(int32_t ALineCount,int32_t AValue);

MT_API float __stdcall MT_Help_Encoder_Factor(double AStepAngle,int32_t ADiv,int32_t ALineCount);

//光栅尺安装在机械上，电机旋转并不一致，需要考虑机械的影响
MT_API float __stdcall MT_Help_Grating_Line_Factor(double AStepAngle,int32_t ADiv,double APitch,double ALineRatio,double AUnit_um);

MT_API float __stdcall MT_Help_Grating_Circle_Factor(double AStepAngle,int32_t ADiv,double ACircleRatio,int32_t ALineCount);

//定义内部资源类型
#endif

