'VB接口文件
'4.4

Option Explicit

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
Declare Function MT_Init Lib "MT_API.dll" () As Long

'//关闭窗口
Declare Function MT_DeInit Lib "MT_API.dll" () As Long

'//获取dll版本号
Declare Function MT_Get_Dll_Version Lib "MT_API.dll" (ByRef sVer As String) As Long

'//设置线程锁时间
Declare Function MT_Set_Thread_Timeout Lib "MT_API.dll" (ByVal ms As Long) As Long

'//======================================================
'//通信口
'//======================================================
'//打开 UART
Declare Function MT_Open_UART Lib "MT_API.dll" (ByVal sCOM As String) As Long

Declare Function MT_Open_UART_Unicode Lib "MT_API.dll" (ByVal sCOM As String) As Long

Declare Function MT_M_Open_UART Lib "MT_API.dll" (ByVal ADev As Long,ByVal sCOM As String) As Long

Declare Function MT_M_Open_UART_Unicode Lib "MT_API.dll" (ByVal ADev As Long,ByVal sCOM As String) As Long

Declare Function MT_Open_UART_ID Lib "MT_API.dll" (ByVal AID As Long) As Long

'//关闭 UART
Declare Function MT_Close_UART Lib "MT_API.dll" () As Long

Declare Function MT_M_Close_UART Lib "MT_API.dll" (ByVal ADev As Long) As Long

'//打开USB,按系统顺序
Declare Function MT_Open_USB Lib "MT_API.dll" () As Long

Declare Function MT_M_Open_USB Lib "MT_API.dll" (ByVal ADev As Long) As Long

'//打开USB，按序列号指定
Declare Function MT_M_Open_USB_SN Lib "MT_API.dll" (ByVal ADev As Long,ByVal ASN As String) As Long

'//关闭USB
Declare Function MT_Close_USB Lib "MT_API.dll" () As Long

Declare Function MT_M_Close_USB Lib "MT_API.dll" (ByVal ADev As Long) As Long

'//打开网口
Declare Function MT_Open_Net Lib "MT_API.dll" (ByVal IP0 As Byte,ByVal IP1 As Byte,ByVal IP2 As Byte,ByVal IP3 As Byte,ByVal IPPort As Integer) As Long

Declare Function MT_M_Open_Net Lib "MT_API.dll" (ByVal ADev As Long,ByVal IP0 As Byte,ByVal IP1 As Byte,ByVal IP2 As Byte,ByVal IP3 As Byte,ByVal IPPort As Integer) As Long

'//2021 04 20 字符串输入IP或者主机名
Declare Function MT_Open_Net_Name Lib "MT_API.dll" (ByVal IP_or_Name As String,ByVal IPPort As Integer) As Long

Declare Function MT_M_Open_Net_Name Lib "MT_API.dll" (ByVal ADev As Long,ByVal IP_or_Name As String,ByVal IPPort As Integer) As Long

'//关闭网口
Declare Function MT_Close_Net Lib "MT_API.dll" () As Long

Declare Function MT_M_Close_Net Lib "MT_API.dll" (ByVal ADev As Long) As Long

'//=====================================================
'//板卡检测
'//=====================================================
'//检测设备
Declare Function MT_Check Lib "MT_API.dll" () As Long

Declare Function MT_M_Check Lib "MT_API.dll" (ByVal ADev As Long) As Long

'//读取资源模块
Declare Function MT_Get_Product_Resource Lib "MT_API.dll" (ByRef pValue As Long) As Long

Declare Function MT_M_Get_Product_Resource Lib "MT_API.dll" (ByVal ADev As Long,ByRef pValue As Long) As Long

'//获取ID
Declare Function MT_Get_Product_ID Lib "MT_API.dll" (ByVal sID As String) As Long

Declare Function MT_M_Get_Product_ID Lib "MT_API.dll" (ByVal ADev As Long,ByVal sID As String) As Long

'//获取SN
Declare Function MT_Get_Product_SN Lib "MT_API.dll" (ByVal sSN As String) As Long

Declare Function MT_M_Get_Product_SN Lib "MT_API.dll" (ByVal ADev As Long,ByVal sSN As String) As Long

'//获取SN2
Declare Function MT_Get_Product_SN2 Lib "MT_API.dll" (ByVal sSN As Long) As Long

Declare Function MT_M_Get_Product_SN2 Lib "MT_API.dll" (ByVal ADev As Long,ByVal sSN As Long) As Long

'//获取SN3
Declare Function MT_Get_Product_SN3 Lib "MT_API.dll" (ByVal sSN As String) As Long

Declare Function MT_M_Get_Product_SN3 Lib "MT_API.dll" (ByVal ADev As Long,ByVal sSN As String) As Long

'//读取固件版本号
Declare Function MT_Get_Product_Version Lib "MT_API.dll" (ByRef pMajor As Long,ByRef pMinor As Long) As Long

Declare Function MT_M_Get_Product_Version Lib "MT_API.dll" (ByVal ADev As Long,ByRef pMajor As Long,ByRef pMinor As Long) As Long

'//读取固件版本号
Declare Function MT_Get_Product_Version2 Lib "MT_API.dll" (ByRef pMajor As Long,ByRef pMinor As Long,ByRef pRelease As Long,ByRef pBuild As Long) As Long

Declare Function MT_M_Get_Product_Version2 Lib "MT_API.dll" (ByVal ADev As Long,ByRef pMajor As Long,ByRef pMinor As Long,ByRef pRelease As Long,ByRef pBuild As Long) As Long

'//===================================================================
'//电机相关
'//====================================================================
'//轴数
Declare Function MT_Get_Axis_Num Lib "MT_API.dll" (ByRef pValue As Long) As Long

Declare Function MT_M_Get_Axis_Num Lib "MT_API.dll" (ByVal ADev As Long,ByRef pValue As Long) As Long

'//读取加速度
Declare Function MT_Get_Axis_Acc Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_Axis_Acc Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

'//设置加速度
Declare Function MT_Set_Axis_Acc Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Axis_Acc Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

'//读取加速度
Declare Function MT_Get_Axis_Dec Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_Axis_Dec Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

'//设置加速度
Declare Function MT_Set_Axis_Dec Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Axis_Dec Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

'//读取工作模式
Declare Function MT_Get_Axis_Mode Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_Axis_Mode Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

'//设置速度模式
Declare Function MT_Set_Axis_Mode_Velocity Lib "MT_API.dll" (ByVal AObj As Integer) As Long

Declare Function MT_M_Set_Axis_Mode_Velocity Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer) As Long

'//设置位置模式
Declare Function MT_Set_Axis_Mode_Position Lib "MT_API.dll" (ByVal AObj As Integer) As Long

Declare Function MT_M_Set_Axis_Mode_Position Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer) As Long

Declare Function MT_Set_Axis_Mode_Position_Open Lib "MT_API.dll" (ByVal AObj As Integer) As Long

Declare Function MT_M_Set_Axis_Mode_Position_Open Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer) As Long

Declare Function MT_Set_Axis_Mode_Position_Close Lib "MT_API.dll" (ByVal AObj As Integer) As Long

Declare Function MT_M_Set_Axis_Mode_Position_Close Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer) As Long

'//读取速度模式目标速度
Declare Function MT_Get_Axis_Velocity_V_Target Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_Axis_Velocity_V_Target Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

'//设置速度模式目标速度
Declare Function MT_Set_Axis_Velocity_V_Target_Abs Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Axis_Velocity_V_Target_Abs Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

'//设置速度模式目标速度
Declare Function MT_Set_Axis_Velocity_V_Target_Rel Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Axis_Velocity_V_Target_Rel Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

'//停止速度模式
Declare Function MT_Set_Axis_Velocity_Stop Lib "MT_API.dll" (ByVal AObj As Integer) As Long

Declare Function MT_M_Set_Axis_Velocity_Stop Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer) As Long

'//读取位置模式最大速度
Declare Function MT_Get_Axis_Position_V_Max Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_Axis_Position_V_Max Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

'//设置位置模式最大速度
Declare Function MT_Set_Axis_Position_V_Max Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Axis_Position_V_Max Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

'//读取位置模式目标
Declare Function MT_Get_Axis_Position_P_Target Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_Axis_Position_P_Target Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

'//设置位置模式目标
Declare Function MT_Set_Axis_Position_P_Target_Abs Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Axis_Position_P_Target_Abs Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_Set_Axis_Position_P_Target_Rel Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Axis_Position_P_Target_Rel Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

'//停止位置模式
Declare Function MT_Set_Axis_Position_Stop Lib "MT_API.dll" (ByVal AObj As Integer) As Long

Declare Function MT_M_Set_Axis_Position_Stop Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer) As Long

'//设置编码器比例,用在减速判断上
Declare Function MT_Set_Axis_Position_Close_Dec_Factor Lib "MT_API.dll" (ByVal AObj As Integer,ByVal AFactor As Single) As Long

Declare Function MT_M_Set_Axis_Position_Close_Dec_Factor Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal AFactor As Single) As Long

'//紧急停止
Declare Function MT_Set_Axis_Halt Lib "MT_API.dll" (ByVal AObj As Integer) As Long

Declare Function MT_M_Set_Axis_Halt Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer) As Long

Declare Function MT_Set_Axis_Halt_All Lib "MT_API.dll" () As Long

Declare Function MT_M_Set_Axis_Halt_All Lib "MT_API.dll" (ByVal ADev As Long) As Long

'//////////////////////////////////////////////////////////////
'///  状态相关
'///  //////////////////////////////////////////////////////
'//读取当前速度
Declare Function MT_Get_Axis_V_Now Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_Axis_V_Now Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

'//读取当前软件位置
Declare Function MT_Get_Axis_P_Now Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_Axis_P_Now Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_Get_Axis_Software_P_Now Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_Axis_Software_P_Now Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_Get_Axis_Software_P Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_Axis_Software_P Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

'//设置软件位置
Declare Function MT_Set_Axis_P_Now Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Axis_P_Now Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_Set_Axis_Software_P Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Axis_Software_P Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_Set_Axis_Software_P_Now Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Axis_Software_P_Now Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_Get_Axis_Status Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pRun As Byte,ByRef pDir As Byte,ByRef pNeg As Byte,ByRef pPos As Byte,ByRef pZero As Byte,ByRef pMode As Byte) As Long

Declare Function MT_M_Get_Axis_Status Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pRun As Byte,ByRef pDir As Byte,ByRef pNeg As Byte,ByRef pPos As Byte,ByRef pZero As Byte,ByRef pMode As Byte) As Long

Declare Function MT_Get_Axis_Status2 Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pRun As Long,ByRef pDir As Long,ByRef pNeg As Long,ByRef pPos As Long,ByRef pZero As Long,ByRef pMode As Long) As Long

Declare Function MT_M_Get_Axis_Status2 Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pRun As Long,ByRef pDir As Long,ByRef pNeg As Long,ByRef pPos As Long,ByRef pZero As Long,ByRef pMode As Long) As Long

Declare Function MT_Get_Axis_Status_Run Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pRun As Long) As Long

Declare Function MT_M_Get_Axis_Status_Run Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pRun As Long) As Long

Declare Function MT_Get_Axis_Status_Dir Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pDir As Long) As Long

Declare Function MT_M_Get_Axis_Status_Dir Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pDir As Long) As Long

Declare Function MT_Get_Axis_Status_Neg Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pNeg As Long) As Long

Declare Function MT_M_Get_Axis_Status_Neg Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pNeg As Long) As Long

Declare Function MT_Get_Axis_Status_Pos Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pPos As Long) As Long

Declare Function MT_M_Get_Axis_Status_Pos Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pPos As Long) As Long

Declare Function MT_Get_Axis_Status_Zero Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pZero As Long) As Long

Declare Function MT_M_Get_Axis_Status_Zero Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pZero As Long) As Long

Declare Function MT_Get_Axis_Status_Mode Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pMode As Long) As Long

Declare Function MT_M_Get_Axis_Status_Mode Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pMode As Long) As Long

'//设置0位模式
Declare Function MT_Set_Axis_Mode_Home Lib "MT_API.dll" (ByVal AObj As Integer) As Long

Declare Function MT_M_Set_Axis_Mode_Home Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer) As Long

Declare Function MT_Set_Axis_Mode_Home_Home_Switch Lib "MT_API.dll" (ByVal AObj As Integer) As Long

Declare Function MT_M_Set_Axis_Mode_Home_Home_Switch Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer) As Long

Declare Function MT_Set_Axis_Mode_Home_Encoder_Index Lib "MT_API.dll" (ByVal AObj As Integer) As Long

Declare Function MT_M_Set_Axis_Mode_Home_Encoder_Index Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer) As Long

Declare Function MT_Set_Axis_Mode_Home_Encoder_Home_Switch Lib "MT_API.dll" (ByVal AObj As Integer) As Long

Declare Function MT_M_Set_Axis_Mode_Home_Encoder_Home_Switch Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer) As Long

Declare Function MT_Set_Axis_Mode_Home_Home_Zero Lib "MT_API.dll" (ByVal AObj As Integer) As Long

Declare Function MT_M_Set_Axis_Mode_Home_Home_Zero Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer) As Long

'//设置0位模式目标速度
Declare Function MT_Set_Axis_Home_V Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Axis_Home_V Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

'//停止0位模式
Declare Function MT_Set_Axis_Home_Stop Lib "MT_API.dll" (ByVal AObj As Integer) As Long

Declare Function MT_M_Set_Axis_Home_Stop Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer) As Long

'//软件限位
'//设置软件限位值
Declare Function MT_Set_Axis_Software_Limit_Neg_Value Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Axis_Software_Limit_Neg_Value Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

'//设置软件限位值
Declare Function MT_Set_Axis_Software_Limit_Pos_Value Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Axis_Software_Limit_Pos_Value Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

'//使能软件限位模式
Declare Function MT_Set_Axis_Software_Limit_Enable Lib "MT_API.dll" (ByVal AObj As Integer) As Long

Declare Function MT_M_Set_Axis_Software_Limit_Enable Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer) As Long

'//停止软件限位模式
Declare Function MT_Set_Axis_Software_Limit_Disable Lib "MT_API.dll" (ByVal AObj As Integer) As Long

Declare Function MT_M_Set_Axis_Software_Limit_Disable Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer) As Long

'////////////////////////////////////////////////////////////////////////
'//存储器
'//读取存储器长度
Declare Function MT_Get_System_Mem_Len Lib "MT_API.dll" (ByRef pValue As Long) As Long

Declare Function MT_M_Get_System_Mem_Len Lib "MT_API.dll" (ByVal ADev As Long,ByRef pValue As Long) As Long

'//读取存储器数据
Declare Function MT_Get_System_Mem_Data Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Byte) As Long

Declare Function MT_M_Get_System_Mem_Data Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Byte) As Long

'//设置存储器数据
Declare Function MT_Set_System_Mem_Data Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Byte) As Long

Declare Function MT_M_Set_System_Mem_Data Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Byte) As Long

'//====================================================================
'// 系统参数存储器
'//======================================================================
'// 读取存储器长度
Declare Function MT_Get_Param_Mem_Len Lib "MT_API.dll" (ByRef pValue As Long) As Long

Declare Function MT_M_Get_Param_Mem_Len Lib "MT_API.dll" (ByVal ADev As Long,ByRef pValue As Long) As Long

'//读取存储器数据
Declare Function MT_Get_Param_Mem_Data Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Byte) As Long

Declare Function MT_M_Get_Param_Mem_Data Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Byte) As Long

'//设置存储器数据
Declare Function MT_Set_Param_Mem_Data Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Byte) As Long

Declare Function MT_M_Set_Param_Mem_Data Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Byte) As Long

'//====================================================================
'//光隔输入
'//======================================================================
'//通道数
Declare Function MT_Get_Optic_In_Num Lib "MT_API.dll" (ByRef pValue As Long) As Long

Declare Function MT_M_Get_Optic_In_Num Lib "MT_API.dll" (ByVal ADev As Long,ByRef pValue As Long) As Long

'//不算复用电机的限位和零位
Declare Function MT_Get_Optic_In_Basic_Num Lib "MT_API.dll" (ByRef pValue As Long) As Long

Declare Function MT_M_Get_Optic_In_Basic_Num Lib "MT_API.dll" (ByVal ADev As Long,ByRef pValue As Long) As Long

'//读取单通道值
Declare Function MT_Get_Optic_In_Single Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_Optic_In_Single Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

'//读取所有通道值
Declare Function MT_Get_Optic_In_All Lib "MT_API.dll" (ByRef pValue As Long) As Long

Declare Function MT_M_Get_Optic_In_All Lib "MT_API.dll" (ByVal ADev As Long,ByRef pValue As Long) As Long

'//====================================================================
'//光隔输出
'//======================================================================
'//通道数
Declare Function MT_Get_Optic_Out_Num Lib "MT_API.dll" (ByRef pValue As Long) As Long

Declare Function MT_M_Get_Optic_Out_Num Lib "MT_API.dll" (ByVal ADev As Long,ByRef pValue As Long) As Long

'//设置单通道值
Declare Function MT_Set_Optic_Out_Single Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Optic_Out_Single Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

'//设置所有通道值
Declare Function MT_Set_Optic_Out_All Lib "MT_API.dll" (ByVal Value As Long) As Long

Declare Function MT_M_Set_Optic_Out_All Lib "MT_API.dll" (ByVal ADev As Long,ByVal Value As Long) As Long

'//读取单通道值
Declare Function MT_Get_Optic_Out_Single Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_Optic_Out_Single Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

'//读取所有通道值
Declare Function MT_Get_Optic_Out_All Lib "MT_API.dll" (ByRef pValue As Long) As Long

Declare Function MT_M_Get_Optic_Out_All Lib "MT_API.dll" (ByVal ADev As Long,ByRef pValue As Long) As Long

'//====================================================================
'//OC输出
'//======================================================================
'//通道数
Declare Function MT_Get_OC_Out_Num Lib "MT_API.dll" (ByRef pValue As Long) As Long

Declare Function MT_M_Get_OC_Out_Num Lib "MT_API.dll" (ByVal ADev As Long,ByRef pValue As Long) As Long

'//设置单通道值
Declare Function MT_Set_OC_Out_Single Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_OC_Out_Single Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

'//设置所有通道值
Declare Function MT_Set_OC_Out_All Lib "MT_API.dll" (ByVal Value As Long) As Long

Declare Function MT_M_Set_OC_Out_All Lib "MT_API.dll" (ByVal ADev As Long,ByVal Value As Long) As Long

'//读取单通道值
Declare Function MT_Get_OC_Out_Single Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_OC_Out_Single Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

'//读取所有通道值
Declare Function MT_Get_OC_Out_All Lib "MT_API.dll" (ByRef pValue As Long) As Long

Declare Function MT_M_Get_OC_Out_All Lib "MT_API.dll" (ByVal ADev As Long,ByRef pValue As Long) As Long

'//直线插补相关
'//设置直线插补主轴及速度
Declare Function MT_Set_Axis_Line_Axis Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Axis_ID0 As Long,ByVal Axis_ID1 As Long) As Long

Declare Function MT_M_Set_Axis_Line_Axis Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Axis_ID0 As Long,ByVal Axis_ID1 As Long) As Long

'//设置直线插补加速度
Declare Function MT_Set_Axis_Line_Acc Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Axis_Line_Acc Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

'//设置直线插补减速度
Declare Function MT_Set_Axis_Line_Dec Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Axis_Line_Dec Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

'//设置直线插补速度
Declare Function MT_Set_Axis_Line_V Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Axis_Line_V Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

'//设置直线插补启动
Declare Function MT_Set_Axis_Line_Run Lib "MT_API.dll" (ByVal AObj As Integer) As Long

Declare Function MT_M_Set_Axis_Line_Run Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer) As Long

'//设置直线插补停止
Declare Function MT_Set_Axis_Line_Stop Lib "MT_API.dll" (ByVal AObj As Integer) As Long

Declare Function MT_M_Set_Axis_Line_Stop Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer) As Long

'//设置直线插补急停
Declare Function MT_Set_Axis_Line_Halt Lib "MT_API.dll" (ByVal AObj As Integer) As Long

Declare Function MT_M_Set_Axis_Line_Halt Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer) As Long

'//设置直线插补相对移动目标
Declare Function MT_Set_Axis_Line_Rel Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Axis_Target0 As Long,ByVal Axis_Target1 As Long) As Long

Declare Function MT_M_Set_Axis_Line_Rel Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Axis_Target0 As Long,ByVal Axis_Target1 As Long) As Long

'//设置直线插补绝对移动目标
Declare Function MT_Set_Axis_Line_Abs Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Axis_Target0 As Long,ByVal Axis_Target1 As Long) As Long

Declare Function MT_M_Set_Axis_Line_Abs Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Axis_Target0 As Long,ByVal Axis_Target1 As Long) As Long

'//设置直线插补启动
Declare Function MT_Set_Axis_Line_Run_Rel Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Axis_Target0 As Long,ByVal Axis_Target1 As Long) As Long

Declare Function MT_M_Set_Axis_Line_Run_Rel Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Axis_Target0 As Long,ByVal Axis_Target1 As Long) As Long

Declare Function MT_Set_Axis_Line_Run_Abs Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Axis_Target0 As Long,ByVal Axis_Target1 As Long) As Long

Declare Function MT_M_Set_Axis_Line_Run_Abs Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Axis_Target0 As Long,ByVal Axis_Target1 As Long) As Long

'//读取直线插补模块
Declare Function MT_Get_Axis_Line_Num Lib "MT_API.dll" (ByRef pValue As Long) As Long

Declare Function MT_M_Get_Axis_Line_Num Lib "MT_API.dll" (ByVal ADev As Long,ByRef pValue As Long) As Long

'//插补运动状态
Declare Function MT_Get_Axis_Line_Status Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_Axis_Line_Status Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

'//插补轴
Declare Function MT_Get_Axis_Line_Axis Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pID0 As Long,ByRef pID1 As Long) As Long

Declare Function MT_M_Get_Axis_Line_Axis Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pID0 As Long,ByRef pID1 As Long) As Long

'//插补加速度
Declare Function MT_Get_Axis_Line_Acc Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_Axis_Line_Acc Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

'//插补减速度
Declare Function MT_Get_Axis_Line_Dec Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_Axis_Line_Dec Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

'//插补速度
Declare Function MT_Get_Axis_Line_V Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_Axis_Line_V Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

'//====================================================================
'//AD输入
'//======================================================================
'//通道数
Declare Function MT_Get_AD_Num Lib "MT_API.dll" (ByRef pValue As Long) As Long

Declare Function MT_M_Get_AD_Num Lib "MT_API.dll" (ByVal ADev As Long,ByRef pValue As Long) As Long

'//读取单通道值
Declare Function MT_Get_AD_Data Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_AD_Data Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_Get_Board_T Lib "MT_API.dll" (ByRef pValue As Long) As Long

Declare Function MT_M_Get_Board_T Lib "MT_API.dll" (ByVal ADev As Long,ByRef pValue As Long) As Long

'//2020 01 05 外部温度传感器
Declare Function MT_Get_T_Num Lib "MT_API.dll" (ByRef pValue As Long) As Long

Declare Function MT_M_Get_T_Num Lib "MT_API.dll" (ByVal ADev As Long,ByRef pValue As Long) As Long

Declare Function MT_Get_T_Float Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Single) As Long

Declare Function MT_M_Get_T_Float Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Single) As Long

Declare Function MT_Get_T Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_T Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

'//2020 01 05 PWM设置
Declare Function MT_Get_PWM_Num Lib "MT_API.dll" (ByRef pValue As Long) As Long

Declare Function MT_M_Get_PWM_Num Lib "MT_API.dll" (ByVal ADev As Long,ByRef pValue As Long) As Long

Declare Function MT_Set_PWM_F Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_PWM_F Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_Get_PWM_F Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_PWM_F Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_Set_PWM_F_Float Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Single) As Long

Declare Function MT_M_Set_PWM_F_Float Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Single) As Long

Declare Function MT_Get_PWM_F_Float Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Single) As Long

Declare Function MT_M_Get_PWM_F_Float Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Single) As Long

Declare Function MT_Set_PWM01 Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_PWM01 Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_Get_PWM01 Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_PWM01 Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_Set_PWM001 Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_PWM001 Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_Get_PWM001 Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_PWM001 Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_Set_PWM_Float Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Single) As Long

Declare Function MT_M_Set_PWM_Float Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Single) As Long

Declare Function MT_Get_PWM_Float Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Single) As Long

Declare Function MT_M_Get_PWM_Float Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Single) As Long

'//================================================================
'//圆弧插补
'//================================================================
'//设置圆弧插补主轴及速度
Declare Function MT_Set_Axis_Circle_Axis Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Axis_ID0 As Long,ByVal Axis_ID1 As Long) As Long

Declare Function MT_M_Set_Axis_Circle_Axis Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Axis_ID0 As Long,ByVal Axis_ID1 As Long) As Long

'//设置圆弧插补加速度
Declare Function MT_Set_Axis_Circle_Acc Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Axis_Circle_Acc Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

'//设置圆弧插补减速度
Declare Function MT_Set_Axis_Circle_Dec Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Axis_Circle_Dec Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

'//设置圆弧插补速度
Declare Function MT_Set_Axis_Circle_V Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Axis_Circle_V Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

'//设置圆弧插补启动 顺时钟  圆心坐标模式
Declare Function MT_Set_Axis_Circle_R_CW_Run_Rel Lib "MT_API.dll" (ByVal AObj As Integer,ByVal AR As Long,ByVal Axis_Target0 As Long,ByVal Axis_Target1 As Long) As Long

Declare Function MT_M_Set_Axis_Circle_R_CW_Run_Rel Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal AR As Long,ByVal Axis_Target0 As Long,ByVal Axis_Target1 As Long) As Long

Declare Function MT_Set_Axis_Circle_R_CW_Run_Abs Lib "MT_API.dll" (ByVal AObj As Integer,ByVal AR As Long,ByVal Axis_Target0 As Long,ByVal Axis_Target1 As Long) As Long

Declare Function MT_M_Set_Axis_Circle_R_CW_Run_Abs Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal AR As Long,ByVal Axis_Target0 As Long,ByVal Axis_Target1 As Long) As Long

'//设置圆弧插补启动 逆时钟   圆心坐标
Declare Function MT_Set_Axis_Circle_R_CCW_Run_Rel Lib "MT_API.dll" (ByVal AObj As Integer,ByVal AR As Long,ByVal Axis_Target0 As Long,ByVal Axis_Target1 As Long) As Long

Declare Function MT_M_Set_Axis_Circle_R_CCW_Run_Rel Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal AR As Long,ByVal Axis_Target0 As Long,ByVal Axis_Target1 As Long) As Long

Declare Function MT_Set_Axis_Circle_R_CCW_Run_Abs Lib "MT_API.dll" (ByVal AObj As Integer,ByVal AR As Long,ByVal Axis_Target0 As Long,ByVal Axis_Target1 As Long) As Long

Declare Function MT_M_Set_Axis_Circle_R_CCW_Run_Abs Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal AR As Long,ByVal Axis_Target0 As Long,ByVal Axis_Target1 As Long) As Long

'//设置圆弧插补停止
Declare Function MT_Set_Axis_Circle_Stop Lib "MT_API.dll" (ByVal AObj As Integer) As Long

Declare Function MT_M_Set_Axis_Circle_Stop Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer) As Long

'//设置圆弧插补急停
Declare Function MT_Set_Axis_Circle_Halt Lib "MT_API.dll" (ByVal AObj As Integer) As Long

Declare Function MT_M_Set_Axis_Circle_Halt Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer) As Long

'//读取圆弧插补模块
Declare Function MT_Get_Axis_Circle_Num Lib "MT_API.dll" (ByRef pValue As Long) As Long

Declare Function MT_M_Get_Axis_Circle_Num Lib "MT_API.dll" (ByVal ADev As Long,ByRef pValue As Long) As Long

'//插补运动状态
Declare Function MT_Get_Axis_Circle_Status Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_Axis_Circle_Status Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

'//插补轴
Declare Function MT_Get_Axis_Circle_Axis Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pID0 As Long,ByRef pID1 As Long) As Long

Declare Function MT_M_Get_Axis_Circle_Axis Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pID0 As Long,ByRef pID1 As Long) As Long

'//插补加速度
Declare Function MT_Get_Axis_Circle_Acc Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_Axis_Circle_Acc Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

'//插补减速度
Declare Function MT_Get_Axis_Circle_Dec Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_Axis_Circle_Dec Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

'//插补速度
Declare Function MT_Get_Axis_Circle_V Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_Axis_Circle_V Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

'//2014 04 09补充定义 增加起始速度修改 增加多轴联动直线插补
Declare Function MT_Set_Axis_Home_V_Start Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Axis_Home_V_Start Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_Set_Axis_Home_Acc Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Axis_Home_Acc Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_Set_Axis_Home_Dec Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Axis_Home_Dec Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_Get_Axis_Home_Acc Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_Axis_Home_Acc Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_Get_Axis_Home_Dec Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_Axis_Home_Dec Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_Set_Axis_Velocity_V_Start Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Axis_Velocity_V_Start Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_Set_Axis_Velocity_Acc Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Axis_Velocity_Acc Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_Set_Axis_Velocity_Dec Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Axis_Velocity_Dec Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_Get_Axis_Velocity_Acc Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_Axis_Velocity_Acc Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_Get_Axis_Velocity_Dec Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_Axis_Velocity_Dec Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_Set_Axis_Position_V_Start Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Axis_Position_V_Start Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_Set_Axis_Position_Acc Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Axis_Position_Acc Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_Set_Axis_Position_Dec Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Axis_Position_Dec Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_Get_Axis_Position_Acc Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_Axis_Position_Acc Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_Get_Axis_Position_Dec Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_Axis_Position_Dec Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_Set_Axis_Line_V_Start Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Axis_Line_V_Start Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_Set_Axis_Circle_V_Start Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Axis_Circle_V_Start Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_Set_Axis_Line_X_Run_Rel Lib "MT_API.dll" (ByVal AObj As Integer,ByVal AAxis_Num As Long,ByVal pAxis As Long,ByVal pTarget As Long) As Long

Declare Function MT_M_Set_Axis_Line_X_Run_Rel Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal AAxis_Num As Long,ByVal pAxis As Long,ByVal pTarget As Long) As Long

Declare Function MT_Set_Axis_Line_X_Run_Abs Lib "MT_API.dll" (ByVal AObj As Integer,ByVal AAxis_Num As Long,ByVal pAxis As Long,ByVal pTarget As Long) As Long

Declare Function MT_M_Set_Axis_Line_X_Run_Abs Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal AAxis_Num As Long,ByVal pAxis As Long,ByVal pTarget As Long) As Long

Declare Function MT_Set_Axis_Line_X_Target_Rel Lib "MT_API.dll" (ByVal AObj As Integer,ByVal AAxisID As Long,ByVal ATarget As Long) As Long

Declare Function MT_M_Set_Axis_Line_X_Target_Rel Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal AAxisID As Long,ByVal ATarget As Long) As Long

Declare Function MT_Set_Axis_Line_X_Target_Abs Lib "MT_API.dll" (ByVal AObj As Integer,ByVal AAxisID As Long,ByVal ATarget As Long) As Long

Declare Function MT_M_Set_Axis_Line_X_Target_Abs Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal AAxisID As Long,ByVal ATarget As Long) As Long

Declare Function MT_Set_Axis_Line_X_Axis Lib "MT_API.dll" (ByVal AObj As Integer,ByVal AAxisID As Long,ByVal AAxis As Long) As Long

Declare Function MT_M_Set_Axis_Line_X_Axis Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal AAxisID As Long,ByVal AAxis As Long) As Long

Declare Function MT_Set_Axis_Line_X_Count Lib "MT_API.dll" (ByVal AObj As Integer,ByVal ANum As Long) As Long

Declare Function MT_M_Set_Axis_Line_X_Count Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal ANum As Long) As Long

'//PLC相关的函数
'//PLC相关的指令码
'//读变量存储器大小
Declare Function MT_Get_PLC_Var_Num Lib "MT_API.dll" (ByRef pValue As Long) As Long

Declare Function MT_M_Get_PLC_Var_Num Lib "MT_API.dll" (ByVal ADev As Long,ByRef pValue As Long) As Long

'//读变量
Declare Function MT_Get_PLC_Var_Data Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_PLC_Var_Data Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

'//写变量
Declare Function MT_Set_PLC_Var_Data Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_PLC_Var_Data Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

'//暂停PLC
Declare Function MT_Set_PLC_Pause Lib "MT_API.dll" () As Long

Declare Function MT_M_Set_PLC_Pause Lib "MT_API.dll" (ByVal ADev As Long) As Long

'//停止PLC
Declare Function MT_Set_PLC_Stop Lib "MT_API.dll" () As Long

Declare Function MT_M_Set_PLC_Stop Lib "MT_API.dll" (ByVal ADev As Long) As Long

'//启动PLC程序
Declare Function MT_Set_PLC_Run Lib "MT_API.dll" () As Long

Declare Function MT_M_Set_PLC_Run Lib "MT_API.dll" (ByVal ADev As Long) As Long

'//设置PLC程序代码
Declare Function MT_Set_PLC_Data Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Byte) As Long

Declare Function MT_M_Set_PLC_Data Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Byte) As Long

'//读取PLC程序代码大小
Declare Function MT_Get_PLC_Code_Size Lib "MT_API.dll" (ByRef pValue As Long) As Long

Declare Function MT_M_Get_PLC_Code_Size Lib "MT_API.dll" (ByVal ADev As Long,ByRef pValue As Long) As Long

'//2017 01 30 PLC V6 Add
'//读取任务个数
'//PLC任务数
Declare Function MT_Get_PLC_Task_Count Lib "MT_API.dll" (ByRef pValue As Long) As Long

Declare Function MT_M_Get_PLC_Task_Count Lib "MT_API.dll" (ByVal ADev As Long,ByRef pValue As Long) As Long

'//PLC任务状态
Declare Function MT_Get_PLC_Task_Status Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_PLC_Task_Status Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

'//变量分割
Declare Function MT_Get_PLC_Var_Seg Lib "MT_API.dll" (ByRef pValue As Long) As Long

Declare Function MT_M_Get_PLC_Var_Seg Lib "MT_API.dll" (ByVal ADev As Long,ByRef pValue As Long) As Long

'//变量个数
Declare Function MT_Get_PLC_Var_Used Lib "MT_API.dll" (ByRef pValue As Long) As Long

Declare Function MT_M_Get_PLC_Var_Used Lib "MT_API.dll" (ByVal ADev As Long,ByRef pValue As Long) As Long

'//PLC状态
Declare Function MT_Get_PLC_Status Lib "MT_API.dll" (ByRef pValue As Long) As Long

Declare Function MT_M_Get_PLC_Status Lib "MT_API.dll" (ByVal ADev As Long,ByRef pValue As Long) As Long

'//全局状态
Declare Function MT_Get_PLC_Tasks_Status Lib "MT_API.dll" (ByRef pValue As Long) As Long

Declare Function MT_M_Get_PLC_Tasks_Status Lib "MT_API.dll" (ByVal ADev As Long,ByRef pValue As Long) As Long

'//Axis Ratio
Declare Function MT_Get_PLC_Axis_Ratio Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Single) As Long

Declare Function MT_M_Get_PLC_Axis_Ratio Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Single) As Long

Declare Function MT_Get_PLC_Encoder_Ratio Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Single) As Long

Declare Function MT_M_Get_PLC_Encoder_Ratio Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Single) As Long

'//流指令模式
'//启动Stream
Declare Function MT_Set_Stream_Run Lib "MT_API.dll" () As Long

Declare Function MT_M_Set_Stream_Run Lib "MT_API.dll" (ByVal ADev As Long) As Long

'//停止Stream
Declare Function MT_Set_Stream_Stop Lib "MT_API.dll" () As Long

Declare Function MT_M_Set_Stream_Stop Lib "MT_API.dll" (ByVal ADev As Long) As Long

'//暂停Stream
Declare Function MT_Set_Stream_Pause Lib "MT_API.dll" () As Long

Declare Function MT_M_Set_Stream_Pause Lib "MT_API.dll" (ByVal ADev As Long) As Long

'//清除Stream
Declare Function MT_Set_Stream_Clear Lib "MT_API.dll" () As Long

Declare Function MT_M_Set_Stream_Clear Lib "MT_API.dll" (ByVal ADev As Long) As Long

'//读取剩余空间
Declare Function MT_Get_Stream_Space Lib "MT_API.dll" (ByRef pValue As Long) As Long

Declare Function MT_M_Get_Stream_Space Lib "MT_API.dll" (ByVal ADev As Long,ByRef pValue As Long) As Long

'//读取总空间
Declare Function MT_Get_Stream_Total Lib "MT_API.dll" (ByRef pValue As Long) As Long

Declare Function MT_M_Get_Stream_Total Lib "MT_API.dll" (ByVal ADev As Long,ByRef pValue As Long) As Long

'//读取总空间
Declare Function MT_Get_Stream_Count Lib "MT_API.dll" (ByRef pValue As Long) As Long

Declare Function MT_M_Get_Stream_Count Lib "MT_API.dll" (ByVal ADev As Long,ByRef pValue As Long) As Long

'//以下指令在broadcast中存储并由Stream处理
Declare Function MT_Set_Stream_Delay Lib "MT_API.dll" (ByVal Value As Long) As Long

Declare Function MT_M_Set_Stream_Delay Lib "MT_API.dll" (ByVal ADev As Long,ByVal Value As Long) As Long

'//直线插补运动
'//设置直线插补加速度
Declare Function MT_Set_Stream_Line_Acc Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Stream_Line_Acc Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

'//设置直线插补减速度
Declare Function MT_Set_Stream_Line_Dec Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Stream_Line_Dec Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

'//设置直线插补速度
Declare Function MT_Set_Stream_Line_V_Max Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Stream_Line_V_Max Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

'//设置直线插补启动速度
Declare Function MT_Set_Stream_Line_V_Start Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Stream_Line_V_Start Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

'//设置直线插补停止
Declare Function MT_Set_Stream_Line_Stop Lib "MT_API.dll" (ByVal AObj As Integer) As Long

Declare Function MT_M_Set_Stream_Line_Stop Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer) As Long

'//设置直线插补急停
Declare Function MT_Set_Stream_Line_Halt Lib "MT_API.dll" (ByVal AObj As Integer) As Long

Declare Function MT_M_Set_Stream_Line_Halt Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer) As Long

'//启动直线插补
Declare Function MT_Set_Stream_Line_X_Run_Rel Lib "MT_API.dll" (ByVal AObj As Integer,ByVal AAxis_Num As Long,ByVal pAxis As Long,ByVal pTarget As Long) As Long

Declare Function MT_M_Set_Stream_Line_X_Run_Rel Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal AAxis_Num As Long,ByVal pAxis As Long,ByVal pTarget As Long) As Long

Declare Function MT_Set_Stream_Line_X_Run_Abs Lib "MT_API.dll" (ByVal AObj As Integer,ByVal AAxis_Num As Long,ByVal pAxis As Long,ByVal pTarget As Long) As Long

Declare Function MT_M_Set_Stream_Line_X_Run_Abs Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal AAxis_Num As Long,ByVal pAxis As Long,ByVal pTarget As Long) As Long

'//设置圆弧插补主轴及速度
Declare Function MT_Set_Stream_Circle_Axis Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Axis_ID0 As Long,ByVal Axis_ID1 As Long) As Long

Declare Function MT_M_Set_Stream_Circle_Axis Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Axis_ID0 As Long,ByVal Axis_ID1 As Long) As Long

'//设置圆弧插补加速度
Declare Function MT_Set_Stream_Circle_Acc Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Stream_Circle_Acc Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

'//设置圆弧插补减速度
Declare Function MT_Set_Stream_Circle_Dec Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Stream_Circle_Dec Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

'//设置圆弧插补速度
Declare Function MT_Set_Stream_Circle_V_Max Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Stream_Circle_V_Max Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

'//设置圆弧插补启动速度
Declare Function MT_Set_Stream_Circle_V_Start Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Stream_Circle_V_Start Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

'//设置圆弧插补启动 顺时钟  圆心坐标模式
Declare Function MT_Set_Stream_Circle_R_CW_Run_Rel Lib "MT_API.dll" (ByVal AObj As Integer,ByVal AR As Long,ByVal Axis_Target0 As Long,ByVal Axis_Target1 As Long) As Long

Declare Function MT_M_Set_Stream_Circle_R_CW_Run_Rel Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal AR As Long,ByVal Axis_Target0 As Long,ByVal Axis_Target1 As Long) As Long

Declare Function MT_Set_Stream_Circle_R_CW_Run_Abs Lib "MT_API.dll" (ByVal AObj As Integer,ByVal AR As Long,ByVal Axis_Target0 As Long,ByVal Axis_Target1 As Long) As Long

Declare Function MT_M_Set_Stream_Circle_R_CW_Run_Abs Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal AR As Long,ByVal Axis_Target0 As Long,ByVal Axis_Target1 As Long) As Long

'//设置圆弧插补启动 逆时钟   圆心坐标
Declare Function MT_Set_Stream_Circle_R_CCW_Run_Rel Lib "MT_API.dll" (ByVal AObj As Integer,ByVal AR As Long,ByVal Axis_Target0 As Long,ByVal Axis_Target1 As Long) As Long

Declare Function MT_M_Set_Stream_Circle_R_CCW_Run_Rel Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal AR As Long,ByVal Axis_Target0 As Long,ByVal Axis_Target1 As Long) As Long

Declare Function MT_Set_Stream_Circle_R_CCW_Run_Abs Lib "MT_API.dll" (ByVal AObj As Integer,ByVal AR As Long,ByVal Axis_Target0 As Long,ByVal Axis_Target1 As Long) As Long

Declare Function MT_M_Set_Stream_Circle_R_CCW_Run_Abs Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal AR As Long,ByVal Axis_Target0 As Long,ByVal Axis_Target1 As Long) As Long

'//设置圆弧插补停止
Declare Function MT_Set_Stream_Circle_Stop Lib "MT_API.dll" (ByVal AObj As Integer) As Long

Declare Function MT_M_Set_Stream_Circle_Stop Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer) As Long

'//设置圆弧插补急停
Declare Function MT_Set_Stream_Circle_Halt Lib "MT_API.dll" (ByVal AObj As Integer) As Long

Declare Function MT_M_Set_Stream_Circle_Halt Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer) As Long

Declare Function MT_Set_Stream_Wait_Line Lib "MT_API.dll" (ByVal AObj As Integer) As Long

Declare Function MT_M_Set_Stream_Wait_Line Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer) As Long

Declare Function MT_Set_Stream_Wait_Circle Lib "MT_API.dll" (ByVal AObj As Integer) As Long

Declare Function MT_M_Set_Stream_Wait_Circle Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer) As Long

'//设置单通道值
Declare Function MT_Set_Stream_OC_Out_Single Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Stream_OC_Out_Single Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

'//设置所有通道值
Declare Function MT_Set_Stream_OC_Out_All Lib "MT_API.dll" (ByVal Value As Long) As Long

Declare Function MT_M_Set_Stream_OC_Out_All Lib "MT_API.dll" (ByVal ADev As Long,ByVal Value As Long) As Long

'//设置单通道值
Declare Function MT_Set_Stream_Optic_Out_Single Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Stream_Optic_Out_Single Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

'//设置所有通道值
Declare Function MT_Set_Stream_Optic_Out_All Lib "MT_API.dll" (ByVal Value As Long) As Long

Declare Function MT_M_Set_Stream_Optic_Out_All Lib "MT_API.dll" (ByVal ADev As Long,ByVal Value As Long) As Long

'//减速功能
Declare Function MT_Set_Stream_Dec_Enable Lib "MT_API.dll" () As Long

Declare Function MT_M_Set_Stream_Dec_Enable Lib "MT_API.dll" (ByVal ADev As Long) As Long

Declare Function MT_Set_Stream_Dec_Disable Lib "MT_API.dll" () As Long

Declare Function MT_M_Set_Stream_Dec_Disable Lib "MT_API.dll" (ByVal ADev As Long) As Long

'//2016 08 20 增加等待输入功能
'//等待Optic_In状态
Declare Function MT_Set_Stream_Wait_Optic_In Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Stream_Wait_Optic_In Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

'//启动Stream,带密码校验功能
Declare Function MT_Set_Stream_Run_Check Lib "MT_API.dll" () As Long

Declare Function MT_M_Set_Stream_Run_Check Lib "MT_API.dll" (ByVal ADev As Long) As Long

'//2019 09 15 running id for UI
Declare Function MT_Set_Stream_Run_ID Lib "MT_API.dll" (ByVal Value As Long) As Long

Declare Function MT_M_Set_Stream_Run_ID Lib "MT_API.dll" (ByVal ADev As Long,ByVal Value As Long) As Long

Declare Function MT_Get_Stream_Run_ID Lib "MT_API.dll" (ByRef pValue As Long) As Long

Declare Function MT_M_Get_Stream_Run_ID Lib "MT_API.dll" (ByVal ADev As Long,ByRef pValue As Long) As Long

'//编码器功能
Declare Function MT_Get_Encoder_Num Lib "MT_API.dll" (ByRef pValue As Long) As Long

Declare Function MT_M_Get_Encoder_Num Lib "MT_API.dll" (ByVal ADev As Long,ByRef pValue As Long) As Long

Declare Function MT_Get_Encoder_Pos Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_Encoder_Pos Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_Set_Encoder_Pos Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Encoder_Pos Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_Set_Encoder_Z_Polarity Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Encoder_Z_Polarity Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_Set_Encoder_Dir_Polarity Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Encoder_Dir_Polarity Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_Get_Encoder_Index_Line_Count Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_Encoder_Index_Line_Count Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_Set_Encoder_Over_Enable Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Encoder_Over_Enable Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_Set_Encoder_Over_Max Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Encoder_Over_Max Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_Set_Encoder_Over_Stable Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Encoder_Over_Stable Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

'//高速主动数据上传
Declare Function MT_Get_Push_Data Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_Push_Data Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

'//2021 04 24  同步触发相关接口
Declare Function MT_Set_Trigger_Enable Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Trigger_Enable Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_Set_Trigger_Start Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Trigger_Start Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_Set_Trigger_End Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Trigger_End Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_Set_Trigger_Step Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Trigger_Step Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_Set_Trigger_Width Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Trigger_Width Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_Set_Trigger_Channel Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Trigger_Channel Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_Set_Trigger_Polarity Lib "MT_API.dll" (ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_M_Set_Trigger_Polarity Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByVal Value As Long) As Long

Declare Function MT_Get_Trigger_Enable Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_Trigger_Enable Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_Get_Trigger_Start Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_Trigger_Start Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_Get_Trigger_End Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_Trigger_End Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_Get_Trigger_Step Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_Trigger_Step Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_Get_Trigger_Width Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_Trigger_Width Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_Get_Trigger_Channel Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_Trigger_Channel Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_Get_Trigger_Polarity Lib "MT_API.dll" (ByVal AObj As Integer,ByRef pValue As Long) As Long

Declare Function MT_M_Get_Trigger_Polarity Lib "MT_API.dll" (ByVal ADev As Long,ByVal AObj As Integer,ByRef pValue As Long) As Long

'//辅助计算公式
'//mm to pluse
Declare Function MT_Help_Step_Line_Real_To_Steps Lib "MT_API.dll" (ByVal AStepAngle As Double,ByVal ADiv As Long,ByVal APitch As Double,ByVal ALineRatio As Double,ByVal AValue As Double) As Long

Declare Function MT_Help_Step_Circle_Real_To_Steps Lib "MT_API.dll" (ByVal AStepAngle As Double,ByVal ADiv As Long,ByVal ACircleRatio As Double,ByVal AValue As Double) As Long

'//pluse to mm
Declare Function MT_Help_Step_Line_Steps_To_Real Lib "MT_API.dll" (ByVal AStepAngle As Double,ByVal ADiv As Long,ByVal APitch As Double,ByVal ALineRatio As Double,ByVal AValue As Long) As Double

Declare Function MT_Help_Step_Circle_Steps_To_Real Lib "MT_API.dll" (ByVal AStepAngle As Double,ByVal ADiv As Long,ByVal ACircleRatio As Double,ByVal AValue As Long) As Double

'//Encoder
'//物理量到单位脉冲
Declare Function MT_Help_Encoder_Line_Real_To_Steps Lib "MT_API.dll" (ByVal APitch As Double,ByVal ALineRatio As Double,ByVal ALineCount As Long,ByVal AValue As Double) As Long

Declare Function MT_Help_Encoder_Circle_Real_To_Steps Lib "MT_API.dll" (ByVal ACircleRatio As Double,ByVal ALineCount As Long,ByVal AValue As Double) As Long

'//pluse to mm
Declare Function MT_Help_Encoder_Line_Steps_To_Real Lib "MT_API.dll" (ByVal APitch As Double,ByVal ALineRatio As Double,ByVal ALineCount As Long,ByVal AValue As Long) As Double

Declare Function MT_Help_Encoder_Circle_Steps_To_Real Lib "MT_API.dll" (ByVal ACircleRatio As Double,ByVal ALineCount As Long,ByVal AValue As Long) As Double

'//Grating
'//物理量到单位脉冲
Declare Function MT_Help_Grating_Line_Real_To_Steps Lib "MT_API.dll" (ByVal AUnit_um As Double,ByVal AValue As Double) As Long

Declare Function MT_Help_Grating_Circle_Real_To_Steps Lib "MT_API.dll" (ByVal ALineCount As Long,ByVal AValue As Double) As Long

'//pluse to mm
Declare Function MT_Help_Grating_Line_Steps_To_Real Lib "MT_API.dll" (ByVal AUnit_um As Double,ByVal AValue As Long) As Double

Declare Function MT_Help_Grating_Circle_Steps_To_Real Lib "MT_API.dll" (ByVal ALineCount As Long,ByVal AValue As Long) As Double

Declare Function MT_Help_Encoder_Factor Lib "MT_API.dll" (ByVal AStepAngle As Double,ByVal ADiv As Long,ByVal ALineCount As Long) As Single

'//光栅尺安装在机械上，电机旋转并不一致，需要考虑机械的影响
Declare Function MT_Help_Grating_Line_Factor Lib "MT_API.dll" (ByVal AStepAngle As Double,ByVal ADiv As Long,ByVal APitch As Double,ByVal ALineRatio As Double,ByVal AUnit_um As Double) As Single

Declare Function MT_Help_Grating_Circle_Factor Lib "MT_API.dll" (ByVal AStepAngle As Double,ByVal ADiv As Long,ByVal ACircleRatio As Double,ByVal ALineCount As Long) As Single

'//定义内部资源类型


