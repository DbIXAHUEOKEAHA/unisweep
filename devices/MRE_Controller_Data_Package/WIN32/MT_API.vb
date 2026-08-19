'VB.net接口文件
'4.4

Imports System
Imports System.Text
Imports System.Runtime.InteropServices
Public Class MT_API

Public Const R_OK =0
Public Const RUN_OFF =0
Public Const RUN_ON =1
Public Const DIR_NEG =0
Public Const DIR_POS =1
Public Const LIMIT_ON =1
Public Const LIMIT_OFF =0
Public Const RESOURCE_MOTOR =&H00000001
Public Const RESOURCE_TTL_IN =&H00000002
Public Const RESOURCE_TTL_OUT =&H00000004
Public Const RESOURCE_OPTIC_IN =&H00000008
Public Const RESOURCE_OPTIC_OUT =&H00000010
Public Const RESOURCE_AD =&H00000020
Public Const RESOURCE_OC =&H00000040
Public Const RESOURCE_LINE =&H00000080
Public Const RESOURCE_CIRCLE =&H00000100
Public Const RESOURCE_PLC =&H00000200
Public Const RESOURCE_STREAM =&H00000400
Public Const RESOURCE_ENCODER =&H00000800
Public Const RESOURCE_PWM =&H00001000
Public Const RESOURCE_T =&H00002000
Public Const RESOURCE_TRIGGER =&H00004000

'//**************************************************//
'// V4.3 updated 2020-04-24
'//**************************************************//
'//==================================================
'//运行环境
'//===================================================
'//dll版本
'//初始化窗口
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Init() As Integer
End Function

'//关闭窗口
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_DeInit() As Integer
End Function

'//获取dll版本号
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Dll_Version(ByRef sVer As String) As Integer
End Function

'//设置线程锁时间
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Thread_Timeout(ByVal ms As UInt32) As Integer
End Function

'//======================================================
'//通信口
'//======================================================
'//打开 UART
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Open_UART(ByVal sCOM As String) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Open_UART_Unicode(ByVal sCOM As String) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Open_UART(ByVal ADev As Int32,ByVal sCOM As String) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Open_UART_Unicode(ByVal ADev As Int32,ByVal sCOM As String) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Open_UART_ID(ByVal AID As Int32) As Integer
End Function

'//关闭 UART
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Close_UART() As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Close_UART(ByVal ADev As Int32) As Integer
End Function

'//打开USB,按系统顺序
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Open_USB() As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Open_USB(ByVal ADev As Int32) As Integer
End Function

'//打开USB，按序列号指定
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Open_USB_SN(ByVal ADev As Int32,ByRef ASN As StringBuilder) As Integer
End Function

'//关闭USB
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Close_USB() As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Close_USB(ByVal ADev As Int32) As Integer
End Function

'//打开网口
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Open_Net(ByVal IP0 As Byte,ByVal IP1 As Byte,ByVal IP2 As Byte,ByVal IP3 As Byte,ByVal IPPort As UInt16) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Open_Net(ByVal ADev As Int32,ByVal IP0 As Byte,ByVal IP1 As Byte,ByVal IP2 As Byte,ByVal IP3 As Byte,ByVal IPPort As UInt16) As Integer
End Function

'//2021 04 20 字符串输入IP或者主机名
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Open_Net_Name(ByRef IP_or_Name As StringBuilder,ByVal IPPort As UInt16) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Open_Net_Name(ByVal ADev As Int32,ByRef IP_or_Name As StringBuilder,ByVal IPPort As UInt16) As Integer
End Function

'//关闭网口
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Close_Net() As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Close_Net(ByVal ADev As Int32) As Integer
End Function

'//=====================================================
'//板卡检测
'//=====================================================
'//检测设备
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Check() As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Check(ByVal ADev As Int32) As Integer
End Function

'//读取资源模块
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Product_Resource(ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Product_Resource(ByVal ADev As Int32,ByRef pValue As Int32) As Integer
End Function

'//获取ID
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Product_ID(ByRef sID As StringBuilder) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Product_ID(ByVal ADev As Int32,ByRef sID As StringBuilder) As Integer
End Function

'//获取SN
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Product_SN(ByRef sSN As StringBuilder) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Product_SN(ByVal ADev As Int32,ByRef sSN As StringBuilder) As Integer
End Function

'//获取SN2
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Product_SN2(ByRef sSN As Byte) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Product_SN2(ByVal ADev As Int32,ByRef sSN As Byte) As Integer
End Function

'//获取SN3
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Product_SN3(ByRef sSN As StringBuilder) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Product_SN3(ByVal ADev As Int32,ByRef sSN As StringBuilder) As Integer
End Function

'//读取固件版本号
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Product_Version(ByRef pMajor As Int32,ByRef pMinor As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Product_Version(ByVal ADev As Int32,ByRef pMajor As Int32,ByRef pMinor As Int32) As Integer
End Function

'//读取固件版本号
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Product_Version2(ByRef pMajor As Int32,ByRef pMinor As Int32,ByRef pRelease As Int32,ByRef pBuild As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Product_Version2(ByVal ADev As Int32,ByRef pMajor As Int32,ByRef pMinor As Int32,ByRef pRelease As Int32,ByRef pBuild As Int32) As Integer
End Function

'//===================================================================
'//电机相关
'//====================================================================
'//轴数
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Axis_Num(ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Axis_Num(ByVal ADev As Int32,ByRef pValue As Int32) As Integer
End Function

'//读取加速度
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Axis_Acc(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Axis_Acc(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

'//设置加速度
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Acc(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Acc(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

'//读取加速度
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Axis_Dec(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Axis_Dec(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

'//设置加速度
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Dec(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Dec(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

'//读取工作模式
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Axis_Mode(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Axis_Mode(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

'//设置速度模式
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Mode_Velocity(ByVal AObj As UInt16) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Mode_Velocity(ByVal ADev As Int32,ByVal AObj As UInt16) As Integer
End Function

'//设置位置模式
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Mode_Position(ByVal AObj As UInt16) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Mode_Position(ByVal ADev As Int32,ByVal AObj As UInt16) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Mode_Position_Open(ByVal AObj As UInt16) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Mode_Position_Open(ByVal ADev As Int32,ByVal AObj As UInt16) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Mode_Position_Close(ByVal AObj As UInt16) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Mode_Position_Close(ByVal ADev As Int32,ByVal AObj As UInt16) As Integer
End Function

'//读取速度模式目标速度
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Axis_Velocity_V_Target(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Axis_Velocity_V_Target(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

'//设置速度模式目标速度
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Velocity_V_Target_Abs(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Velocity_V_Target_Abs(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

'//设置速度模式目标速度
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Velocity_V_Target_Rel(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Velocity_V_Target_Rel(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

'//停止速度模式
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Velocity_Stop(ByVal AObj As UInt16) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Velocity_Stop(ByVal ADev As Int32,ByVal AObj As UInt16) As Integer
End Function

'//读取位置模式最大速度
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Axis_Position_V_Max(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Axis_Position_V_Max(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

'//设置位置模式最大速度
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Position_V_Max(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Position_V_Max(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

'//读取位置模式目标
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Axis_Position_P_Target(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Axis_Position_P_Target(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

'//设置位置模式目标
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Position_P_Target_Abs(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Position_P_Target_Abs(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Position_P_Target_Rel(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Position_P_Target_Rel(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

'//停止位置模式
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Position_Stop(ByVal AObj As UInt16) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Position_Stop(ByVal ADev As Int32,ByVal AObj As UInt16) As Integer
End Function

'//设置编码器比例,用在减速判断上
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Position_Close_Dec_Factor(ByVal AObj As UInt16,ByVal AFactor As Single) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Position_Close_Dec_Factor(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal AFactor As Single) As Integer
End Function

'//紧急停止
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Halt(ByVal AObj As UInt16) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Halt(ByVal ADev As Int32,ByVal AObj As UInt16) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Halt_All() As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Halt_All(ByVal ADev As Int32) As Integer
End Function

'//////////////////////////////////////////////////////////////
'///  状态相关
'///  //////////////////////////////////////////////////////
'//读取当前速度
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Axis_V_Now(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Axis_V_Now(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

'//读取当前软件位置
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Axis_P_Now(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Axis_P_Now(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Axis_Software_P_Now(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Axis_Software_P_Now(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Axis_Software_P(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Axis_Software_P(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

'//设置软件位置
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_P_Now(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_P_Now(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Software_P(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Software_P(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Software_P_Now(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Software_P_Now(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Axis_Status(ByVal AObj As UInt16,ByRef pRun As Byte,ByRef pDir As Byte,ByRef pNeg As Byte,ByRef pPos As Byte,ByRef pZero As Byte,ByRef pMode As Byte) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Axis_Status(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pRun As Byte,ByRef pDir As Byte,ByRef pNeg As Byte,ByRef pPos As Byte,ByRef pZero As Byte,ByRef pMode As Byte) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Axis_Status2(ByVal AObj As UInt16,ByRef pRun As Int32,ByRef pDir As Int32,ByRef pNeg As Int32,ByRef pPos As Int32,ByRef pZero As Int32,ByRef pMode As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Axis_Status2(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pRun As Int32,ByRef pDir As Int32,ByRef pNeg As Int32,ByRef pPos As Int32,ByRef pZero As Int32,ByRef pMode As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Axis_Status_Run(ByVal AObj As UInt16,ByRef pRun As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Axis_Status_Run(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pRun As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Axis_Status_Dir(ByVal AObj As UInt16,ByRef pDir As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Axis_Status_Dir(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pDir As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Axis_Status_Neg(ByVal AObj As UInt16,ByRef pNeg As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Axis_Status_Neg(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pNeg As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Axis_Status_Pos(ByVal AObj As UInt16,ByRef pPos As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Axis_Status_Pos(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pPos As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Axis_Status_Zero(ByVal AObj As UInt16,ByRef pZero As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Axis_Status_Zero(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pZero As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Axis_Status_Mode(ByVal AObj As UInt16,ByRef pMode As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Axis_Status_Mode(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pMode As Int32) As Integer
End Function

'//设置0位模式
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Mode_Home(ByVal AObj As UInt16) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Mode_Home(ByVal ADev As Int32,ByVal AObj As UInt16) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Mode_Home_Home_Switch(ByVal AObj As UInt16) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Mode_Home_Home_Switch(ByVal ADev As Int32,ByVal AObj As UInt16) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Mode_Home_Encoder_Index(ByVal AObj As UInt16) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Mode_Home_Encoder_Index(ByVal ADev As Int32,ByVal AObj As UInt16) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Mode_Home_Encoder_Home_Switch(ByVal AObj As UInt16) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Mode_Home_Encoder_Home_Switch(ByVal ADev As Int32,ByVal AObj As UInt16) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Mode_Home_Home_Zero(ByVal AObj As UInt16) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Mode_Home_Home_Zero(ByVal ADev As Int32,ByVal AObj As UInt16) As Integer
End Function

'//设置0位模式目标速度
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Home_V(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Home_V(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

'//停止0位模式
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Home_Stop(ByVal AObj As UInt16) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Home_Stop(ByVal ADev As Int32,ByVal AObj As UInt16) As Integer
End Function

'//软件限位
'//设置软件限位值
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Software_Limit_Neg_Value(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Software_Limit_Neg_Value(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

'//设置软件限位值
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Software_Limit_Pos_Value(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Software_Limit_Pos_Value(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

'//使能软件限位模式
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Software_Limit_Enable(ByVal AObj As UInt16) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Software_Limit_Enable(ByVal ADev As Int32,ByVal AObj As UInt16) As Integer
End Function

'//停止软件限位模式
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Software_Limit_Disable(ByVal AObj As UInt16) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Software_Limit_Disable(ByVal ADev As Int32,ByVal AObj As UInt16) As Integer
End Function

'////////////////////////////////////////////////////////////////////////
'//存储器
'//读取存储器长度
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_System_Mem_Len(ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_System_Mem_Len(ByVal ADev As Int32,ByRef pValue As Int32) As Integer
End Function

'//读取存储器数据
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_System_Mem_Data(ByVal AObj As UInt16,ByRef pValue As Byte) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_System_Mem_Data(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Byte) As Integer
End Function

'//设置存储器数据
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_System_Mem_Data(ByVal AObj As UInt16,ByVal Value As Byte) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_System_Mem_Data(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Byte) As Integer
End Function

'//====================================================================
'// 系统参数存储器
'//======================================================================
'// 读取存储器长度
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Param_Mem_Len(ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Param_Mem_Len(ByVal ADev As Int32,ByRef pValue As Int32) As Integer
End Function

'//读取存储器数据
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Param_Mem_Data(ByVal AObj As UInt16,ByRef pValue As Byte) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Param_Mem_Data(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Byte) As Integer
End Function

'//设置存储器数据
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Param_Mem_Data(ByVal AObj As UInt16,ByVal Value As Byte) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Param_Mem_Data(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Byte) As Integer
End Function

'//====================================================================
'//光隔输入
'//======================================================================
'//通道数
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Optic_In_Num(ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Optic_In_Num(ByVal ADev As Int32,ByRef pValue As Int32) As Integer
End Function

'//不算复用电机的限位和零位
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Optic_In_Basic_Num(ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Optic_In_Basic_Num(ByVal ADev As Int32,ByRef pValue As Int32) As Integer
End Function

'//读取单通道值
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Optic_In_Single(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Optic_In_Single(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

'//读取所有通道值
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Optic_In_All(ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Optic_In_All(ByVal ADev As Int32,ByRef pValue As Int32) As Integer
End Function

'//====================================================================
'//光隔输出
'//======================================================================
'//通道数
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Optic_Out_Num(ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Optic_Out_Num(ByVal ADev As Int32,ByRef pValue As Int32) As Integer
End Function

'//设置单通道值
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Optic_Out_Single(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Optic_Out_Single(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

'//设置所有通道值
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Optic_Out_All(ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Optic_Out_All(ByVal ADev As Int32,ByVal Value As Int32) As Integer
End Function

'//读取单通道值
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Optic_Out_Single(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Optic_Out_Single(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

'//读取所有通道值
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Optic_Out_All(ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Optic_Out_All(ByVal ADev As Int32,ByRef pValue As Int32) As Integer
End Function

'//====================================================================
'//OC输出
'//======================================================================
'//通道数
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_OC_Out_Num(ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_OC_Out_Num(ByVal ADev As Int32,ByRef pValue As Int32) As Integer
End Function

'//设置单通道值
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_OC_Out_Single(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_OC_Out_Single(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

'//设置所有通道值
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_OC_Out_All(ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_OC_Out_All(ByVal ADev As Int32,ByVal Value As Int32) As Integer
End Function

'//读取单通道值
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_OC_Out_Single(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_OC_Out_Single(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

'//读取所有通道值
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_OC_Out_All(ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_OC_Out_All(ByVal ADev As Int32,ByRef pValue As Int32) As Integer
End Function

'//直线插补相关
'//设置直线插补主轴及速度
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Line_Axis(ByVal AObj As UInt16,ByVal Axis_ID0 As Int32,ByVal Axis_ID1 As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Line_Axis(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Axis_ID0 As Int32,ByVal Axis_ID1 As Int32) As Integer
End Function

'//设置直线插补加速度
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Line_Acc(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Line_Acc(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

'//设置直线插补减速度
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Line_Dec(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Line_Dec(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

'//设置直线插补速度
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Line_V(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Line_V(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

'//设置直线插补启动
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Line_Run(ByVal AObj As UInt16) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Line_Run(ByVal ADev As Int32,ByVal AObj As UInt16) As Integer
End Function

'//设置直线插补停止
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Line_Stop(ByVal AObj As UInt16) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Line_Stop(ByVal ADev As Int32,ByVal AObj As UInt16) As Integer
End Function

'//设置直线插补急停
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Line_Halt(ByVal AObj As UInt16) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Line_Halt(ByVal ADev As Int32,ByVal AObj As UInt16) As Integer
End Function

'//设置直线插补相对移动目标
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Line_Rel(ByVal AObj As UInt16,ByVal Axis_Target0 As Int32,ByVal Axis_Target1 As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Line_Rel(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Axis_Target0 As Int32,ByVal Axis_Target1 As Int32) As Integer
End Function

'//设置直线插补绝对移动目标
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Line_Abs(ByVal AObj As UInt16,ByVal Axis_Target0 As Int32,ByVal Axis_Target1 As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Line_Abs(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Axis_Target0 As Int32,ByVal Axis_Target1 As Int32) As Integer
End Function

'//设置直线插补启动
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Line_Run_Rel(ByVal AObj As UInt16,ByVal Axis_Target0 As Int32,ByVal Axis_Target1 As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Line_Run_Rel(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Axis_Target0 As Int32,ByVal Axis_Target1 As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Line_Run_Abs(ByVal AObj As UInt16,ByVal Axis_Target0 As Int32,ByVal Axis_Target1 As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Line_Run_Abs(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Axis_Target0 As Int32,ByVal Axis_Target1 As Int32) As Integer
End Function

'//读取直线插补模块
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Axis_Line_Num(ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Axis_Line_Num(ByVal ADev As Int32,ByRef pValue As Int32) As Integer
End Function

'//插补运动状态
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Axis_Line_Status(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Axis_Line_Status(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

'//插补轴
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Axis_Line_Axis(ByVal AObj As UInt16,ByRef pID0 As Int32,ByRef pID1 As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Axis_Line_Axis(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pID0 As Int32,ByRef pID1 As Int32) As Integer
End Function

'//插补加速度
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Axis_Line_Acc(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Axis_Line_Acc(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

'//插补减速度
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Axis_Line_Dec(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Axis_Line_Dec(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

'//插补速度
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Axis_Line_V(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Axis_Line_V(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

'//====================================================================
'//AD输入
'//======================================================================
'//通道数
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_AD_Num(ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_AD_Num(ByVal ADev As Int32,ByRef pValue As Int32) As Integer
End Function

'//读取单通道值
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_AD_Data(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_AD_Data(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Board_T(ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Board_T(ByVal ADev As Int32,ByRef pValue As Int32) As Integer
End Function

'//2020 01 05 外部温度传感器
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_T_Num(ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_T_Num(ByVal ADev As Int32,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_T_Float(ByVal AObj As UInt16,ByRef pValue As Single) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_T_Float(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Single) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_T(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_T(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

'//2020 01 05 PWM设置
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_PWM_Num(ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_PWM_Num(ByVal ADev As Int32,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_PWM_F(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_PWM_F(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_PWM_F(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_PWM_F(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_PWM_F_Float(ByVal AObj As UInt16,ByVal Value As Single) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_PWM_F_Float(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Single) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_PWM_F_Float(ByVal AObj As UInt16,ByRef pValue As Single) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_PWM_F_Float(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Single) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_PWM01(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_PWM01(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_PWM01(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_PWM01(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_PWM001(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_PWM001(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_PWM001(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_PWM001(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_PWM_Float(ByVal AObj As UInt16,ByVal Value As Single) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_PWM_Float(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Single) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_PWM_Float(ByVal AObj As UInt16,ByRef pValue As Single) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_PWM_Float(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Single) As Integer
End Function

'//================================================================
'//圆弧插补
'//================================================================
'//设置圆弧插补主轴及速度
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Circle_Axis(ByVal AObj As UInt16,ByVal Axis_ID0 As Int32,ByVal Axis_ID1 As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Circle_Axis(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Axis_ID0 As Int32,ByVal Axis_ID1 As Int32) As Integer
End Function

'//设置圆弧插补加速度
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Circle_Acc(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Circle_Acc(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

'//设置圆弧插补减速度
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Circle_Dec(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Circle_Dec(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

'//设置圆弧插补速度
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Circle_V(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Circle_V(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

'//设置圆弧插补启动 顺时钟  圆心坐标模式
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Circle_R_CW_Run_Rel(ByVal AObj As UInt16,ByVal AR As Int32,ByVal Axis_Target0 As Int32,ByVal Axis_Target1 As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Circle_R_CW_Run_Rel(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal AR As Int32,ByVal Axis_Target0 As Int32,ByVal Axis_Target1 As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Circle_R_CW_Run_Abs(ByVal AObj As UInt16,ByVal AR As Int32,ByVal Axis_Target0 As Int32,ByVal Axis_Target1 As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Circle_R_CW_Run_Abs(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal AR As Int32,ByVal Axis_Target0 As Int32,ByVal Axis_Target1 As Int32) As Integer
End Function

'//设置圆弧插补启动 逆时钟   圆心坐标
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Circle_R_CCW_Run_Rel(ByVal AObj As UInt16,ByVal AR As Int32,ByVal Axis_Target0 As Int32,ByVal Axis_Target1 As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Circle_R_CCW_Run_Rel(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal AR As Int32,ByVal Axis_Target0 As Int32,ByVal Axis_Target1 As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Circle_R_CCW_Run_Abs(ByVal AObj As UInt16,ByVal AR As Int32,ByVal Axis_Target0 As Int32,ByVal Axis_Target1 As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Circle_R_CCW_Run_Abs(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal AR As Int32,ByVal Axis_Target0 As Int32,ByVal Axis_Target1 As Int32) As Integer
End Function

'//设置圆弧插补停止
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Circle_Stop(ByVal AObj As UInt16) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Circle_Stop(ByVal ADev As Int32,ByVal AObj As UInt16) As Integer
End Function

'//设置圆弧插补急停
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Circle_Halt(ByVal AObj As UInt16) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Circle_Halt(ByVal ADev As Int32,ByVal AObj As UInt16) As Integer
End Function

'//读取圆弧插补模块
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Axis_Circle_Num(ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Axis_Circle_Num(ByVal ADev As Int32,ByRef pValue As Int32) As Integer
End Function

'//插补运动状态
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Axis_Circle_Status(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Axis_Circle_Status(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

'//插补轴
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Axis_Circle_Axis(ByVal AObj As UInt16,ByRef pID0 As Int32,ByRef pID1 As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Axis_Circle_Axis(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pID0 As Int32,ByRef pID1 As Int32) As Integer
End Function

'//插补加速度
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Axis_Circle_Acc(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Axis_Circle_Acc(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

'//插补减速度
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Axis_Circle_Dec(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Axis_Circle_Dec(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

'//插补速度
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Axis_Circle_V(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Axis_Circle_V(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

'//2014 04 09补充定义 增加起始速度修改 增加多轴联动直线插补
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Home_V_Start(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Home_V_Start(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Home_Acc(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Home_Acc(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Home_Dec(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Home_Dec(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Axis_Home_Acc(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Axis_Home_Acc(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Axis_Home_Dec(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Axis_Home_Dec(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Velocity_V_Start(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Velocity_V_Start(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Velocity_Acc(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Velocity_Acc(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Velocity_Dec(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Velocity_Dec(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Axis_Velocity_Acc(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Axis_Velocity_Acc(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Axis_Velocity_Dec(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Axis_Velocity_Dec(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Position_V_Start(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Position_V_Start(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Position_Acc(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Position_Acc(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Position_Dec(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Position_Dec(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Axis_Position_Acc(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Axis_Position_Acc(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Axis_Position_Dec(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Axis_Position_Dec(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Line_V_Start(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Line_V_Start(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Circle_V_Start(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Circle_V_Start(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Line_X_Run_Rel(ByVal AObj As UInt16,ByVal AAxis_Num As Int32,ByRef pAxis As Int32,ByRef pTarget As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Line_X_Run_Rel(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal AAxis_Num As Int32,ByRef pAxis As Int32,ByRef pTarget As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Line_X_Run_Abs(ByVal AObj As UInt16,ByVal AAxis_Num As Int32,ByRef pAxis As Int32,ByRef pTarget As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Line_X_Run_Abs(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal AAxis_Num As Int32,ByRef pAxis As Int32,ByRef pTarget As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Line_X_Target_Rel(ByVal AObj As UInt16,ByVal AAxisID As Int32,ByVal ATarget As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Line_X_Target_Rel(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal AAxisID As Int32,ByVal ATarget As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Line_X_Target_Abs(ByVal AObj As UInt16,ByVal AAxisID As Int32,ByVal ATarget As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Line_X_Target_Abs(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal AAxisID As Int32,ByVal ATarget As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Line_X_Axis(ByVal AObj As UInt16,ByVal AAxisID As Int32,ByVal AAxis As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Line_X_Axis(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal AAxisID As Int32,ByVal AAxis As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Axis_Line_X_Count(ByVal AObj As UInt16,ByVal ANum As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Axis_Line_X_Count(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal ANum As Int32) As Integer
End Function

'//PLC相关的函数
'//PLC相关的指令码
'//读变量存储器大小
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_PLC_Var_Num(ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_PLC_Var_Num(ByVal ADev As Int32,ByRef pValue As Int32) As Integer
End Function

'//读变量
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_PLC_Var_Data(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_PLC_Var_Data(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

'//写变量
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_PLC_Var_Data(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_PLC_Var_Data(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

'//暂停PLC
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_PLC_Pause() As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_PLC_Pause(ByVal ADev As Int32) As Integer
End Function

'//停止PLC
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_PLC_Stop() As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_PLC_Stop(ByVal ADev As Int32) As Integer
End Function

'//启动PLC程序
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_PLC_Run() As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_PLC_Run(ByVal ADev As Int32) As Integer
End Function

'//设置PLC程序代码
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_PLC_Data(ByVal AObj As UInt16,ByVal Value As Byte) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_PLC_Data(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Byte) As Integer
End Function

'//读取PLC程序代码大小
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_PLC_Code_Size(ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_PLC_Code_Size(ByVal ADev As Int32,ByRef pValue As Int32) As Integer
End Function

'//2017 01 30 PLC V6 Add
'//读取任务个数
'//PLC任务数
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_PLC_Task_Count(ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_PLC_Task_Count(ByVal ADev As Int32,ByRef pValue As Int32) As Integer
End Function

'//PLC任务状态
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_PLC_Task_Status(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_PLC_Task_Status(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

'//变量分割
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_PLC_Var_Seg(ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_PLC_Var_Seg(ByVal ADev As Int32,ByRef pValue As Int32) As Integer
End Function

'//变量个数
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_PLC_Var_Used(ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_PLC_Var_Used(ByVal ADev As Int32,ByRef pValue As Int32) As Integer
End Function

'//PLC状态
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_PLC_Status(ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_PLC_Status(ByVal ADev As Int32,ByRef pValue As Int32) As Integer
End Function

'//全局状态
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_PLC_Tasks_Status(ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_PLC_Tasks_Status(ByVal ADev As Int32,ByRef pValue As Int32) As Integer
End Function

'//Axis Ratio
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_PLC_Axis_Ratio(ByVal AObj As UInt16,ByRef pValue As Single) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_PLC_Axis_Ratio(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Single) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_PLC_Encoder_Ratio(ByVal AObj As UInt16,ByRef pValue As Single) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_PLC_Encoder_Ratio(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Single) As Integer
End Function

'//流指令模式
'//启动Stream
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Stream_Run() As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Stream_Run(ByVal ADev As Int32) As Integer
End Function

'//停止Stream
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Stream_Stop() As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Stream_Stop(ByVal ADev As Int32) As Integer
End Function

'//暂停Stream
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Stream_Pause() As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Stream_Pause(ByVal ADev As Int32) As Integer
End Function

'//清除Stream
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Stream_Clear() As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Stream_Clear(ByVal ADev As Int32) As Integer
End Function

'//读取剩余空间
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Stream_Space(ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Stream_Space(ByVal ADev As Int32,ByRef pValue As Int32) As Integer
End Function

'//读取总空间
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Stream_Total(ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Stream_Total(ByVal ADev As Int32,ByRef pValue As Int32) As Integer
End Function

'//读取总空间
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Stream_Count(ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Stream_Count(ByVal ADev As Int32,ByRef pValue As Int32) As Integer
End Function

'//以下指令在broadcast中存储并由Stream处理
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Stream_Delay(ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Stream_Delay(ByVal ADev As Int32,ByVal Value As Int32) As Integer
End Function

'//直线插补运动
'//设置直线插补加速度
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Stream_Line_Acc(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Stream_Line_Acc(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

'//设置直线插补减速度
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Stream_Line_Dec(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Stream_Line_Dec(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

'//设置直线插补速度
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Stream_Line_V_Max(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Stream_Line_V_Max(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

'//设置直线插补启动速度
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Stream_Line_V_Start(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Stream_Line_V_Start(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

'//设置直线插补停止
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Stream_Line_Stop(ByVal AObj As UInt16) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Stream_Line_Stop(ByVal ADev As Int32,ByVal AObj As UInt16) As Integer
End Function

'//设置直线插补急停
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Stream_Line_Halt(ByVal AObj As UInt16) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Stream_Line_Halt(ByVal ADev As Int32,ByVal AObj As UInt16) As Integer
End Function

'//启动直线插补
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Stream_Line_X_Run_Rel(ByVal AObj As UInt16,ByVal AAxis_Num As Int32,ByRef pAxis As Int32,ByRef pTarget As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Stream_Line_X_Run_Rel(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal AAxis_Num As Int32,ByRef pAxis As Int32,ByRef pTarget As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Stream_Line_X_Run_Abs(ByVal AObj As UInt16,ByVal AAxis_Num As Int32,ByRef pAxis As Int32,ByRef pTarget As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Stream_Line_X_Run_Abs(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal AAxis_Num As Int32,ByRef pAxis As Int32,ByRef pTarget As Int32) As Integer
End Function

'//设置圆弧插补主轴及速度
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Stream_Circle_Axis(ByVal AObj As UInt16,ByVal Axis_ID0 As Int32,ByVal Axis_ID1 As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Stream_Circle_Axis(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Axis_ID0 As Int32,ByVal Axis_ID1 As Int32) As Integer
End Function

'//设置圆弧插补加速度
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Stream_Circle_Acc(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Stream_Circle_Acc(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

'//设置圆弧插补减速度
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Stream_Circle_Dec(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Stream_Circle_Dec(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

'//设置圆弧插补速度
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Stream_Circle_V_Max(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Stream_Circle_V_Max(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

'//设置圆弧插补启动速度
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Stream_Circle_V_Start(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Stream_Circle_V_Start(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

'//设置圆弧插补启动 顺时钟  圆心坐标模式
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Stream_Circle_R_CW_Run_Rel(ByVal AObj As UInt16,ByVal AR As Int32,ByVal Axis_Target0 As Int32,ByVal Axis_Target1 As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Stream_Circle_R_CW_Run_Rel(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal AR As Int32,ByVal Axis_Target0 As Int32,ByVal Axis_Target1 As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Stream_Circle_R_CW_Run_Abs(ByVal AObj As UInt16,ByVal AR As Int32,ByVal Axis_Target0 As Int32,ByVal Axis_Target1 As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Stream_Circle_R_CW_Run_Abs(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal AR As Int32,ByVal Axis_Target0 As Int32,ByVal Axis_Target1 As Int32) As Integer
End Function

'//设置圆弧插补启动 逆时钟   圆心坐标
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Stream_Circle_R_CCW_Run_Rel(ByVal AObj As UInt16,ByVal AR As Int32,ByVal Axis_Target0 As Int32,ByVal Axis_Target1 As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Stream_Circle_R_CCW_Run_Rel(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal AR As Int32,ByVal Axis_Target0 As Int32,ByVal Axis_Target1 As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Stream_Circle_R_CCW_Run_Abs(ByVal AObj As UInt16,ByVal AR As Int32,ByVal Axis_Target0 As Int32,ByVal Axis_Target1 As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Stream_Circle_R_CCW_Run_Abs(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal AR As Int32,ByVal Axis_Target0 As Int32,ByVal Axis_Target1 As Int32) As Integer
End Function

'//设置圆弧插补停止
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Stream_Circle_Stop(ByVal AObj As UInt16) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Stream_Circle_Stop(ByVal ADev As Int32,ByVal AObj As UInt16) As Integer
End Function

'//设置圆弧插补急停
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Stream_Circle_Halt(ByVal AObj As UInt16) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Stream_Circle_Halt(ByVal ADev As Int32,ByVal AObj As UInt16) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Stream_Wait_Line(ByVal AObj As UInt16) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Stream_Wait_Line(ByVal ADev As Int32,ByVal AObj As UInt16) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Stream_Wait_Circle(ByVal AObj As UInt16) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Stream_Wait_Circle(ByVal ADev As Int32,ByVal AObj As UInt16) As Integer
End Function

'//设置单通道值
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Stream_OC_Out_Single(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Stream_OC_Out_Single(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

'//设置所有通道值
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Stream_OC_Out_All(ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Stream_OC_Out_All(ByVal ADev As Int32,ByVal Value As Int32) As Integer
End Function

'//设置单通道值
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Stream_Optic_Out_Single(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Stream_Optic_Out_Single(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

'//设置所有通道值
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Stream_Optic_Out_All(ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Stream_Optic_Out_All(ByVal ADev As Int32,ByVal Value As Int32) As Integer
End Function

'//减速功能
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Stream_Dec_Enable() As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Stream_Dec_Enable(ByVal ADev As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Stream_Dec_Disable() As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Stream_Dec_Disable(ByVal ADev As Int32) As Integer
End Function

'//2016 08 20 增加等待输入功能
'//等待Optic_In状态
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Stream_Wait_Optic_In(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Stream_Wait_Optic_In(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

'//启动Stream,带密码校验功能
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Stream_Run_Check() As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Stream_Run_Check(ByVal ADev As Int32) As Integer
End Function

'//2019 09 15 running id for UI
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Stream_Run_ID(ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Stream_Run_ID(ByVal ADev As Int32,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Stream_Run_ID(ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Stream_Run_ID(ByVal ADev As Int32,ByRef pValue As Int32) As Integer
End Function

'//编码器功能
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Encoder_Num(ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Encoder_Num(ByVal ADev As Int32,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Encoder_Pos(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Encoder_Pos(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Encoder_Pos(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Encoder_Pos(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Encoder_Z_Polarity(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Encoder_Z_Polarity(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Encoder_Dir_Polarity(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Encoder_Dir_Polarity(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Encoder_Index_Line_Count(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Encoder_Index_Line_Count(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Encoder_Over_Enable(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Encoder_Over_Enable(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Encoder_Over_Max(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Encoder_Over_Max(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Encoder_Over_Stable(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Encoder_Over_Stable(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

'//高速主动数据上传
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Push_Data(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Push_Data(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

'//2021 04 24  同步触发相关接口
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Trigger_Enable(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Trigger_Enable(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Trigger_Start(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Trigger_Start(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Trigger_End(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Trigger_End(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Trigger_Step(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Trigger_Step(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Trigger_Width(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Trigger_Width(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Trigger_Channel(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Trigger_Channel(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Set_Trigger_Polarity(ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Set_Trigger_Polarity(ByVal ADev As Int32,ByVal AObj As UInt16,ByVal Value As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Trigger_Enable(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Trigger_Enable(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Trigger_Start(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Trigger_Start(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Trigger_End(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Trigger_End(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Trigger_Step(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Trigger_Step(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Trigger_Width(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Trigger_Width(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Trigger_Channel(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Trigger_Channel(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Get_Trigger_Polarity(ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_M_Get_Trigger_Polarity(ByVal ADev As Int32,ByVal AObj As UInt16,ByRef pValue As Int32) As Integer
End Function

'//辅助计算公式
'//mm to pluse
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Help_Step_Line_Real_To_Steps(ByVal AStepAngle As Double,ByVal ADiv As Int32,ByVal APitch As Double,ByVal ALineRatio As Double,ByVal AValue As Double) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Help_Step_Circle_Real_To_Steps(ByVal AStepAngle As Double,ByVal ADiv As Int32,ByVal ACircleRatio As Double,ByVal AValue As Double) As Integer
End Function

'//pluse to mm
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Help_Step_Line_Steps_To_Real(ByVal AStepAngle As Double,ByVal ADiv As Int32,ByVal APitch As Double,ByVal ALineRatio As Double,ByVal AValue As Int32) As Double
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Help_Step_Circle_Steps_To_Real(ByVal AStepAngle As Double,ByVal ADiv As Int32,ByVal ACircleRatio As Double,ByVal AValue As Int32) As Double
End Function

'//Encoder
'//物理量到单位脉冲
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Help_Encoder_Line_Real_To_Steps(ByVal APitch As Double,ByVal ALineRatio As Double,ByVal ALineCount As Int32,ByVal AValue As Double) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Help_Encoder_Circle_Real_To_Steps(ByVal ACircleRatio As Double,ByVal ALineCount As Int32,ByVal AValue As Double) As Integer
End Function

'//pluse to mm
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Help_Encoder_Line_Steps_To_Real(ByVal APitch As Double,ByVal ALineRatio As Double,ByVal ALineCount As Int32,ByVal AValue As Int32) As Double
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Help_Encoder_Circle_Steps_To_Real(ByVal ACircleRatio As Double,ByVal ALineCount As Int32,ByVal AValue As Int32) As Double
End Function

'//Grating
'//物理量到单位脉冲
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Help_Grating_Line_Real_To_Steps(ByVal AUnit_um As Double,ByVal AValue As Double) As Integer
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Help_Grating_Circle_Real_To_Steps(ByVal ALineCount As Int32,ByVal AValue As Double) As Integer
End Function

'//pluse to mm
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Help_Grating_Line_Steps_To_Real(ByVal AUnit_um As Double,ByVal AValue As Int32) As Double
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Help_Grating_Circle_Steps_To_Real(ByVal ALineCount As Int32,ByVal AValue As Int32) As Double
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Help_Encoder_Factor(ByVal AStepAngle As Double,ByVal ADiv As Int32,ByVal ALineCount As Int32) As Single
End Function

'//光栅尺安装在机械上，电机旋转并不一致，需要考虑机械的影响
<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Help_Grating_Line_Factor(ByVal AStepAngle As Double,ByVal ADiv As Int32,ByVal APitch As Double,ByVal ALineRatio As Double,ByVal AUnit_um As Double) As Single
End Function

<DllImport("MT_API.dll", CharSet:=CharSet.Ansi, CallingConvention:=CallingConvention.Winapi)> Public Shared Function MT_Help_Grating_Circle_Factor(ByVal AStepAngle As Double,ByVal ADiv As Int32,ByVal ACircleRatio As Double,ByVal ALineCount As Int32) As Single
End Function

'//定义内部资源类型
End Class

