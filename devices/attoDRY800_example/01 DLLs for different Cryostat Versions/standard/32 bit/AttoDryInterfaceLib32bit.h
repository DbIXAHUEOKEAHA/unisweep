#include "extcode.h"
#pragma pack(push)
#pragma pack(1)

#ifdef __cplusplus
extern "C" {
#endif
typedef uint16_t  AttoDRY_Interface_Device;
#define AttoDRY_Interface_Device_attoDRY1100 0
#define AttoDRY_Interface_Device_attoDRY2100 1
#define AttoDRY_Interface_Device_attoDRY800 2
typedef uint16_t  Enum;
#define Enum__1Second 0
#define Enum__5Seconds 1
#define Enum__30Seconds 2
#define Enum__1Minute 3
#define Enum__5Minutes 4

/*!
 * Disconnects from the attoDRY, if already connected. This should be run 
 * before the <B>end.vi</B>
 */
int32_t __cdecl AttoDRY_Interface_Disconnect(void);
/*!
 * Starts the server that communicates with the attoDRY and loads the software 
 * for the device specified by <B> Device </B>. This VI needs to be run before 
 * commands can be sent or received. The <B>UI Queue</B> is an event queue for 
 * updating the GUI. It should not be used when calling the function from a 
 * DLL.
 */
int32_t __cdecl AttoDRY_Interface_begin(AttoDRY_Interface_Device Device);
/*!
 * Sends a 'Cancel' Command to the attoDRY. Use this when you want to cancel 
 * an action or respond negatively to a pop up.
 */
int32_t __cdecl AttoDRY_Interface_Cancel(void);
/*!
 * Sends a 'Confirm' command to the attoDRY. Use this when you want to respond 
 * positively to a pop up.
 */
int32_t __cdecl AttoDRY_Interface_Confirm(void);
/*!
 * Connects to the attoDRY using the specified COM Port
 */
int32_t __cdecl AttoDRY_Interface_Connect(char COMPort[]);
/*!
 * Starts the download of the <B>Sample Temperature Sensor Calibration 
 * Curve</B>. The curve will be saved to <B>Save Path</B>
 */
int32_t __cdecl AttoDRY_Interface_downloadSampleTemperatureSensorCalibrationCurve(
	char SavePath[]);
/*!
 * Starts the download of the Temperature Sensor Calibration Curve at <b>User 
 * Curve Number</B> on the temperature monitor. The curve will be saved to 
 * <B>Path</B>
 */
int32_t __cdecl AttoDRY_Interface_downloadTemperatureSensorCalibrationCurve(
	uint8_t UserCurveNumber, char Path[]);
/*!
 * Stops the server that is communicating with the attoDRY. The 
 * <B>Disconnect.vi</B> should be run before this. This VI should be run 
 * before closing your program.
 */
int32_t __cdecl AttoDRY_Interface_end(void);
/*!
 * Returns the temperature of the 4 Kelvin Stage
 */
int32_t __cdecl AttoDRY_Interface_get4KStageTemperature(
	float *_4KStageTemperatureK);
/*!
 * Gets the current action message. If an action is being performed, it will 
 * be shown here. It is similar to the pop ups on the display.
 */
int32_t __cdecl AttoDRY_Interface_getActionMessage(char ActionMessage[], 
	int32_t len);
/*!
 * Returns the current error message
 */
int32_t __cdecl AttoDRY_Interface_getAttodryErrorMessage(char ErrorMessage[], 
	int32_t len);
/*!
 * Returns the current error code
 */
int32_t __cdecl AttoDRY_Interface_getAttodryErrorStatus(uint8_t *ErrorCode);
/*!
 * Gets the Derivative gain. The gain retrieved depends on which heater is 
 * active:
 * - If no heaters are on or the sample heater is on, the <B>Sample Heater</B> 
 * gain is returned
 * - If the VTI heater is on and a sample temperature sensor is connected, the 
 * <B>VTI Heater</B> gain is returned
 * - If the VTI heater is on and no sample temperature sensor is connected, 
 * the <B>Exchange Heater</B> gain is returned
 */
int32_t __cdecl AttoDRY_Interface_getDerivativeGain(float *DerivativeGain);
/*!
 * Gets the Integral gain. The gain retrieved depends on which heater is 
 * active:
 * - If no heaters are on or the sample heater is on, the <B>Sample Heater</B> 
 * gain is returned
 * - If the VTI heater is on and a sample temperature sensor is connected, the 
 * <B>VTI Heater</B> gain is returned
 * - If the VTI heater is on and no sample temperature sensor is connected, 
 * the <B>Exchange Heater</B> gain is returned
 */
int32_t __cdecl AttoDRY_Interface_getIntegralGain(float *IntegralGain);
/*!
 * Gets the current magnetic field
 */
int32_t __cdecl AttoDRY_Interface_getMagneticField(float *MagneticFieldT);
/*!
 * Gets the current magnetic field set point
 */
int32_t __cdecl AttoDRY_Interface_getMagneticFieldSetPoint(
	float *MagneticFieldSetPointT);
/*!
 * Gets the Proportional gain. The gain retrieved depends on which heater is 
 * active:
 * - If no heaters are on or the sample heater is on, the <B>Sample Heater</B> 
 * gain is returned
 * - If the VTI heater is on and a sample temperature sensor is connected, the 
 * <B>VTI Heater</B> gain is returned
 * - If the VTI heater is on and no sample temperature sensor is connected, 
 * the <B>Exchange Heater</B> gain is returned
 */
int32_t __cdecl AttoDRY_Interface_getProportionalGain(
	float *ProportionalGain);
/*!
 * Gets the maximum power limit of the sample heater in Watts. This value, is 
 * the one stored in memory on the computer, not the one on the attoDRY. You 
 * should first use the appropriate <B>query VI</B> to request the value from 
 * the attoDRY.
 * 
 * The output power of the heater will not exceed this value. It is stored in 
 * non-volatile memory, this means that the value will not be lost, even if 
 * the attoDRY is turned off.
 */
int32_t __cdecl AttoDRY_Interface_getSampleHeaterMaximumPower(
	float *MaximumPower);
/*!
 * Gets the current Sample Heater power, in Watts
 */
int32_t __cdecl AttoDRY_Interface_getSampleHeaterPower(
	float *SampleHeaterPowerW);
/*!
 * Gets the resistance of the sample heater in Ohms. This value, is the one 
 * stored in memory on the computer, not the one on the attoDRY. You should 
 * first use the appropriate <B>query VI</B> to request the value from the 
 * attoDRY.
 * 
 * This value, along with the heater wire resistance, is used in calculating 
 * the output power of the heater. It is stored in non-volatile memory, this 
 * means that the value will not be lost, even if the attoDRY is turned off.
 * 
 * Power = Voltage^2/((HeaterResistance + WireResistance)^2) * 
 * HeaterResistance
 */
int32_t __cdecl AttoDRY_Interface_getSampleHeaterResistance(
	float *HeaterResistance);
/*!
 * Gets the resistance of the sample heater wires in Ohms. This value, is the 
 * one stored in memory on the computer, not the one on the attoDRY. You 
 * should first use the appropriate <B>query VI</B> to request the value from 
 * the attoDRY.
 * 
 * This value, along with the heater resistance, is used in calculating the 
 * output power of the heater. It is stored in non-volatile memory, this means 
 * that the value will not be lost, even if the attoDRY is turned off.
 * 
 * Power = Voltage^2/((HeaterResistance + WireResistance)^2) * 
 * HeaterResistance
 */
int32_t __cdecl AttoDRY_Interface_getSampleHeaterWireResistance(
	float *WireResistance);
/*!
 * Gets the sample temperature in Kelvin. This value is updated whenever a 
 * status message is received from the attoDRY.
 */
int32_t __cdecl AttoDRY_Interface_getSampleTemperature(float *Temperature);
/*!
 * Gets the user set point temperature, in Kelvin. This value is updated 
 * whenever a status message is received from the attoDRY.
 */
int32_t __cdecl AttoDRY_Interface_getUserTemperature(float *Temperature);
/*!
 * Returns the VTI Heater power, in Watts
 */
int32_t __cdecl AttoDRY_Interface_getVtiHeaterPower(float *VTIHeaterPowerW);
/*!
 * Returns the temperature of the VTI
 */
int32_t __cdecl AttoDRY_Interface_getVtiTemperature(float *VTITemperatureK);
/*!
 * Initiates the "Base Temperature" command, as on the touch screen
 */
int32_t __cdecl AttoDRY_Interface_goToBaseTemperature(void);
/*!
 * Returns 'True' if magnetic filed control is active. This is true when the 
 * magnetic field control icon on the touch screen is orange, and false when 
 * the icon is white.
 */
int32_t __cdecl AttoDRY_Interface_isControllingField(
	int *ControllingField);
/*!
 * Returns 'True' if temperature control is active. This is true when the 
 * temperature control icon on the touch screen is orange, and false when the 
 * icon is white.
 */
int32_t __cdecl AttoDRY_Interface_isControllingTemperature(
	int *ControllingTemperature);
/*!
 * Checks to see if the attoDRY has initialised. Use this VI after you have 
 * connected and before sending any commands or getting any data from the 
 * attoDRY
 */
int32_t __cdecl AttoDRY_Interface_isDeviceInitialised(int *Initialised);
/*!
 * Checks to see if the attoDRY is connected. Returns True if connected.
 */
int32_t __cdecl AttoDRY_Interface_isDeviceConnected(int *isConnected);
/*!
 * Returns 'True' if the base temperature process is active. This is true when 
 * the base temperature button on the touch screen is orange, and false when 
 * the button is white.
 */
int32_t __cdecl AttoDRY_Interface_isGoingToBaseTemperature(
	int *GoingToBaseTemperature);
/*!
 * Checks to see if persistant mode is set for the magnet. Note: this shows if 
 * persistant mode is set, it does not show if the persistant switch heater is 
 * on. The heater may be on during persistant mode when, for example, changing 
 * the field.
 */
int32_t __cdecl AttoDRY_Interface_isPersistentModeSet(
	int *PersistentMode);
/*!
 * Returns true if the pump is running
 */
int32_t __cdecl AttoDRY_Interface_isPumping(int *Pumping);
/*!
 * Returns 'True' if the sample exchange process is active. This is true when 
 * the sample exchange button on the touch screen is orange, and false when 
 * the button is white.
 */
int32_t __cdecl AttoDRY_Interface_isSampleExchangeInProgress(
	int *ExchangingSample);
/*!
 * Checks to see if the sample heater is on. 'On' is defined as PID control is 
 * active or a contant heater power is set. 
 */
int32_t __cdecl AttoDRY_Interface_isSampleHeaterOn(
	int *SampleHeaterStatus);
/*!
 * This will return true when the sample stick is ready to be removed or 
 * inserted.
 */
int32_t __cdecl AttoDRY_Interface_isSampleReadyToExchange(
	int *ReadyToExchange);
/*!
 * Checks to see if the system is running, that is, if the compressor is 
 * running etc
 */
int32_t __cdecl AttoDRY_Interface_isSystemRunning(int *SystemRunning);
/*!
 * Returns 'True' if the "Zero Field" process is active. This is true when the 
 * "Zero Field" button on the touch screen is orange, and false when the 
 * button is white.
 */
int32_t __cdecl AttoDRY_Interface_isZeroingField(int *ZeroingField);
/*!
 * Lowers any raised errors
 */
int32_t __cdecl AttoDRY_Interface_lowerError(void);
/*!
 * Requests the maximum power limit of the sample heater in Watts from the 
 * attoDRY. After running this command, use the appropriate <B>get VI</B> to 
 * get the value stored on the computer.
 * 
 * The output power of the heater will not exceed this value. It is stored in 
 * non-volatile memory, this means that the value will not be lost, even if 
 * the attoDRY is turned off.
 */
int32_t __cdecl AttoDRY_Interface_querySampleHeaterMaximumPower(void);
/*!
 * Requests the  resistance of the sample heater in Ohms from the attoDRY. 
 * After running this command, use the appropriate <B>get VI</B> to get the 
 * value stored on the computer.
 * 
 * This value, along with the heater wire resistance, is used in calculating 
 * the output power of the heater. It is stored in non-volatile memory, this 
 * means that the value will not be lost, even if the attoDRY is turned off.
 * 
 * Power = Voltage^2/((HeaterResistance + WireResistance)^2) * 
 * HeaterResistance
 */
int32_t __cdecl AttoDRY_Interface_querySampleHeaterResistance(void);
/*!
 * Requests the  resistance of the sample wires heater in Ohms from the 
 * attoDRY. After running this command, use the appropriate <B>get VI</B> to 
 * get the value stored on the computer.
 * 
 * This value, along with the heater resistance, is used in calculating the 
 * output power of the heater. It is stored in non-volatile memory, this means 
 * that the value will not be lost, even if the attoDRY is turned off.
 * 
 * Power = Voltage^2/((HeaterResistance + WireResistance)^2) * 
 * HeaterResistance
 */
int32_t __cdecl AttoDRY_Interface_querySampleHeaterWireResistance(void);
/*!
 * Sets the Derivative gain. The controller that is updated depends on which 
 * heater is active:
 * - If no heaters are on or the sample heater is on, the <B>Sample Heater</B> 
 * gain is set
 * - If the VTI heater is on and a sample temperature sensor is connected, the 
 * <B>VTI Heater</B> gain is set
 * - If the VTI heater is on and no sample temperature sensor is connected, 
 * the <B>Exchange Heater</B> gain is set
 */
int32_t __cdecl AttoDRY_Interface_setDerivativeGain(float DerivativeGain);
/*!
 * Sets the Integral gain. The controller that is updated depends on which 
 * heater is active:
 * - If no heaters are on or the sample heater is on, the <B>Sample Heater</B> 
 * gain is set
 * - If the VTI heater is on and a sample temperature sensor is connected, the 
 * <B>VTI Heater</B> gain is set
 * - If the VTI heater is on and no sample temperature sensor is connected, 
 * the <B>Exchange Heater</B> gain is set
 */
int32_t __cdecl AttoDRY_Interface_setIntegralGain(float IntegralGain);
/*!
 * Sets the Proportional gain. The controller that is updated depends on which 
 * heater is active:
 * - If no heaters are on or the sample heater is on, the <B>Sample Heater</B> 
 * gain is set
 * - If the VTI heater is on and a sample temperature sensor is connected, the 
 * <B>VTI Heater</B> gain is set
 * - If the VTI heater is on and no sample temperature sensor is connected, 
 * the <B>Exchange Heater</B> gain is set
 */
int32_t __cdecl AttoDRY_Interface_setProportionalGain(float ProportionalGain);
/*!
 * Sets the maximum power limit of the sample heater in Watts. After running 
 * this command, use the appropriate <B>request</B> and <B>get</B> VIs to 
 * check the value was stored on the attoDRY.
 * 
 * The output power of the heater will not exceed this value. 
 * 
 * It is stored in non-volatile memory, this means that the value will not be 
 * lost, even if the attoDRY is turned off. Note: the non-volatile memory has 
 * a specified life of 100,000 write/erase cycles, so you may need to be 
 * careful about how often you set this value.
 */
int32_t __cdecl AttoDRY_Interface_setSampleHeaterMaximumPower(
	float MaximumPower);
/*!
 * Sets the resistance of the sample heater wires in Ohms. After running this 
 * command, use the appropriate <B>request</B> and <B>get</B> VIs to check the 
 * value was stored on the attoDRY.
 * 
 * This value, along with the heater resistance, is used in calculating the 
 * output power of the heater. It is stored in non-volatile memory, this means 
 * that the value will not be lost, even if the attoDRY is turned off.
 * 
 * Power = Voltage^2/((HeaterResistance + WireResistance)^2) * 
 * HeaterResistance
 * 
 * It is stored in non-volatile memory, this means that the value will not be 
 * lost, even if the attoDRY is turned off. Note: the non-volatile memory has 
 * a specified life of 100,000 write/erase cycles, so you may need to be 
 * careful about how often you set this value.
 */
int32_t __cdecl AttoDRY_Interface_setSampleHeaterWireResistance(
	float WireResistance);
/*!
 * Sets the sample heater value to the specified value
 */
int32_t __cdecl AttoDRY_Interface_setSampleHeaterPower(float HeaterPowerW);
/*!
 * Sets the resistance of the sample heater in Ohms. After running this 
 * command, use the appropriate <B>request</B> and <B>get</B> VIs to check the 
 * value was stored on the attoDRY.
 * 
 * This value, along with the heater wire resistance, is used in calculating 
 * the output power of the heater. It is stored in non-volatile memory, this 
 * means that the value will not be lost, even if the attoDRY is turned off.
 * 
 * Power = Voltage^2/((HeaterResistance + WireResistance)^2) * 
 * HeaterResistance
 * 
 * It is stored in non-volatile memory, this means that the value will not be 
 * lost, even if the attoDRY is turned off. Note: the non-volatile memory has 
 * a specified life of 100,000 write/erase cycles, so you may need to be 
 * careful about how often you set this value.
 */
int32_t __cdecl AttoDRY_Interface_setSampleHeaterResistance(
	float HeaterResistance);
/*!
 * Sets the user magntic field. This is used as the set point when field 
 * control is active
 */
int32_t __cdecl AttoDRY_Interface_setUserMagneticField(
	float MagneticFieldSetPointT);
/*!
 * Sets the user temperature. This is the temperature used when temperature 
 * control is enabled.
 */
int32_t __cdecl AttoDRY_Interface_setUserTemperature(float Temperature);
/*!
 * Starts logging data to the file specifed by <B>Path</B>. 
 * 
 * If the file does not exist, it will be created.
 */
int32_t __cdecl AttoDRY_Interface_startLogging(char Path[], 
	Enum TimeSelection, int Append);
/*!
 * Starts the sample exchange procedure
 */
int32_t __cdecl AttoDRY_Interface_startSampleExchange(void);
/*!
 * Stops logging data
 */
int32_t __cdecl AttoDRY_Interface_stopLogging(void);
/*!
 * Initiates the "Zero Field" command, as on the touch screen
 */
int32_t __cdecl AttoDRY_Interface_sweepFieldToZero(void);
/*!
 * Toggles temperature control, just as the thermometer icon on the touch 
 * screen.
 */
int32_t __cdecl AttoDRY_Interface_toggleFullTemperatureControl(void);
/*!
 * Toggle magnetic field control, just as the magnet icon on the touch screen
 */
int32_t __cdecl AttoDRY_Interface_toggleMagneticFieldControl(void);
/*!
 * Toggles persistant mode for magnet control. If it is enabled, the switch 
 * heater will be turned off once the desired field is reached. If it is not, 
 * the switch heater will be left on.
 */
int32_t __cdecl AttoDRY_Interface_togglePersistentMode(void);
/*!
 * Starts and stops the pump. If the pump is running, it will stop it. If the 
 * pump is not running, it will be started.
 */
int32_t __cdecl AttoDRY_Interface_togglePump(void);
/*!
 * This command only toggles the sample temperature controller. It does not 
 * pump the volumes etc. Use  <B>toggleFullTemperatureControl.vi</B> for 
 * behaviour like the temperature control icon on the touch screen.
 */
int32_t __cdecl AttoDRY_Interface_toggleSampleTemperatureControl(void);
/*!
 * Toggles the start up/shutdown procedure. If the attoDRY is started up, the 
 * shut down procedure will be run and vice versa
 */
int32_t __cdecl AttoDRY_Interface_toggleStartUpShutdown(void);
/*!
 * Starts the upload of a <B>.crv calibration curve file</B> to the <B>sample 
 * temperature sensor</B>
 */
int32_t __cdecl AttoDRY_Interface_uploadSampleTemperatureCalibrationCurve(
	char Path[]);
/*!
 * Starts the upload of a <B>.crv calibration curve file</B> to the specified 
 * <B>User Curve Number</B> on the temperature monitor. Use a curve number of 
 * 1 to 8, inclusive
 */
int32_t __cdecl AttoDRY_Interface_uploadTemperatureCalibrationCurve(
	uint8_t UserCurveNumber, char Path[]);
/*!
 * AttoDRY_Interface_setVTIHeaterPower
 */
int32_t __cdecl AttoDRY_Interface_setVTIHeaterPower(float VTIHeaterPowerW);
/*!
 * AttoDRY_Interface_queryReservoirTsetColdSample
 */
int32_t __cdecl AttoDRY_Interface_queryReservoirTsetColdSample(void);
/*!
 * AttoDRY_Interface_getReservoirTsetColdSample
 */
int32_t __cdecl AttoDRY_Interface_getReservoirTsetColdSample(
	float *ReservoirTsetColdSampleK);
/*!
 * AttoDRY_Interface_setReservoirTsetWarmMagnet
 */
int32_t __cdecl AttoDRY_Interface_setReservoirTsetWarmMagnet(
	float ReservoirTsetWarmMagnetW);
/*!
 * AttoDRY_Interface_setReservoirTsetColdSample
 */
int32_t __cdecl AttoDRY_Interface_setReservoirTsetColdSample(
	float SetReservoirTsetColdSampleK);
/*!
 * AttoDRY_Interface_setReservoirTsetWarmSample
 */
int32_t __cdecl AttoDRY_Interface_setReservoirTsetWarmSample(
	float ReservoirTsetWarmSampleW);
/*!
 * AttoDRY_Interface_queryReservoirTsetWarmSample
 */
int32_t __cdecl AttoDRY_Interface_queryReservoirTsetWarmSample(void);
/*!
 * AttoDRY_Interface_queryReservoirTsetWarmMagnet
 */
int32_t __cdecl AttoDRY_Interface_queryReservoirTsetWarmMagnet(void);
/*!
 * AttoDRY_Interface_getReservoirTsetWarmSample
 */
int32_t __cdecl AttoDRY_Interface_getReservoirTsetWarmSample(
	float *ReservoirTsetWarmSampleK);
/*!
 * AttoDRY_Interface_getReservoirTsetWarmMagnet
 */
int32_t __cdecl AttoDRY_Interface_getReservoirTsetWarmMagnet(
	float *ReservoirTsetWarmMagnetK);
/*!
 * ATTODRY800 ONLY. Gets the current status of the BreakVacuum valve. 
 */
int32_t __cdecl AttoDRY_Interface_getBreakVac800Valve(int *valveStatus);
/*!
 * ATTODRY800 ONLY. Toggles the SampleSpace valve. If it is closed, it will 
 * open and if it is open, it will close. 
 */
int32_t __cdecl AttoDRY_Interface_toggleSampleSpace800Valve(void);
/*!
 * ATTODRY800 ONLY. Gets the current status of the Pump valve. 
 */
int32_t __cdecl AttoDRY_Interface_getPump800Valve(int *valveStatus);
/*!
 * ATTODRY800 ONLY. Gets the current status of the SampleSpace valve.
 */
int32_t __cdecl AttoDRY_Interface_getSampleSpace800Valve(
	int *valveStatus);
/*!
 * ATTODRY800 ONLY. Toggles the Pump valve. If it is closed, it will open and 
 * if it is open, it will close. 
 */
int32_t __cdecl AttoDRY_Interface_togglePump800Valve(void);
/*!
 * ATTODRY800 ONLY. Toggles the BreakVacuum valve. If it is closed, it will 
 * open and if it is open, it will close. 
 */
int32_t __cdecl AttoDRY_Interface_toggleBreakVac800Valve(void);
/*!
 * ATTODRY800 ONLY. Gets the pressure at the Cryostat Inlet.
 */
int32_t __cdecl AttoDRY_Interface_getPressure800(
	float *CryostatInPressureMbar);
/*!
 * ATTODRY800 ONLY. Gets the current frequency of the turbopump.
 */
int32_t __cdecl AttoDRY_Interface_GetTurbopumpFrequ800(
	uint16_t *TurbopumpFrequencyHz);
/*!
 * ATTODRY1100 ONLY. Gets the current temperature of the 40K Stage, in Kelvin
 */
int32_t __cdecl AttoDRY_Interface_get40KStageTemperature(
	float *_40KStageTemperatureK);
/*!
 * ATTODRY1100 ONLY. Gets the current status of the helium valve. True is 
 * opened, false is closed.
 */
int32_t __cdecl AttoDRY_Interface_getHeliumValve(int *valveStatus);
/*!
 * ATTODRY1100 ONLY. Gets the current status of the inner volume valve. True 
 * is opened, false is closed.
 */
int32_t __cdecl AttoDRY_Interface_getInnerVolumeValve(int *valveStatus);
/*!
 * ATTODRY1100 ONLY. Gets the current status of the outer volume valve. True 
 * is opened, false is closed.
 */
int32_t __cdecl AttoDRY_Interface_getOuterVolumeValve(int *valveStatus);
/*!
 * ATTODRY1100 ONLY. Gets the current presure in the valve junction block, in 
 * mbar. 
 */
int32_t __cdecl AttoDRY_Interface_getPressure(float *PressureMbar);
/*!
 * ATTODRY1100 ONLY. Gets the current status of the pump valve. True is 
 * opened, false is closed.
 */
int32_t __cdecl AttoDRY_Interface_getPumpValve(int *valveStatus);
/*!
 * ATTODRY1100 ONLY. Gets the current frequency of the turbopump.
 */
int32_t __cdecl AttoDRY_Interface_getTurbopumpFrequency(
	uint16_t *TurbopumpFrequencyHz);
/*!
 * Checks to see if the exchange/vti heater is on. 'On' is defined as PID 
 * control is active or a constant heater power is set. 
 */
int32_t __cdecl AttoDRY_Interface_isExchangeHeaterOn(
	int *ExchangeHeaterStatus);
/*!
 * This command only toggles the exchange/vti temperature controller. If a 
 * sample temperature sensor is connected, this will be controlled, otherwise 
 * the temperature of the exchange tube will be used
 */
int32_t __cdecl AttoDRY_Interface_toggleExchangeHeaterControl(void);
/*!
 * ATTODRY1100 ONLY. Toggles the helium valve. If it is closed, it will open 
 * and if it is open, it will close.
 */
int32_t __cdecl AttoDRY_Interface_toggleHeliumValve(void);
/*!
 * ATTODRY1100 ONLY. 
 * Toggles the inner volume valve. If it is closed, it will open and if it is 
 * open, it will close. 
 */
int32_t __cdecl AttoDRY_Interface_toggleInnerVolumeValve(void);
/*!
 * ATTODRY1100 ONLY. Toggles the outer volume valve. If it is closed, it will 
 * open and if it is open, it will close. 
 */
int32_t __cdecl AttoDRY_Interface_toggleOuterVolumeValve(void);
/*!
 * ATTODRY1100 ONLY. Toggles the pump valve. If it is closed, it will open and 
 * if it is open, it will close. 
 */
int32_t __cdecl AttoDRY_Interface_togglePumpValve(void);
/*!
 * ATTODRY2100 ONLY. Gets the pressure at the Cryostat Inlet
 */
int32_t __cdecl AttoDRY_Interface_getCryostatInPressure(
	float *CryostatInPressureMbar);
/*!
 * ATTODRY2100 ONLY. Gets the current status of the Cryostat In valve.
 */
int32_t __cdecl AttoDRY_Interface_getCryostatInValve(int *valveStatus);
/*!
 * Gets the Cryostat Outlet pressure
 */
int32_t __cdecl AttoDRY_Interface_getCryostatOutPressure(
	float *CryostatOutPressureMbar);
/*!
 * ATTODRY2100 ONLY. Gets the current status of the Cryostat Out valve.
 */
int32_t __cdecl AttoDRY_Interface_getCryostatOutValve(int *valveStatus);
/*!
 * ATTODRY2100 ONLY. Gets the current status of the Dump In volume valve. 
 */
int32_t __cdecl AttoDRY_Interface_getDumpInValve(int *valveStatus);
/*!
 * ATTODRY2100 ONLY. Gets the current status of the outer volume valve. 
 */
int32_t __cdecl AttoDRY_Interface_getDumpOutValve(int *valveStatus);
/*!
 * ATTODRY2100 ONLY. Gets the pressure at the Dump
 */
int32_t __cdecl AttoDRY_Interface_getDumpPressure(float *DumpPressureMbar);
/*!
 * Gets the current power, in Watts, being produced by the Reservoir Heater
 */
int32_t __cdecl AttoDRY_Interface_getReservoirHeaterPower(
	float *ReservoirHeaterPowerW);
/*!
 * Gets the current temperature of the Helium Reservoir, in Kelvin
 */
int32_t __cdecl AttoDRY_Interface_getReservoirTemperature(
	float *ReservoirTemperatureK);
/*!
 * ATTODRY2100 ONLY. Toggles the Cryostat In valve. If it is closed, it will 
 * open and if it is open, it will close. 
 */
int32_t __cdecl AttoDRY_Interface_toggleCryostatInValve(void);
/*!
 * ATTODRY2100 ONLY. Toggles the Cryostat Out valve. If it is closed, it will 
 * open and if it is open, it will close. 
 */
int32_t __cdecl AttoDRY_Interface_toggleCryostatOutValve(void);
/*!
 * ATTODRY2100 ONLY. Toggles the inner volume valve. If it is closed, it will 
 * open and if it is open, it will close. 
 */
int32_t __cdecl AttoDRY_Interface_toggleDumpInValve(void);
/*!
 * ATTODRY2100 ONLY. Toggles the outer volume valve. If it is closed, it will 
 * open and if it is open, it will close. 
 */
int32_t __cdecl AttoDRY_Interface_toggleDumpOutValve(void);

MgErr __cdecl LVDLLStatus(char *errStr, int errStrLen, void *module);

#ifdef __cplusplus
} // extern "C"
#endif

#pragma pack(pop)

