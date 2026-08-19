/*
C#接口文件
4.4
*/
using System;
using System.Text;
using System.Runtime.InteropServices;
public class MT_API
{

public const Int32  R_OK =0;
public const Int32  RUN_OFF =0;
public const Int32  RUN_ON =1;
public const Int32  DIR_NEG =0;
public const Int32  DIR_POS =1;
public const Int32  LIMIT_ON =1;
public const Int32  LIMIT_OFF =0;
public const Int32  RESOURCE_MOTOR =0x00000001;
public const Int32  RESOURCE_TTL_IN =0x00000002;
public const Int32  RESOURCE_TTL_OUT =0x00000004;
public const Int32  RESOURCE_OPTIC_IN =0x00000008;
public const Int32  RESOURCE_OPTIC_OUT =0x00000010;
public const Int32  RESOURCE_AD =0x00000020;
public const Int32  RESOURCE_OC =0x00000040;
public const Int32  RESOURCE_LINE =0x00000080;
public const Int32  RESOURCE_CIRCLE =0x00000100;
public const Int32  RESOURCE_PLC =0x00000200;
public const Int32  RESOURCE_STREAM =0x00000400;
public const Int32  RESOURCE_ENCODER =0x00000800;
public const Int32  RESOURCE_PWM =0x00001000;
public const Int32  RESOURCE_T =0x00002000;
public const Int32  RESOURCE_TRIGGER =0x00004000;

//**************************************************//
// V4.3 updated 2020-04-24
//**************************************************//
//==================================================
//运行环境
//===================================================
//dll版本
//初始化窗口
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Init();

//关闭窗口
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_DeInit();

//获取dll版本号
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Dll_Version(ref String sVer);

//设置线程锁时间
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Thread_Timeout(UInt32 ms);

//======================================================
//通信口
//======================================================
//打开 UART
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Open_UART(String sCOM);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Open_UART_Unicode(String sCOM);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Open_UART(Int32 ADev,String sCOM);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Open_UART_Unicode(Int32 ADev,String sCOM);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Open_UART_ID(Int32 AID);

//关闭 UART
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Close_UART();

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Close_UART(Int32 ADev);

//打开USB,按系统顺序
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Open_USB();

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Open_USB(Int32 ADev);

//打开USB，按序列号指定
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Open_USB_SN(Int32 ADev,StringBuilder ASN);

//关闭USB
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Close_USB();

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Close_USB(Int32 ADev);

//打开网口
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Open_Net(Byte IP0,Byte IP1,Byte IP2,Byte IP3,UInt16 IPPort);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Open_Net(Int32 ADev,Byte IP0,Byte IP1,Byte IP2,Byte IP3,UInt16 IPPort);

//2021 04 20 字符串输入IP或者主机名
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Open_Net_Name(StringBuilder IP_or_Name,UInt16 IPPort);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Open_Net_Name(Int32 ADev,StringBuilder IP_or_Name,UInt16 IPPort);

//关闭网口
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Close_Net();

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Close_Net(Int32 ADev);

//=====================================================
//板卡检测
//=====================================================
//检测设备
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Check();

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Check(Int32 ADev);

//读取资源模块
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Product_Resource(ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Product_Resource(Int32 ADev,ref Int32 pValue);

//获取ID
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Product_ID(StringBuilder sID);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Product_ID(Int32 ADev,StringBuilder sID);

//获取SN
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Product_SN(StringBuilder sSN);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Product_SN(Int32 ADev,StringBuilder sSN);

//获取SN2
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Product_SN2(ref Byte sSN);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Product_SN2(Int32 ADev,ref Byte sSN);

//获取SN3
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Product_SN3(StringBuilder sSN);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Product_SN3(Int32 ADev,StringBuilder sSN);

//读取固件版本号
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Product_Version(ref Int32 pMajor,ref Int32 pMinor);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Product_Version(Int32 ADev,ref Int32 pMajor,ref Int32 pMinor);

//读取固件版本号
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Product_Version2(ref Int32 pMajor,ref Int32 pMinor,ref Int32 pRelease,ref Int32 pBuild);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Product_Version2(Int32 ADev,ref Int32 pMajor,ref Int32 pMinor,ref Int32 pRelease,ref Int32 pBuild);

//===================================================================
//电机相关
//====================================================================
//轴数
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Axis_Num(ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Axis_Num(Int32 ADev,ref Int32 pValue);

//读取加速度
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Axis_Acc(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Axis_Acc(Int32 ADev,UInt16 AObj,ref Int32 pValue);

//设置加速度
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Acc(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Acc(Int32 ADev,UInt16 AObj,Int32 Value);

//读取加速度
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Axis_Dec(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Axis_Dec(Int32 ADev,UInt16 AObj,ref Int32 pValue);

//设置加速度
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Dec(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Dec(Int32 ADev,UInt16 AObj,Int32 Value);

//读取工作模式
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Axis_Mode(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Axis_Mode(Int32 ADev,UInt16 AObj,ref Int32 pValue);

//设置速度模式
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Mode_Velocity(UInt16 AObj);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Mode_Velocity(Int32 ADev,UInt16 AObj);

//设置位置模式
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Mode_Position(UInt16 AObj);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Mode_Position(Int32 ADev,UInt16 AObj);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Mode_Position_Open(UInt16 AObj);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Mode_Position_Open(Int32 ADev,UInt16 AObj);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Mode_Position_Close(UInt16 AObj);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Mode_Position_Close(Int32 ADev,UInt16 AObj);

//读取速度模式目标速度
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Axis_Velocity_V_Target(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Axis_Velocity_V_Target(Int32 ADev,UInt16 AObj,ref Int32 pValue);

//设置速度模式目标速度
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Velocity_V_Target_Abs(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Velocity_V_Target_Abs(Int32 ADev,UInt16 AObj,Int32 Value);

//设置速度模式目标速度
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Velocity_V_Target_Rel(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Velocity_V_Target_Rel(Int32 ADev,UInt16 AObj,Int32 Value);

//停止速度模式
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Velocity_Stop(UInt16 AObj);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Velocity_Stop(Int32 ADev,UInt16 AObj);

//读取位置模式最大速度
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Axis_Position_V_Max(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Axis_Position_V_Max(Int32 ADev,UInt16 AObj,ref Int32 pValue);

//设置位置模式最大速度
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Position_V_Max(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Position_V_Max(Int32 ADev,UInt16 AObj,Int32 Value);

//读取位置模式目标
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Axis_Position_P_Target(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Axis_Position_P_Target(Int32 ADev,UInt16 AObj,ref Int32 pValue);

//设置位置模式目标
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Position_P_Target_Abs(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Position_P_Target_Abs(Int32 ADev,UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Position_P_Target_Rel(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Position_P_Target_Rel(Int32 ADev,UInt16 AObj,Int32 Value);

//停止位置模式
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Position_Stop(UInt16 AObj);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Position_Stop(Int32 ADev,UInt16 AObj);

//设置编码器比例,用在减速判断上
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Position_Close_Dec_Factor(UInt16 AObj,Single AFactor);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Position_Close_Dec_Factor(Int32 ADev,UInt16 AObj,Single AFactor);

//紧急停止
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Halt(UInt16 AObj);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Halt(Int32 ADev,UInt16 AObj);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Halt_All();

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Halt_All(Int32 ADev);

//////////////////////////////////////////////////////////////
///  状态相关
///  //////////////////////////////////////////////////////
//读取当前速度
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Axis_V_Now(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Axis_V_Now(Int32 ADev,UInt16 AObj,ref Int32 pValue);

//读取当前软件位置
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Axis_P_Now(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Axis_P_Now(Int32 ADev,UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Axis_Software_P_Now(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Axis_Software_P_Now(Int32 ADev,UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Axis_Software_P(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Axis_Software_P(Int32 ADev,UInt16 AObj,ref Int32 pValue);

//设置软件位置
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_P_Now(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_P_Now(Int32 ADev,UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Software_P(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Software_P(Int32 ADev,UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Software_P_Now(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Software_P_Now(Int32 ADev,UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Axis_Status(UInt16 AObj,ref Byte pRun,ref Byte pDir,ref Byte pNeg,ref Byte pPos,ref Byte pZero,ref Byte pMode);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Axis_Status(Int32 ADev,UInt16 AObj,ref Byte pRun,ref Byte pDir,ref Byte pNeg,ref Byte pPos,ref Byte pZero,ref Byte pMode);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Axis_Status2(UInt16 AObj,ref Int32 pRun,ref Int32 pDir,ref Int32 pNeg,ref Int32 pPos,ref Int32 pZero,ref Int32 pMode);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Axis_Status2(Int32 ADev,UInt16 AObj,ref Int32 pRun,ref Int32 pDir,ref Int32 pNeg,ref Int32 pPos,ref Int32 pZero,ref Int32 pMode);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Axis_Status_Run(UInt16 AObj,ref Int32 pRun);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Axis_Status_Run(Int32 ADev,UInt16 AObj,ref Int32 pRun);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Axis_Status_Dir(UInt16 AObj,ref Int32 pDir);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Axis_Status_Dir(Int32 ADev,UInt16 AObj,ref Int32 pDir);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Axis_Status_Neg(UInt16 AObj,ref Int32 pNeg);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Axis_Status_Neg(Int32 ADev,UInt16 AObj,ref Int32 pNeg);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Axis_Status_Pos(UInt16 AObj,ref Int32 pPos);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Axis_Status_Pos(Int32 ADev,UInt16 AObj,ref Int32 pPos);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Axis_Status_Zero(UInt16 AObj,ref Int32 pZero);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Axis_Status_Zero(Int32 ADev,UInt16 AObj,ref Int32 pZero);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Axis_Status_Mode(UInt16 AObj,ref Int32 pMode);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Axis_Status_Mode(Int32 ADev,UInt16 AObj,ref Int32 pMode);

//设置0位模式
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Mode_Home(UInt16 AObj);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Mode_Home(Int32 ADev,UInt16 AObj);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Mode_Home_Home_Switch(UInt16 AObj);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Mode_Home_Home_Switch(Int32 ADev,UInt16 AObj);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Mode_Home_Encoder_Index(UInt16 AObj);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Mode_Home_Encoder_Index(Int32 ADev,UInt16 AObj);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Mode_Home_Encoder_Home_Switch(UInt16 AObj);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Mode_Home_Encoder_Home_Switch(Int32 ADev,UInt16 AObj);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Mode_Home_Home_Zero(UInt16 AObj);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Mode_Home_Home_Zero(Int32 ADev,UInt16 AObj);

//设置0位模式目标速度
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Home_V(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Home_V(Int32 ADev,UInt16 AObj,Int32 Value);

//停止0位模式
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Home_Stop(UInt16 AObj);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Home_Stop(Int32 ADev,UInt16 AObj);

//软件限位
//设置软件限位值
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Software_Limit_Neg_Value(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Software_Limit_Neg_Value(Int32 ADev,UInt16 AObj,Int32 Value);

//设置软件限位值
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Software_Limit_Pos_Value(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Software_Limit_Pos_Value(Int32 ADev,UInt16 AObj,Int32 Value);

//使能软件限位模式
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Software_Limit_Enable(UInt16 AObj);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Software_Limit_Enable(Int32 ADev,UInt16 AObj);

//停止软件限位模式
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Software_Limit_Disable(UInt16 AObj);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Software_Limit_Disable(Int32 ADev,UInt16 AObj);

////////////////////////////////////////////////////////////////////////
//存储器
//读取存储器长度
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_System_Mem_Len(ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_System_Mem_Len(Int32 ADev,ref Int32 pValue);

//读取存储器数据
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_System_Mem_Data(UInt16 AObj,ref Byte pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_System_Mem_Data(Int32 ADev,UInt16 AObj,ref Byte pValue);

//设置存储器数据
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_System_Mem_Data(UInt16 AObj,Byte Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_System_Mem_Data(Int32 ADev,UInt16 AObj,Byte Value);

//====================================================================
// 系统参数存储器
//======================================================================
// 读取存储器长度
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Param_Mem_Len(ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Param_Mem_Len(Int32 ADev,ref Int32 pValue);

//读取存储器数据
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Param_Mem_Data(UInt16 AObj,ref Byte pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Param_Mem_Data(Int32 ADev,UInt16 AObj,ref Byte pValue);

//设置存储器数据
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Param_Mem_Data(UInt16 AObj,Byte Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Param_Mem_Data(Int32 ADev,UInt16 AObj,Byte Value);

//====================================================================
//光隔输入
//======================================================================
//通道数
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Optic_In_Num(ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Optic_In_Num(Int32 ADev,ref Int32 pValue);

//不算复用电机的限位和零位
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Optic_In_Basic_Num(ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Optic_In_Basic_Num(Int32 ADev,ref Int32 pValue);

//读取单通道值
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Optic_In_Single(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Optic_In_Single(Int32 ADev,UInt16 AObj,ref Int32 pValue);

//读取所有通道值
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Optic_In_All(ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Optic_In_All(Int32 ADev,ref Int32 pValue);

//====================================================================
//光隔输出
//======================================================================
//通道数
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Optic_Out_Num(ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Optic_Out_Num(Int32 ADev,ref Int32 pValue);

//设置单通道值
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Optic_Out_Single(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Optic_Out_Single(Int32 ADev,UInt16 AObj,Int32 Value);

//设置所有通道值
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Optic_Out_All(Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Optic_Out_All(Int32 ADev,Int32 Value);

//读取单通道值
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Optic_Out_Single(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Optic_Out_Single(Int32 ADev,UInt16 AObj,ref Int32 pValue);

//读取所有通道值
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Optic_Out_All(ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Optic_Out_All(Int32 ADev,ref Int32 pValue);

//====================================================================
//OC输出
//======================================================================
//通道数
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_OC_Out_Num(ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_OC_Out_Num(Int32 ADev,ref Int32 pValue);

//设置单通道值
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_OC_Out_Single(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_OC_Out_Single(Int32 ADev,UInt16 AObj,Int32 Value);

//设置所有通道值
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_OC_Out_All(Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_OC_Out_All(Int32 ADev,Int32 Value);

//读取单通道值
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_OC_Out_Single(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_OC_Out_Single(Int32 ADev,UInt16 AObj,ref Int32 pValue);

//读取所有通道值
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_OC_Out_All(ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_OC_Out_All(Int32 ADev,ref Int32 pValue);

//直线插补相关
//设置直线插补主轴及速度
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Line_Axis(UInt16 AObj,Int32 Axis_ID0,Int32 Axis_ID1);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Line_Axis(Int32 ADev,UInt16 AObj,Int32 Axis_ID0,Int32 Axis_ID1);

//设置直线插补加速度
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Line_Acc(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Line_Acc(Int32 ADev,UInt16 AObj,Int32 Value);

//设置直线插补减速度
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Line_Dec(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Line_Dec(Int32 ADev,UInt16 AObj,Int32 Value);

//设置直线插补速度
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Line_V(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Line_V(Int32 ADev,UInt16 AObj,Int32 Value);

//设置直线插补启动
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Line_Run(UInt16 AObj);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Line_Run(Int32 ADev,UInt16 AObj);

//设置直线插补停止
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Line_Stop(UInt16 AObj);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Line_Stop(Int32 ADev,UInt16 AObj);

//设置直线插补急停
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Line_Halt(UInt16 AObj);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Line_Halt(Int32 ADev,UInt16 AObj);

//设置直线插补相对移动目标
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Line_Rel(UInt16 AObj,Int32 Axis_Target0,Int32 Axis_Target1);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Line_Rel(Int32 ADev,UInt16 AObj,Int32 Axis_Target0,Int32 Axis_Target1);

//设置直线插补绝对移动目标
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Line_Abs(UInt16 AObj,Int32 Axis_Target0,Int32 Axis_Target1);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Line_Abs(Int32 ADev,UInt16 AObj,Int32 Axis_Target0,Int32 Axis_Target1);

//设置直线插补启动
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Line_Run_Rel(UInt16 AObj,Int32 Axis_Target0,Int32 Axis_Target1);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Line_Run_Rel(Int32 ADev,UInt16 AObj,Int32 Axis_Target0,Int32 Axis_Target1);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Line_Run_Abs(UInt16 AObj,Int32 Axis_Target0,Int32 Axis_Target1);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Line_Run_Abs(Int32 ADev,UInt16 AObj,Int32 Axis_Target0,Int32 Axis_Target1);

//读取直线插补模块
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Axis_Line_Num(ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Axis_Line_Num(Int32 ADev,ref Int32 pValue);

//插补运动状态
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Axis_Line_Status(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Axis_Line_Status(Int32 ADev,UInt16 AObj,ref Int32 pValue);

//插补轴
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Axis_Line_Axis(UInt16 AObj,ref Int32 pID0,ref Int32 pID1);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Axis_Line_Axis(Int32 ADev,UInt16 AObj,ref Int32 pID0,ref Int32 pID1);

//插补加速度
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Axis_Line_Acc(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Axis_Line_Acc(Int32 ADev,UInt16 AObj,ref Int32 pValue);

//插补减速度
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Axis_Line_Dec(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Axis_Line_Dec(Int32 ADev,UInt16 AObj,ref Int32 pValue);

//插补速度
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Axis_Line_V(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Axis_Line_V(Int32 ADev,UInt16 AObj,ref Int32 pValue);

//====================================================================
//AD输入
//======================================================================
//通道数
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_AD_Num(ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_AD_Num(Int32 ADev,ref Int32 pValue);

//读取单通道值
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_AD_Data(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_AD_Data(Int32 ADev,UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Board_T(ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Board_T(Int32 ADev,ref Int32 pValue);

//2020 01 05 外部温度传感器
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_T_Num(ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_T_Num(Int32 ADev,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_T_Float(UInt16 AObj,ref Single pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_T_Float(Int32 ADev,UInt16 AObj,ref Single pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_T(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_T(Int32 ADev,UInt16 AObj,ref Int32 pValue);

//2020 01 05 PWM设置
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_PWM_Num(ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_PWM_Num(Int32 ADev,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_PWM_F(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_PWM_F(Int32 ADev,UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_PWM_F(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_PWM_F(Int32 ADev,UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_PWM_F_Float(UInt16 AObj,Single Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_PWM_F_Float(Int32 ADev,UInt16 AObj,Single Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_PWM_F_Float(UInt16 AObj,ref Single pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_PWM_F_Float(Int32 ADev,UInt16 AObj,ref Single pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_PWM01(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_PWM01(Int32 ADev,UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_PWM01(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_PWM01(Int32 ADev,UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_PWM001(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_PWM001(Int32 ADev,UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_PWM001(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_PWM001(Int32 ADev,UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_PWM_Float(UInt16 AObj,Single Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_PWM_Float(Int32 ADev,UInt16 AObj,Single Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_PWM_Float(UInt16 AObj,ref Single pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_PWM_Float(Int32 ADev,UInt16 AObj,ref Single pValue);

//================================================================
//圆弧插补
//================================================================
//设置圆弧插补主轴及速度
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Circle_Axis(UInt16 AObj,Int32 Axis_ID0,Int32 Axis_ID1);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Circle_Axis(Int32 ADev,UInt16 AObj,Int32 Axis_ID0,Int32 Axis_ID1);

//设置圆弧插补加速度
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Circle_Acc(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Circle_Acc(Int32 ADev,UInt16 AObj,Int32 Value);

//设置圆弧插补减速度
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Circle_Dec(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Circle_Dec(Int32 ADev,UInt16 AObj,Int32 Value);

//设置圆弧插补速度
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Circle_V(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Circle_V(Int32 ADev,UInt16 AObj,Int32 Value);

//设置圆弧插补启动 顺时钟  圆心坐标模式
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Circle_R_CW_Run_Rel(UInt16 AObj,Int32 AR,Int32 Axis_Target0,Int32 Axis_Target1);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Circle_R_CW_Run_Rel(Int32 ADev,UInt16 AObj,Int32 AR,Int32 Axis_Target0,Int32 Axis_Target1);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Circle_R_CW_Run_Abs(UInt16 AObj,Int32 AR,Int32 Axis_Target0,Int32 Axis_Target1);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Circle_R_CW_Run_Abs(Int32 ADev,UInt16 AObj,Int32 AR,Int32 Axis_Target0,Int32 Axis_Target1);

//设置圆弧插补启动 逆时钟   圆心坐标
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Circle_R_CCW_Run_Rel(UInt16 AObj,Int32 AR,Int32 Axis_Target0,Int32 Axis_Target1);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Circle_R_CCW_Run_Rel(Int32 ADev,UInt16 AObj,Int32 AR,Int32 Axis_Target0,Int32 Axis_Target1);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Circle_R_CCW_Run_Abs(UInt16 AObj,Int32 AR,Int32 Axis_Target0,Int32 Axis_Target1);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Circle_R_CCW_Run_Abs(Int32 ADev,UInt16 AObj,Int32 AR,Int32 Axis_Target0,Int32 Axis_Target1);

//设置圆弧插补停止
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Circle_Stop(UInt16 AObj);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Circle_Stop(Int32 ADev,UInt16 AObj);

//设置圆弧插补急停
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Circle_Halt(UInt16 AObj);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Circle_Halt(Int32 ADev,UInt16 AObj);

//读取圆弧插补模块
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Axis_Circle_Num(ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Axis_Circle_Num(Int32 ADev,ref Int32 pValue);

//插补运动状态
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Axis_Circle_Status(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Axis_Circle_Status(Int32 ADev,UInt16 AObj,ref Int32 pValue);

//插补轴
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Axis_Circle_Axis(UInt16 AObj,ref Int32 pID0,ref Int32 pID1);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Axis_Circle_Axis(Int32 ADev,UInt16 AObj,ref Int32 pID0,ref Int32 pID1);

//插补加速度
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Axis_Circle_Acc(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Axis_Circle_Acc(Int32 ADev,UInt16 AObj,ref Int32 pValue);

//插补减速度
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Axis_Circle_Dec(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Axis_Circle_Dec(Int32 ADev,UInt16 AObj,ref Int32 pValue);

//插补速度
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Axis_Circle_V(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Axis_Circle_V(Int32 ADev,UInt16 AObj,ref Int32 pValue);

//2014 04 09补充定义 增加起始速度修改 增加多轴联动直线插补
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Home_V_Start(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Home_V_Start(Int32 ADev,UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Home_Acc(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Home_Acc(Int32 ADev,UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Home_Dec(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Home_Dec(Int32 ADev,UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Axis_Home_Acc(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Axis_Home_Acc(Int32 ADev,UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Axis_Home_Dec(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Axis_Home_Dec(Int32 ADev,UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Velocity_V_Start(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Velocity_V_Start(Int32 ADev,UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Velocity_Acc(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Velocity_Acc(Int32 ADev,UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Velocity_Dec(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Velocity_Dec(Int32 ADev,UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Axis_Velocity_Acc(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Axis_Velocity_Acc(Int32 ADev,UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Axis_Velocity_Dec(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Axis_Velocity_Dec(Int32 ADev,UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Position_V_Start(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Position_V_Start(Int32 ADev,UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Position_Acc(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Position_Acc(Int32 ADev,UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Position_Dec(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Position_Dec(Int32 ADev,UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Axis_Position_Acc(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Axis_Position_Acc(Int32 ADev,UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Axis_Position_Dec(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Axis_Position_Dec(Int32 ADev,UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Line_V_Start(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Line_V_Start(Int32 ADev,UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Circle_V_Start(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Circle_V_Start(Int32 ADev,UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Line_X_Run_Rel(UInt16 AObj,Int32 AAxis_Num,ref Int32 pAxis,ref Int32 pTarget);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Line_X_Run_Rel(Int32 ADev,UInt16 AObj,Int32 AAxis_Num,ref Int32 pAxis,ref Int32 pTarget);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Line_X_Run_Abs(UInt16 AObj,Int32 AAxis_Num,ref Int32 pAxis,ref Int32 pTarget);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Line_X_Run_Abs(Int32 ADev,UInt16 AObj,Int32 AAxis_Num,ref Int32 pAxis,ref Int32 pTarget);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Line_X_Target_Rel(UInt16 AObj,Int32 AAxisID,Int32 ATarget);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Line_X_Target_Rel(Int32 ADev,UInt16 AObj,Int32 AAxisID,Int32 ATarget);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Line_X_Target_Abs(UInt16 AObj,Int32 AAxisID,Int32 ATarget);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Line_X_Target_Abs(Int32 ADev,UInt16 AObj,Int32 AAxisID,Int32 ATarget);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Line_X_Axis(UInt16 AObj,Int32 AAxisID,Int32 AAxis);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Line_X_Axis(Int32 ADev,UInt16 AObj,Int32 AAxisID,Int32 AAxis);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Axis_Line_X_Count(UInt16 AObj,Int32 ANum);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Axis_Line_X_Count(Int32 ADev,UInt16 AObj,Int32 ANum);

//PLC相关的函数
//PLC相关的指令码
//读变量存储器大小
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_PLC_Var_Num(ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_PLC_Var_Num(Int32 ADev,ref Int32 pValue);

//读变量
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_PLC_Var_Data(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_PLC_Var_Data(Int32 ADev,UInt16 AObj,ref Int32 pValue);

//写变量
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_PLC_Var_Data(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_PLC_Var_Data(Int32 ADev,UInt16 AObj,Int32 Value);

//暂停PLC
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_PLC_Pause();

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_PLC_Pause(Int32 ADev);

//停止PLC
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_PLC_Stop();

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_PLC_Stop(Int32 ADev);

//启动PLC程序
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_PLC_Run();

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_PLC_Run(Int32 ADev);

//设置PLC程序代码
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_PLC_Data(UInt16 AObj,Byte Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_PLC_Data(Int32 ADev,UInt16 AObj,Byte Value);

//读取PLC程序代码大小
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_PLC_Code_Size(ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_PLC_Code_Size(Int32 ADev,ref Int32 pValue);

//2017 01 30 PLC V6 Add
//读取任务个数
//PLC任务数
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_PLC_Task_Count(ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_PLC_Task_Count(Int32 ADev,ref Int32 pValue);

//PLC任务状态
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_PLC_Task_Status(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_PLC_Task_Status(Int32 ADev,UInt16 AObj,ref Int32 pValue);

//变量分割
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_PLC_Var_Seg(ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_PLC_Var_Seg(Int32 ADev,ref Int32 pValue);

//变量个数
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_PLC_Var_Used(ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_PLC_Var_Used(Int32 ADev,ref Int32 pValue);

//PLC状态
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_PLC_Status(ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_PLC_Status(Int32 ADev,ref Int32 pValue);

//全局状态
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_PLC_Tasks_Status(ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_PLC_Tasks_Status(Int32 ADev,ref Int32 pValue);

//Axis Ratio
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_PLC_Axis_Ratio(UInt16 AObj,ref Single pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_PLC_Axis_Ratio(Int32 ADev,UInt16 AObj,ref Single pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_PLC_Encoder_Ratio(UInt16 AObj,ref Single pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_PLC_Encoder_Ratio(Int32 ADev,UInt16 AObj,ref Single pValue);

//流指令模式
//启动Stream
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Stream_Run();

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Stream_Run(Int32 ADev);

//停止Stream
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Stream_Stop();

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Stream_Stop(Int32 ADev);

//暂停Stream
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Stream_Pause();

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Stream_Pause(Int32 ADev);

//清除Stream
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Stream_Clear();

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Stream_Clear(Int32 ADev);

//读取剩余空间
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Stream_Space(ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Stream_Space(Int32 ADev,ref Int32 pValue);

//读取总空间
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Stream_Total(ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Stream_Total(Int32 ADev,ref Int32 pValue);

//读取总空间
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Stream_Count(ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Stream_Count(Int32 ADev,ref Int32 pValue);

//以下指令在broadcast中存储并由Stream处理
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Stream_Delay(Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Stream_Delay(Int32 ADev,Int32 Value);

//直线插补运动
//设置直线插补加速度
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Stream_Line_Acc(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Stream_Line_Acc(Int32 ADev,UInt16 AObj,Int32 Value);

//设置直线插补减速度
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Stream_Line_Dec(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Stream_Line_Dec(Int32 ADev,UInt16 AObj,Int32 Value);

//设置直线插补速度
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Stream_Line_V_Max(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Stream_Line_V_Max(Int32 ADev,UInt16 AObj,Int32 Value);

//设置直线插补启动速度
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Stream_Line_V_Start(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Stream_Line_V_Start(Int32 ADev,UInt16 AObj,Int32 Value);

//设置直线插补停止
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Stream_Line_Stop(UInt16 AObj);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Stream_Line_Stop(Int32 ADev,UInt16 AObj);

//设置直线插补急停
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Stream_Line_Halt(UInt16 AObj);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Stream_Line_Halt(Int32 ADev,UInt16 AObj);

//启动直线插补
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Stream_Line_X_Run_Rel(UInt16 AObj,Int32 AAxis_Num,ref Int32 pAxis,ref Int32 pTarget);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Stream_Line_X_Run_Rel(Int32 ADev,UInt16 AObj,Int32 AAxis_Num,ref Int32 pAxis,ref Int32 pTarget);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Stream_Line_X_Run_Abs(UInt16 AObj,Int32 AAxis_Num,ref Int32 pAxis,ref Int32 pTarget);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Stream_Line_X_Run_Abs(Int32 ADev,UInt16 AObj,Int32 AAxis_Num,ref Int32 pAxis,ref Int32 pTarget);

//设置圆弧插补主轴及速度
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Stream_Circle_Axis(UInt16 AObj,Int32 Axis_ID0,Int32 Axis_ID1);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Stream_Circle_Axis(Int32 ADev,UInt16 AObj,Int32 Axis_ID0,Int32 Axis_ID1);

//设置圆弧插补加速度
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Stream_Circle_Acc(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Stream_Circle_Acc(Int32 ADev,UInt16 AObj,Int32 Value);

//设置圆弧插补减速度
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Stream_Circle_Dec(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Stream_Circle_Dec(Int32 ADev,UInt16 AObj,Int32 Value);

//设置圆弧插补速度
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Stream_Circle_V_Max(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Stream_Circle_V_Max(Int32 ADev,UInt16 AObj,Int32 Value);

//设置圆弧插补启动速度
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Stream_Circle_V_Start(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Stream_Circle_V_Start(Int32 ADev,UInt16 AObj,Int32 Value);

//设置圆弧插补启动 顺时钟  圆心坐标模式
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Stream_Circle_R_CW_Run_Rel(UInt16 AObj,Int32 AR,Int32 Axis_Target0,Int32 Axis_Target1);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Stream_Circle_R_CW_Run_Rel(Int32 ADev,UInt16 AObj,Int32 AR,Int32 Axis_Target0,Int32 Axis_Target1);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Stream_Circle_R_CW_Run_Abs(UInt16 AObj,Int32 AR,Int32 Axis_Target0,Int32 Axis_Target1);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Stream_Circle_R_CW_Run_Abs(Int32 ADev,UInt16 AObj,Int32 AR,Int32 Axis_Target0,Int32 Axis_Target1);

//设置圆弧插补启动 逆时钟   圆心坐标
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Stream_Circle_R_CCW_Run_Rel(UInt16 AObj,Int32 AR,Int32 Axis_Target0,Int32 Axis_Target1);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Stream_Circle_R_CCW_Run_Rel(Int32 ADev,UInt16 AObj,Int32 AR,Int32 Axis_Target0,Int32 Axis_Target1);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Stream_Circle_R_CCW_Run_Abs(UInt16 AObj,Int32 AR,Int32 Axis_Target0,Int32 Axis_Target1);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Stream_Circle_R_CCW_Run_Abs(Int32 ADev,UInt16 AObj,Int32 AR,Int32 Axis_Target0,Int32 Axis_Target1);

//设置圆弧插补停止
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Stream_Circle_Stop(UInt16 AObj);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Stream_Circle_Stop(Int32 ADev,UInt16 AObj);

//设置圆弧插补急停
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Stream_Circle_Halt(UInt16 AObj);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Stream_Circle_Halt(Int32 ADev,UInt16 AObj);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Stream_Wait_Line(UInt16 AObj);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Stream_Wait_Line(Int32 ADev,UInt16 AObj);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Stream_Wait_Circle(UInt16 AObj);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Stream_Wait_Circle(Int32 ADev,UInt16 AObj);

//设置单通道值
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Stream_OC_Out_Single(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Stream_OC_Out_Single(Int32 ADev,UInt16 AObj,Int32 Value);

//设置所有通道值
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Stream_OC_Out_All(Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Stream_OC_Out_All(Int32 ADev,Int32 Value);

//设置单通道值
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Stream_Optic_Out_Single(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Stream_Optic_Out_Single(Int32 ADev,UInt16 AObj,Int32 Value);

//设置所有通道值
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Stream_Optic_Out_All(Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Stream_Optic_Out_All(Int32 ADev,Int32 Value);

//减速功能
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Stream_Dec_Enable();

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Stream_Dec_Enable(Int32 ADev);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Stream_Dec_Disable();

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Stream_Dec_Disable(Int32 ADev);

//2016 08 20 增加等待输入功能
//等待Optic_In状态
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Stream_Wait_Optic_In(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Stream_Wait_Optic_In(Int32 ADev,UInt16 AObj,Int32 Value);

//启动Stream,带密码校验功能
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Stream_Run_Check();

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Stream_Run_Check(Int32 ADev);

//2019 09 15 running id for UI
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Stream_Run_ID(Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Stream_Run_ID(Int32 ADev,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Stream_Run_ID(ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Stream_Run_ID(Int32 ADev,ref Int32 pValue);

//编码器功能
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Encoder_Num(ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Encoder_Num(Int32 ADev,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Encoder_Pos(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Encoder_Pos(Int32 ADev,UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Encoder_Pos(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Encoder_Pos(Int32 ADev,UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Encoder_Z_Polarity(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Encoder_Z_Polarity(Int32 ADev,UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Encoder_Dir_Polarity(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Encoder_Dir_Polarity(Int32 ADev,UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Encoder_Index_Line_Count(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Encoder_Index_Line_Count(Int32 ADev,UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Encoder_Over_Enable(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Encoder_Over_Enable(Int32 ADev,UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Encoder_Over_Max(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Encoder_Over_Max(Int32 ADev,UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Encoder_Over_Stable(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Encoder_Over_Stable(Int32 ADev,UInt16 AObj,Int32 Value);

//高速主动数据上传
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Push_Data(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Push_Data(Int32 ADev,UInt16 AObj,ref Int32 pValue);

//2021 04 24  同步触发相关接口
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Trigger_Enable(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Trigger_Enable(Int32 ADev,UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Trigger_Start(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Trigger_Start(Int32 ADev,UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Trigger_End(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Trigger_End(Int32 ADev,UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Trigger_Step(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Trigger_Step(Int32 ADev,UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Trigger_Width(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Trigger_Width(Int32 ADev,UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Trigger_Channel(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Trigger_Channel(Int32 ADev,UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Set_Trigger_Polarity(UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Set_Trigger_Polarity(Int32 ADev,UInt16 AObj,Int32 Value);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Trigger_Enable(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Trigger_Enable(Int32 ADev,UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Trigger_Start(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Trigger_Start(Int32 ADev,UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Trigger_End(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Trigger_End(Int32 ADev,UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Trigger_Step(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Trigger_Step(Int32 ADev,UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Trigger_Width(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Trigger_Width(Int32 ADev,UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Trigger_Channel(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Trigger_Channel(Int32 ADev,UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Get_Trigger_Polarity(UInt16 AObj,ref Int32 pValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_M_Get_Trigger_Polarity(Int32 ADev,UInt16 AObj,ref Int32 pValue);

//辅助计算公式
//mm to pluse
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Help_Step_Line_Real_To_Steps(Double AStepAngle,Int32 ADiv,Double APitch,Double ALineRatio,Double AValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Help_Step_Circle_Real_To_Steps(Double AStepAngle,Int32 ADiv,Double ACircleRatio,Double AValue);

//pluse to mm
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Double MT_Help_Step_Line_Steps_To_Real(Double AStepAngle,Int32 ADiv,Double APitch,Double ALineRatio,Int32 AValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Double MT_Help_Step_Circle_Steps_To_Real(Double AStepAngle,Int32 ADiv,Double ACircleRatio,Int32 AValue);

//Encoder
//物理量到单位脉冲
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Help_Encoder_Line_Real_To_Steps(Double APitch,Double ALineRatio,Int32 ALineCount,Double AValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Help_Encoder_Circle_Real_To_Steps(Double ACircleRatio,Int32 ALineCount,Double AValue);

//pluse to mm
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Double MT_Help_Encoder_Line_Steps_To_Real(Double APitch,Double ALineRatio,Int32 ALineCount,Int32 AValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Double MT_Help_Encoder_Circle_Steps_To_Real(Double ACircleRatio,Int32 ALineCount,Int32 AValue);

//Grating
//物理量到单位脉冲
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Help_Grating_Line_Real_To_Steps(Double AUnit_um,Double AValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Int32 MT_Help_Grating_Circle_Real_To_Steps(Int32 ALineCount,Double AValue);

//pluse to mm
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Double MT_Help_Grating_Line_Steps_To_Real(Double AUnit_um,Int32 AValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Double MT_Help_Grating_Circle_Steps_To_Real(Int32 ALineCount,Int32 AValue);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Single MT_Help_Encoder_Factor(Double AStepAngle,Int32 ADiv,Int32 ALineCount);

//光栅尺安装在机械上，电机旋转并不一致，需要考虑机械的影响
[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Single MT_Help_Grating_Line_Factor(Double AStepAngle,Int32 ADiv,Double APitch,Double ALineRatio,Double AUnit_um);

[DllImport("MT_API.dll",CharSet=CharSet.Ansi,CallingConvention=CallingConvention.StdCall)]
public static extern Single MT_Help_Grating_Circle_Factor(Double AStepAngle,Int32 ADiv,Double ACircleRatio,Int32 ALineCount);

//定义内部资源类型
}

