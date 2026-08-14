#Thanks to https://github.com/chmurer/AttoDRY
# This is a Python script for direct control of the AttoDRY2100 cryostat.
# It depends on the .dll files provided by Attocube (AttoDRYLib.dll) which
# has to be referred to in the dll_directory variable. Not all functions
# are implemented in the given code, since control is still maintained with
# the attoDRY labview interface. All additional function names are found in the dll_list.txt
# file. 
# You need to install the 2016 labview runtime engine. Additinally, the 
# script will only work with a 32 bit python version. 
#
# AttoDRY2100lib.py and PyAttoDRY2100.py are written by 
# Christoph Murer
# Magnetism and interface Physics, ETH Zurich
# christoph.murer@mat.ethz.ch or chmurer@gmail.com
# script started on 04-Sep-2020
# inspired by the ANC350 scrips written by Rob Heath and Brian Schaefer (https://github.com/Laukei/pyanc350)

# define the path to the AttoDRY DLL:


import ctypes
import os

dll_directory = 'C:\\NUS\\Transport_lab\\App\\devices\\attoDRYLib\\'

print(dll_directory)

os.add_dll_directory(dll_directory)

# error code (EC) as described by 
EC_Ok = 0                      # No error
EC_Error = -1                  # Unknown / other error
# all other error codes are implemented in checkError directly...

#checks the errors returned from the dll
def checkError(code,func,args):
    if code == EC_Ok:
        return
    elif code == 1:
    	raise Exception('Error 1: High liquid helium reservoir temperature. Action: Wait for it to cool.')
    elif code == 2:
    	raise Exception('Error 2: High pressure. Action: Wait for it to drop.')
    elif code == 3:
    	raise Exception('Error 3: The temperature monitor has not initialised properly. Action: Turn the AttoDRY off and on.')
    elif code == 4:
    	raise Exception('Error 4: There is a fault with channel A on the temperature Monitor. Action: Turn the attoDRY off and on. If this error occurs repeatedly, contact attocube.')
    elif code == 5:
    	raise Exception('Error 5: There is a fault with channel B on the temperature Monitor. Action: Turn the attoDRY off and on. If this error occurs repeatedly, contact attocube.')
    elif code == 6:
    	raise Exception('Error 6: There is a fault with channel C on the temperature Monitor. Action: Turn the attoDRY off and on. If this error occurs repeatedly, contact attocube.')
    elif code == 7:
    	raise Exception('Error 7: There is a fault with channel D on the temperature Monitor. Action: Turn the attoDRY off and on. If this error occurs repeatedly, contact attocube.')
    elif code == 8:
    	raise Exception('Error 8: The temperature monitor has not responded within a ceratin amount of time. Action: Lower the error. If the error occurs again, try restarting the attoDRY. If this occurs again, contact attocube.')
    elif code == 9:
    	raise Exception('Error 9: Excessive pump link voltage. Action: Turn off the attoDRY, switch the pump on and off again. Turn the attoDRY on. If this occurs again, contact attocube.')
    elif code == 10:
    	raise Exception('Error 10: Excessive pump motor current. Action: Turn off the attoDRY, switch the pump on and off again. Turn the attoDRY on. If this occurs again, contact attocube.')
    elif code == 11:
    	raise Exception('Error 11: Excessive pump controller temperature. Action: Turn off the attoDRY, switch the pump on and off again. Turn the attoDRY on. If this occurs again, contact attocube. Make sure the pump is in a well-ventilated area.')
    elif code == 12:
    	raise Exception('Error 12: Pump controller temp sensor failure. Action: Turn off the attoDRY, switch the pump on and off again. Turn the attoDRY on. If this occurs again, contact attocube.')
    elif code == 13:
    	raise Exception('Error 13: Pump power stage failure. Action: Turn off the attoDRY, switch the pump on and off again. Turn the attoDRY on. If this occurs again, contact attocube.')
    elif code == 17:
    	raise Exception('Error 17: Critical pump EEPROM problem. Action: Turn off the attoDRY, switch the pump on and off again. Turn the attoDRY on. If this occurs again, contact attocube.')
    elif code == 19:
    	raise Exception('Error 19: Pump parameter set upload required. Action: Turn off the attoDRY, switch the pump on and off again. Turn the attoDRY on. If this occurs again, contact attocube.')
    elif code == 20:
    	raise Exception('Error 20: Pump self-test fault (invalid pump software code). Action: Turn off the attoDRY, switch the pump on and off again. Turn the attoDRY on. If this occurs again, contact attocube.')
    elif code == 21:
    	raise Exception('Error 21: Pump serial enable input went inactive whilst operating with a serial start command. Action: Turn off the attoDRY, switch the pump on and off again. Turn the attoDRY on. If this occurs again, contact attocube. Ensure the cable between the pump and the attoDRY is plugged in properly.')
    elif code == 22:
    	raise Exception('Error 22: Pump output frequency dropped below threshold for too long. Action: Turn off the attoDRY, switch the pump on and off again. Turn the attoDRY on. If this occurs again, contact attocube. This error may occur if the pressure suddenly increases in the pumping line.')
    elif code == 23:
    	raise Exception('Error 23: Pump output frequency did not reach threshold in allowable time. Action: Turn off the attoDRY, switch the pump on and off again. Turn the attoDRY on. If this occurs again, contact attocube.')
    elif code == 24:
    	raise Exception('Error 24: Error processing pump response. Action: Try to send the command again.')
    elif code == 29:
    	raise Exception('Error 29: Error with pump inlet pressure gauge. Action: Check the light on top of the pressure gauge. If it is off, ensure everything is plugged correctly. If it is red or green, try switching the power on and off. Contact attocube if the light stays off or red.')
    elif code == 30:
    	raise Exception('Error 30: Error with the pump outlet pressure gauge. Action: Check the light on top of the pressure gauge. If it is off, ensure everything is plugged in correctly. If it is red or green, try switching the power on and off. Contact attocube if the light stays off or red.')
    elif code == 31:
    	raise Exception('Error 31: Error with the helium dump pressure gauge. Action: Check the light on top of the pressure gauge. If it is off, ensure everything is plugged in correctly. If it is red or green, try switching the power on and off. Contact attocube if the light stays off or red.')
    elif code == 32:
    	raise Exception('Error 32: Error with compressor. Action: Check the compressor display for more information.')
    elif code == 33:
    	raise Exception('Error 33: VTI temperature is too high; everything is stopped to prefent damage. Action: Wait for the temperature to drop. If this occurs repeatedly, contact attocube.')
    elif code == 34:
    	raise Exception('Error 34: The temperature monitor has given invalid temperatures for too long. Unable to control the temperature. This can occur when changing temperature monitor settings e.g. sensor exictation ranges. Action: Check all temperature sensor cables are connected and try again. If the error occurs again, restart the attoDRY. If you changed a setting on the temperature monitor, wait a few seconds and start controlling again.')
    elif code == 35:
    	raise Exception('Error 35: An operation has been requested that requires the magnet controller and there is not one connected. Action: Ensure magnet controller is connected, switched on, and communication is configured. Restart attoDRY.')
    elif code == 36:
    	raise Exception('Error 36: An operation with the magnet controller requires it to be in remote mode when it is not. Action: The magnet controller must be in remote mode. Ensure the magnet controller is not in local mode.')
    elif code == 37:
    	raise Exception('Error 37: Magnet quenched. Action: Let magnet cool. Try again.')
    elif code == 38:
    	raise Exception('Error 38: Magnet controller power module failure. Action: Contact attocube.')
    elif code == 39:
    	raise Exception('Error 39: Error with chip 1 on motor driver 1. Action: Restart attoDRY. Contact attocube if problem persists.')
    elif code == 40:
    	raise Exception('Error 40: Error with chip 1 on motor driver 2. Action: Restart attoDRY. Contact attocube if problem persists.')
    elif code == 41:
    	raise Exception('Error 41: Error with chip 1 on motor driver 3. Action: Restart attoDRY. Contact attocube if problem persists.')
    elif code == 42:
    	raise Exception('Error 42: Error with chip 1 on motor driver 4. Action: Restart attoDRY. Contact attocube if problem persists.')
    elif code <= EC_Error:             
        raise Exception('Error: unspecific in'+str(func.__name__)+'with parameters:'+str(args))
    else:                    
        raise Exception('Error: unknown Error code: '+str(code))
    return code


class ADRY:
    # load attoDRYLib...
    attoDRYLib = ctypes.windll.attoDRYLib
    #############################################################################################################
    ##### aliases for the DLL functions (only selected ones; we want to change field and temperature only):
    #############################################################################################################
    
    ##### communication
    getActionMessage = getattr(attoDRYLib,'AttoDRY_Interface_getActionMessage')
    begin = getattr(attoDRYLib,'AttoDRY_Interface_begin')
    Cancel = getattr(attoDRYLib,'AttoDRY_Interface_Cancel')
    Confirm = getattr(attoDRYLib,'AttoDRY_Interface_Confirm')
    Connect = getattr(attoDRYLib,'AttoDRY_Interface_Connect')
    Main = getattr(attoDRYLib,'AttoDRY_Interface_Main')
    Disconnect = getattr(attoDRYLib,'AttoDRY_Interface_Disconnect')
    end = getattr(attoDRYLib,'AttoDRY_Interface_end')
    getAttodryErrorMessage = getattr(attoDRYLib,'AttoDRY_Interface_getAttodryErrorMessage')
    getAttodryErrorStatus = getattr(attoDRYLib,'AttoDRY_Interface_getAttodryErrorStatus')
    goToBaseTemperature = getattr(attoDRYLib,'AttoDRY_Interface_goToBaseTemperature')
    lowerError = getattr(attoDRYLib,'AttoDRY_Interface_lowerError')
    LVDLLStatus = getattr(attoDRYLib,'LVDLLStatus')
    startLogging = getattr(attoDRYLib,'AttoDRY_Interface_startLogging')
    startSampleExchange = getattr(attoDRYLib,'AttoDRY_Interface_startSampleExchange')
    stopLogging = getattr(attoDRYLib,'AttoDRY_Interface_stopLogging')
    sweepFieldToZero = getattr(attoDRYLib,'AttoDRY_Interface_sweepFieldToZero')
    downloadSampleTemperatureSensorCalibrationCurve = getattr(attoDRYLib,'AttoDRY_Interface_downloadSampleTemperatureSensorCalibrationCurve')
    downloadTemperatureSensorCalibrationCurve = getattr(attoDRYLib,'AttoDRY_Interface_downloadTemperatureSensorCalibrationCurve')
    uploadSampleTemperatureCalibrationCurve = getattr(attoDRYLib,'AttoDRY_Interface_uploadSampleTemperatureCalibrationCurve')
    uploadTemperatureCalibrationCurve = getattr(attoDRYLib,'AttoDRY_Interface_uploadTemperatureCalibrationCurve')
    
    ##### asking questions
    isControllingField = getattr(attoDRYLib,'AttoDRY_Interface_isControllingField')
    isControllingTemperature = getattr(attoDRYLib,'AttoDRY_Interface_isControllingTemperature')
    isDeviceConnected = getattr(attoDRYLib,'AttoDRY_Interface_isDeviceConnected')
    isDeviceInitialised = getattr(attoDRYLib,'AttoDRY_Interface_isDeviceInitialised')
    isGoingToBaseTemperature = getattr(attoDRYLib,'AttoDRY_Interface_isGoingToBaseTemperature')
    isExchangeHeaterOn = getattr(attoDRYLib,'AttoDRY_Interface_isExchangeHeaterOn')
    isPersistentModeSet = getattr(attoDRYLib,'AttoDRY_Interface_isPersistentModeSet')
    isPumping = getattr(attoDRYLib,'AttoDRY_Interface_isPumping')
    isSampleExchangeInProgress = getattr(attoDRYLib,'AttoDRY_Interface_isSampleExchangeInProgress')
    isSampleHeaterOn = getattr(attoDRYLib,'AttoDRY_Interface_isSampleHeaterOn')
    isSampleReadyToExchange = getattr(attoDRYLib,'AttoDRY_Interface_isSampleReadyToExchange')
    isSystemRunning = getattr(attoDRYLib,'AttoDRY_Interface_isSystemRunning')
    isPumping = getattr(attoDRYLib,'AttoDRY_Interface_isPumping')
    isZeroingField = getattr(attoDRYLib,'AttoDRY_Interface_isZeroingField')
    
    ##### queries
    queryReservoirTsetColdSample = getattr(attoDRYLib,'AttoDRY_Interface_queryReservoirTsetColdSample') 
    queryReservoirTsetWarmMagnet = getattr(attoDRYLib,'AttoDRY_Interface_queryReservoirTsetWarmMagnet')
    queryReservoirTsetWarmSample = getattr(attoDRYLib,'AttoDRY_Interface_queryReservoirTsetWarmSample')
    querySampleHeaterMaximumPower = getattr(attoDRYLib,'AttoDRY_Interface_querySampleHeaterMaximumPower')
    querySampleHeaterResistance = getattr(attoDRYLib,'AttoDRY_Interface_querySampleHeaterResistance')
    querySampleHeaterWireResistance = getattr(attoDRYLib,'AttoDRY_Interface_querySampleHeaterWireResistance')
    
    ##### toggle commands
    toggleCryostatInValve = getattr(attoDRYLib,'AttoDRY_Interface_toggleCryostatInValve')
    toggleCryostatOutValve = getattr(attoDRYLib,'AttoDRY_Interface_toggleCryostatOutValve')
    toggleDumpInValve = getattr(attoDRYLib,'AttoDRY_Interface_toggleDumpInValve')
    toggleDumpOutValve = getattr(attoDRYLib,'AttoDRY_Interface_toggleDumpOutValve')
    toggleExchangeHeaterControl = getattr(attoDRYLib,'AttoDRY_Interface_toggleExchangeHeaterControl')
    toggleFullTemperatureControl = getattr(attoDRYLib,'AttoDRY_Interface_toggleFullTemperatureControl')
    toggleHeliumValve = getattr(attoDRYLib,'AttoDRY_Interface_toggleHeliumValve')
    toggleInnerVolumeValve = getattr(attoDRYLib,'AttoDRY_Interface_toggleInnerVolumeValve')
    toggleOuterVolumeValve = getattr(attoDRYLib,'AttoDRY_Interface_toggleOuterVolumeValve')
    toggleMagneticFieldControl = getattr(attoDRYLib,'AttoDRY_Interface_toggleMagneticFieldControl')
    togglePersistentMode = getattr(attoDRYLib,'AttoDRY_Interface_togglePersistentMode')
    togglePump = getattr(attoDRYLib,'AttoDRY_Interface_togglePump')
    togglePumpValve = getattr(attoDRYLib,'AttoDRY_Interface_togglePumpValve')
    toggleSampleTemperatureControl = getattr(attoDRYLib,'AttoDRY_Interface_toggleSampleTemperatureControl') 
    toggleStartUpShutdown = getattr(attoDRYLib,'AttoDRY_Interface_toggleStartUpShutdown') 
    
    ##### get values
    getCryostatInPressure = getattr(attoDRYLib,'AttoDRY_Interface_getCryostatInPressure')
    getCryostatInValve = getattr(attoDRYLib,'AttoDRY_Interface_getCryostatInValve')
    getCryostatOutPressure = getattr(attoDRYLib,'AttoDRY_Interface_getCryostatOutPressure')
    getCryostatOutValve = getattr(attoDRYLib,'AttoDRY_Interface_getCryostatOutValve')
    getDumpInValve = getattr(attoDRYLib,'AttoDRY_Interface_getDumpInValve')
    getDumpOutValve = getattr(attoDRYLib,'AttoDRY_Interface_getDumpOutValve')
    getDumpPressure = getattr(attoDRYLib,'AttoDRY_Interface_getDumpPressure')
    getHeliumValve = getattr(attoDRYLib,'AttoDRY_Interface_getHeliumValve')
    getInnerVolumeValve = getattr(attoDRYLib,'AttoDRY_Interface_getInnerVolumeValve')
    getOuterVolumeValve = getattr(attoDRYLib,'AttoDRY_Interface_getOuterVolumeValve')
    getReservoirHeaterPower = getattr(attoDRYLib,'AttoDRY_Interface_getReservoirHeaterPower')
    getReservoirTemperature = getattr(attoDRYLib,'AttoDRY_Interface_getReservoirTemperature')
    getReservoirTsetColdSample = getattr(attoDRYLib,'AttoDRY_Interface_getReservoirTsetColdSample')
    getReservoirTsetWarmMagnet = getattr(attoDRYLib,'AttoDRY_Interface_getReservoirTsetWarmMagnet')
    getReservoirTsetWarmSample = getattr(attoDRYLib,'AttoDRY_Interface_getReservoirTsetWarmSample')
    getPressure = getattr(attoDRYLib,'AttoDRY_Interface_getPressure')
    get40KStageTemperature = getattr(attoDRYLib,'AttoDRY_Interface_get40KStageTemperature')
    get4KStageTemperature = getattr(attoDRYLib,'AttoDRY_Interface_get4KStageTemperature')
    getDerivativeGain = getattr(attoDRYLib,'AttoDRY_Interface_getDerivativeGain')
    getIntegralGain = getattr(attoDRYLib,'AttoDRY_Interface_getIntegralGain')
    getMagneticField = getattr(attoDRYLib,'AttoDRY_Interface_getMagneticField')
    getMagneticFieldSetPoint = getattr(attoDRYLib,'AttoDRY_Interface_getMagneticFieldSetPoint')
    getProportionalGain = getattr(attoDRYLib,'AttoDRY_Interface_getProportionalGain')
    getSampleHeaterMaximumPower = getattr(attoDRYLib,'AttoDRY_Interface_getSampleHeaterMaximumPower')
    getSampleHeaterPower = getattr(attoDRYLib,'AttoDRY_Interface_getSampleHeaterPower')
    getSampleHeaterResistance = getattr(attoDRYLib,'AttoDRY_Interface_getSampleHeaterResistance')
    getSampleHeaterWireResistance = getattr(attoDRYLib,'AttoDRY_Interface_getSampleHeaterWireResistance')
    getSampleTemperature = getattr(attoDRYLib,'AttoDRY_Interface_getSampleTemperature')
    getUserTemperature = getattr(attoDRYLib,'AttoDRY_Interface_getUserTemperature')
    getVtiHeaterPower = getattr(attoDRYLib,'AttoDRY_Interface_getVtiHeaterPower')
    getVtiTemperature = getattr(attoDRYLib,'AttoDRY_Interface_getVtiTemperature')
    getPumpValve = getattr(attoDRYLib,'AttoDRY_Interface_getPumpValve')
    getTurbopumpFrequency = getattr(attoDRYLib,'AttoDRY_Interface_getTurbopumpFrequency')
    
    ##### set values
    setDerivativeGain = getattr(attoDRYLib,'AttoDRY_Interface_setDerivativeGain')
    setIntegralGain = getattr(attoDRYLib,'AttoDRY_Interface_setIntegralGain')
    setProportionalGain = getattr(attoDRYLib,'AttoDRY_Interface_setProportionalGain')
    setReservoirTsetColdSample = getattr(attoDRYLib,'AttoDRY_Interface_setReservoirTsetColdSample')
    setReservoirTsetWarmMagnet = getattr(attoDRYLib,'AttoDRY_Interface_setReservoirTsetWarmMagnet')
    setReservoirTsetWarmSample = getattr(attoDRYLib,'AttoDRY_Interface_setReservoirTsetWarmSample')
    setSampleHeaterMaximumPower = getattr(attoDRYLib,'AttoDRY_Interface_setSampleHeaterMaximumPower')
    setSampleHeaterPower = getattr(attoDRYLib,'AttoDRY_Interface_setSampleHeaterPower')
    setSampleHeaterResistance = getattr(attoDRYLib,'AttoDRY_Interface_setSampleHeaterResistance')
    setSampleHeaterWireResistance = getattr(attoDRYLib,'AttoDRY_Interface_setSampleHeaterWireResistance')
    setUserMagneticField = getattr(attoDRYLib,'AttoDRY_Interface_setUserMagneticField')
    setUserTemperature = getattr(attoDRYLib,'AttoDRY_Interface_setUserTemperature')
    setVTIHeaterPower = getattr(attoDRYLib,'AttoDRY_Interface_setVTIHeaterPower')
    
    
    
    #############################################################################################################
    ##### error checking and handling...
    #############################################################################################################
    
    ##### communication
    getActionMessage.errcheck = checkError
    begin.errcheck = checkError
    Cancel.errcheck = checkError
    Confirm.errcheck = checkError
    Connect.errcheck = checkError
    Main.errcheck = checkError
    Disconnect.errcheck = checkError
    end.errcheck = checkError
    getAttodryErrorMessage.errcheck = checkError
    getAttodryErrorStatus.errcheck = checkError
    goToBaseTemperature.errcheck = checkError
    lowerError.errcheck = checkError
    startLogging.errcheck = checkError
    startSampleExchange.errcheck = checkError
    stopLogging.errcheck = checkError
    sweepFieldToZero.errcheck = checkError
    downloadSampleTemperatureSensorCalibrationCurve.errcheck = checkError
    downloadTemperatureSensorCalibrationCurve.errcheck = checkError
    uploadSampleTemperatureCalibrationCurve.errcheck = checkError
    uploadTemperatureCalibrationCurve.errcheck = checkError
    LVDLLStatus.errcheck = checkError
    
    ##### asking questions
    isControllingField.errcheck = checkError
    isControllingTemperature.errcheck = checkError
    isDeviceConnected.errcheck = checkError
    isDeviceInitialised.errcheck = checkError
    isGoingToBaseTemperature.errcheck = checkError
    isExchangeHeaterOn.errcheck = checkError
    isPersistentModeSet.errcheck = checkError
    isPumping.errcheck = checkError
    isSampleExchangeInProgress.errcheck = checkError
    isSampleHeaterOn.errcheck = checkError
    isSampleReadyToExchange.errcheck = checkError
    isSystemRunning.errcheck = checkError
    isPumping.errcheck = checkError
    isZeroingField.errcheck = checkError
    
    ##### queries
    queryReservoirTsetColdSample.errcheck = checkError 
    queryReservoirTsetWarmMagnet.errcheck = checkError
    queryReservoirTsetWarmSample.errcheck = checkError
    querySampleHeaterMaximumPower.errcheck = checkError
    querySampleHeaterResistance.errcheck = checkError
    querySampleHeaterWireResistance.errcheck = checkError
    
    ##### toggle commands
    toggleCryostatInValve.errcheck = checkError
    toggleCryostatOutValve.errcheck = checkError
    toggleDumpInValve.errcheck = checkError
    toggleDumpOutValve.errcheck = checkError
    toggleExchangeHeaterControl.errcheck = checkError
    toggleFullTemperatureControl.errcheck = checkError
    toggleHeliumValve.errcheck = checkError
    toggleInnerVolumeValve.errcheck = checkError
    toggleOuterVolumeValve.errcheck = checkError
    toggleMagneticFieldControl.errcheck = checkError
    togglePersistentMode.errcheck = checkError
    togglePump.errcheck = checkError
    togglePumpValve.errcheck = checkError
    toggleSampleTemperatureControl.errcheck = checkError
    toggleStartUpShutdown.errcheck = checkError
    
    ##### get values
    getCryostatInPressure.errcheck = checkError
    getCryostatInValve.errcheck = checkError
    getCryostatOutPressure.errcheck = checkError
    getCryostatOutValve.errcheck = checkError
    getDumpInValve.errcheck = checkError
    getDumpOutValve.errcheck = checkError
    getDumpPressure.errcheck = checkError
    getHeliumValve.errcheck = checkError
    getInnerVolumeValve.errcheck = checkError
    getOuterVolumeValve.errcheck = checkError
    getReservoirHeaterPower.errcheck = checkError
    getReservoirTemperature.errcheck = checkError
    getReservoirTsetColdSample.errcheck = checkError
    getReservoirTsetWarmMagnet.errcheck = checkError
    getReservoirTsetWarmSample.errcheck = checkError
    getPressure.errcheck = checkError
    get40KStageTemperature.errcheck = checkError
    get4KStageTemperature.errcheck = checkError
    getDerivativeGain.errcheck = checkError
    getIntegralGain.errcheck = checkError
    getMagneticField.errcheck = checkError
    getMagneticFieldSetPoint.errcheck = checkError
    getProportionalGain.errcheck = checkError
    getSampleHeaterMaximumPower.errcheck = checkError
    getSampleHeaterPower.errcheck = checkError
    getSampleHeaterResistance.errcheck = checkError
    getSampleHeaterWireResistance.errcheck = checkError
    getSampleTemperature.errcheck = checkError
    getUserTemperature.errcheck = checkError
    getVtiHeaterPower.errcheck = checkError
    getVtiTemperature.errcheck = checkError
    getPumpValve.errcheck = checkError
    getTurbopumpFrequency.errcheck = checkError
    
    ##### set values
    setDerivativeGain.errcheck = checkError
    setIntegralGain.errcheck = checkError
    setProportionalGain.errcheck = checkError
    setReservoirTsetColdSample.errcheck = checkError
    setReservoirTsetWarmMagnet.errcheck = checkError
    setReservoirTsetWarmSample.errcheck = checkError
    setSampleHeaterMaximumPower.errcheck = checkError
    setSampleHeaterPower.errcheck = checkError
    setSampleHeaterResistance.errcheck = checkError
    setSampleHeaterWireResistance.errcheck = checkError
    setUserMagneticField.errcheck = checkError
    setUserTemperature.errcheck = checkError
    setVTIHeaterPower.errcheck = checkError

class AttoDry:

	def begin(setup_version):
		"""
		Starts the server that communicates with the attoDRY and loads the software 
		for the device specified by <B> Device </B>. This VI needs to be run before 
		commands can be sent or received. The <B>UI Queue</B> is an event queue for 
		updating the GUI. It should not be used when calling the function from a 
		DLL.
		Setup versions:
		0: attoDRY1100
		1: attoDRY2100
		2: attoDRY800
		"""
		c = ctypes.c_uint16(setup_version)
		ADRY.begin(c.value)

	def Connect(COMPort='COM4'):
		"""
		Connects to the attoDRY using the specified COM Port
		"""
		COMPort = COMPort.encode('utf-8')
		ADRY.Connect(ctypes.c_char_p(COMPort).value)

	"""
	def Main():
		#AttoDRY_Interface_Main
		ADRY.Main()
	"""
		
	def Disconnect():
		"""
		Disconnects from the attoDRY, if already connected. This should be run 
		before the <B>end.vi</B>
		"""
		ADRY.Disconnect()


	def end():
		"""
		Stops the server that is communicating with the attoDRY. The 
		<B>Disconnect.vi</B> should be run before this. This VI should be run 
		before closing your program.
		"""
		ADRY.end()


	def Cancel():
		"""
		Sends a 'Cancel' Command to the attoDRY. Use this when you want to cancel 
		an action or respond negatively to a pop up.
		"""
		ADRY.Cancel()


	def Confirm():
		"""
		Sends a 'Confirm' command to the attoDRY. Use this when you want to respond 
		positively to a pop up.
		"""
		ADRY.Confirm()


	def getActionMessage(length=500):
		"""
		Gets the current action message. If an action is being performed, it will 
		be shown here. It is similar to the pop ups on the display.
 		"""
		ActionMessage = ctypes.create_string_buffer(length)
		l = ctypes.c_int(length)
		ADRY.getAttodryErrorMessage(ctypes.byref(ActionMessage), l)
		return ActionMessage.value.decode('utf-8')


	def getAttodryErrorMessage(length=500):
		"""
		Returns the current error message with length 500; Change that if characters are missing
		Too long should not be a problem(?)
		"""
		ErrorStatus = ctypes.create_string_buffer(length)
		l = ctypes.c_int(length)
		ADRY.getAttodryErrorMessage(ctypes.byref(ErrorStatus), l)
		return ErrorStatus.value.decode('utf-8')


	def getAttodryErrorStatus():
		"""
		Returns the current error code
		"""
		ErrorCode = ctypes.c_int()
		ADRY.getAttodryErrorStatus(ctypes.byref(ErrorCode))
		return ErrorCode.value


	def isControllingField():
		"""
		Returns 'True' if magnetic filed control is active. This is true when the 
		magnetic field control icon on the touch screen is orange, and false when 
		the icon is white.
		"""
		ControllingField = ctypes.c_int()
		ADRY.isControllingField(ctypes.byref(ControllingField))
		return ControllingField.value


	def isControllingTemperature():
		"""
		Returns 'True' if temperature control is active. This is true when the 
		temperature control icon on the touch screen is orange, and false when the 
		icon is white.
		"""
		ControllingTemperature = ctypes.c_int()
		ADRY.isControllingTemperature(ctypes.byref(ControllingTemperature))
		return ControllingTemperature.value


	def isPersistentModeSet():
		"""
		Checks to see if persistant mode is set for the magnet. Note: this shows if 
		persistant mode is set, it does not show if the persistant switch heater is 
		on. The heater may be on during persistant mode when, for example, changing 
		the field.
		"""
		PersistentMode = ctypes.c_int()
		ADRY.isPersistentModeSet(ctypes.byref(PersistentMode))
		return PersistentMode.value


	def isDeviceInitialised():
		"""
		Checks to see if the attoDRY has initialised. Use this VI after you have 
		connected and before sending any commands or getting any data from the 
		attoDRY
		"""
		DeviceInitialised = ctypes.c_int()
		ADRY.isDeviceInitialised(ctypes.byref(DeviceInitialised))
		return DeviceInitialised.value

	def isDeviceConnected():
		"""
		Checks to see if the attoDRY is connected. Returns True if connected.
		"""
		DeviceConnected = ctypes.c_int()
		ADRY.isDeviceConnected(ctypes.byref(DeviceConnected))
		return DeviceConnected.value


	def toggleMagneticFieldControl():
		"""
		Toggles persistant mode for magnet control. If it is enabled, the switch 
		heater will be turned off once the desired field is reached. If it is not, 
		the switch heater will be left on.
 		"""
		ADRY.toggleMagneticFieldControl()


	def togglePersistentMode():
		"""
		Starts and stops the pump. If the pump is running, it will stop it. If the 
		pump is not running, it will be started.
 		"""
		ADRY.togglePersistentMode()


	def toggleSampleTemperatureControl():
		"""
		This command only toggles the sample temperature controller. It does not 
		pump the volumes etc. Use  <B>toggleFullTemperatureControl.vi</B> for 
		behaviour like the temperature control icon on the touch screen.
 		"""
		ADRY.toggleSampleTemperatureControl()


	def toggleFullTemperatureControl():
		"""
		This command only toggles the sample temperature controller. It does not 
		pump the volumes etc. Use  <B>toggleFullTemperatureControl.vi</B> for 
		behaviour like the temperature control icon on the touch screen.
 		"""
		ADRY.toggleFullTemperatureControl()


	def goToBaseTemperature():
		"""
		Initiates the "Base Temperature" command, as on the touch screen
 		"""
		ADRY.goToBaseTemperature()


	def get4KStageTemperature():
		"""
		Gets the current magnetic fiel
		"""
		StageTemperature = ctypes.c_float()
		ADRY.get4KStageTemperature(ctypes.byref(StageTemperature))
		return StageTemperature.value
		

	def getMagneticField():
		"""
		Gets the current magnetic fiel
		"""
		MagneticField = ctypes.c_float()
		ADRY.getMagneticField(ctypes.byref(MagneticField))
		return MagneticField.value


	def getMagneticFieldSetPoint():
		"""
		Gets the current magnetic field set point
		"""
		MagneticField = ctypes.c_float()
		ADRY.getMagneticFieldSetPoint(ctypes.byref(MagneticField))
		return MagneticField.value


	def getSampleTemperature():
		"""
		Gets the sample temperature in Kelvin. This value is updated whenever a 
		status message is received from the attoDRY.
		"""
		Temperature = ctypes.c_float()
		ADRY.getSampleTemperature(ctypes.byref(Temperature))
		return Temperature.value


	def getUserTemperature():
		"""
		Gets the user set point temperature, in Kelvin. This value is updated 
		whenever a status message is received from the attoDRY.
		"""
		Temperature = ctypes.c_float()
		ADRY.getUserTemperature(ctypes.byref(Temperature))
		return Temperature.value


	def setUserMagneticField(MagneticField):
		"""
		Sets the user magntic field. This is used as the set point when field 
		control is active
		"""
		ADRY.setUserMagneticField(ctypes.c_float(MagneticField))


	def setUserTemperature(Temperature):
		"""
		Sets the user temperature. This is the temperature used when temperature 
		control is enabled.
		"""
		ADRY.setUserTemperature(ctypes.c_float(Temperature))

##################################################################################
##### Functions below this line were not tested!
##### TODO: test the following functions
##################################################################################

	def downloadSampleTemperatureSensorCalibrationCurve(savepath):
		"""
		Starts the download of the <B>Sample Temperature Sensor Calibration 
		Curve</B>. The curve will be saved to <B>Save Path</B>
		"""
		Savepath = savepath.encode('utf-8')
		ADRY.downloadSampleTemperatureSensorCalibrationCurve(ctypes.c_char_p(Savepath).value)


	def downloadTemperatureSensorCalibrationCurve(UserCurveNumber,savepath):
		"""
		Starts the download of the Temperature Sensor Calibration Curve at <b>User 
		Curve Number</B> on the temperature monitor. The curve will be saved to 
		<B>Path</B>
		"""
		Savepath = savepath.encode('utf-8')
		ADRY.downloadTemperatureSensorCalibrationCurve(ctypes.c_int(UserCurveNumber),ctypes.c_char_p(Savepath).value)


	def getDerivativeGain():
		"""
		Gets the Derivative gain. The gain retrieved depends on which heater is 
		active:
		- If no heaters are on or the sample heater is on, the <B>Sample Heater</B> 
		gain is returned
		- If the VTI heater is on and a sample temperature sensor is connected, the 
		<B>VTI Heater</B> gain is returned
		- If the VTI heater is on and no sample temperature sensor is connected, 
		the <B>Exchange Heater</B> gain is returned
		 """
		DerivativeGain = ctypes.c_float()
		ADRY.getDerivativeGain(ctypes.byref(DerivativeGain))
		return DerivativeGain.value


	def getIntegralGain():
		"""
		Gets the Integral gain. The gain retrieved depends on which heater is 
		active:
		- If no heaters are on or the sample heater is on, the <B>Sample Heater</B> 
		gain is returned
		- If the VTI heater is on and a sample temperature sensor is connected, the 
		<B>VTI Heater</B> gain is returned
		- If the VTI heater is on and no sample temperature sensor is connected, 
		the <B>Exchange Heater</B> gain is returned
		"""
		IntegralGain = ctypes.c_float()
		ADRY.getIntegralGain(ctypes.byref(IntegralGain))
		return IntegralGain.value


	def getProportionalGain():
		"""
		Gets the Proportional gain. The gain retrieved depends on which heater is 
		active:
		- If no heaters are on or the sample heater is on, the <B>Sample Heater</B> 
		gain is returned
		- If the VTI heater is on and a sample temperature sensor is connected, the 
		<B>VTI Heater</B> gain is returned
		- If the VTI heater is on and no sample temperature sensor is connected, 
		the <B>Exchange Heater</B> gain is returned
		"""
		ProportionalGain = ctypes.c_float()
		ADRY.getProportionalGain(ctypes.byref(ProportionalGain))
		return ProportionalGain.value


	def getSampleHeaterMaximumPower():
		"""
		Gets the maximum power limit of the sample heater in Watts. This value, is 
		the one stored in memory on the computer, not the one on the attoDRY. You 
		should first use the appropriate <B>query VI</B> to request the value from 
		the attoDRY.
		
		The output power of the heater will not exceed this value. It is stored in 
		non-volatile memory, this means that the value will not be lost, even if 
		the attoDRY is turned off.
		"""
		SampleHeaterMaximumPower = ctypes.c_float()
		ADRY.getSampleHeaterMaximumPower(ctypes.byref(SampleHeaterMaximumPower))
		return SampleHeaterMaximumPower.value


	def getSampleHeaterPower():
		"""
		Gets the current Sample Heater power, in Watts
		"""
		SampleHeaterPower = ctypes.c_float()
		ADRY.getSampleHeaterPower(ctypes.byref(SampleHeaterPower))
		return SampleHeaterPower.value


	def getSampleHeaterResistance():
		"""
		Gets the resistance of the sample heater in Ohms. This value, is the one 
		stored in memory on the computer, not the one on the attoDRY. You should 
		first use the appropriate <B>query VI</B> to request the value from the 
		attoDRY.
		
		This value, along with the heater wire resistance, is used in calculating 
		the output power of the heater. It is stored in non-volatile memory, this 
		means that the value will not be lost, even if the attoDRY is turned off.
		
		Power = Voltage^2/((HeaterResistance + WireResistance)^2) * 
		HeaterResistance
		"""
		SampleHeaterResistance = ctypes.c_float()
		ADRY.getSampleHeaterResistance(ctypes.byref(SampleHeaterResistance))
		return SampleHeaterResistance.value


	def getSampleHeaterWireResistance():
		"""
		Gets the resistance of the sample heater wires in Ohms. This value, is the 
		one stored in memory on the computer, not the one on the attoDRY. You 
		should first use the appropriate <B>query VI</B> to request the value from 
		the attoDRY.
		
		This value, along with the heater resistance, is used in calculating the 
		output power of the heater. It is stored in non-volatile memory, this means 
		that the value will not be lost, even if the attoDRY is turned off.
		
		Power = Voltage^2/((HeaterResistance + WireResistance)^2) * 
		HeaterResistance
 		"""
		SampleHeaterWireResistance = ctypes.c_float()
		ADRY.getSampleHeaterWireResistance(ctypes.byref(SampleHeaterWireResistance))
		return SampleHeaterWireResistance.value


	def getVtiHeaterPower():
		"""
		Returns the VTI Heater power, in Watts
		"""
		VtiHeaterPower = ctypes.c_float()
		ADRY.getVtiHeaterPower(ctypes.byref(VtiHeaterPower))
		return VtiHeaterPower.value



	def getVtiTemperature():
		"""
		Returns the temperature of the VTI
		"""
		VtiTemperature = ctypes.c_float()
		ADRY.getVtiTemperature(ctypes.byref(VtiTemperature))
		return VtiTemperature.value


	def isGoingToBaseTemperature():
		"""
		Returns 'True' if the base temperature process is active. This is true when 
		the base temperature button on the touch screen is orange, and false when 
		the button is white.
		"""
		GoingToBaseTemperature = ctypes.c_int()
		ADRY.isGoingToBaseTemperature(ctypes.byref(GoingToBaseTemperature))
		return GoingToBaseTemperature.value


	def isPumping():
		"""
		Returns true if the pump is running
		"""
		Pumping = ctypes.c_int()
		ADRY.isPumping(ctypes.byref(Pumping))
		return Pumping.value


	def isSampleExchangeInProgress():
		"""
		Returns 'True' if the sample exchange process is active. This is true when 
		the sample exchange button on the touch screen is orange, and false when 
		the button is white.
		"""
		SampleExchangeInProgress = ctypes.c_int()
		ADRY.isSampleExchangeInProgress(ctypes.byref(SampleExchangeInProgress))
		return SampleExchangeInProgress.value



	def isSampleHeaterOn():
		"""
		Checks to see if the sample heater is on. 'On' is defined as PID control is 
		active or a contant heater power is set. 
		"""
		SampleHeaterOn = ctypes.c_int()
		ADRY.isSampleHeaterOn(ctypes.byref(SampleHeaterOn))
		return SampleHeaterOn.value


	def isSampleReadyToExchange():
		"""
		This will return true when the sample stick is ready to be removed or 
		inserted.
		"""
		SampleReadyToExchange = ctypes.c_int()
		ADRY.isSampleReadyToExchange(ctypes.byref(SampleReadyToExchange))
		return SampleReadyToExchange.value


	def isSystemRunning():
		"""
		This will return true when the sample stick is ready to be removed or 
		inserted.
		"""
		SystemRunning = ctypes.c_int()
		ADRY.isSystemRunning(ctypes.byref(SystemRunning))
		return SystemRunning.value


	def isZeroingField():
		"""
		This will return true when the sample stick is ready to be removed or 
		inserted.
		"""
		ZeroingField = ctypes.c_int()
		ADRY.isZeroingField(ctypes.byref(ZeroingField))
		return ZeroingField.value


	def lowerError():
		"""
		Lowers any raised errors
		"""
		ADRY.lowerError()


	def querySampleHeaterMaximumPower():
		"""
		Requests the maximum power limit of the sample heater in Watts from the 
		attoDRY. After running this command, use the appropriate <B>get VI</B> to 
		get the value stored on the computer.
		
		The output power of the heater will not exceed this value. It is stored in 
		non-volatile memory, this means that the value will not be lost, even if 
		the attoDRY is turned off.
		"""
		ADRY.querySampleHeaterMaximumPower()



	def querySampleHeaterResistance():
		"""
		Requests the  resistance of the sample heater in Ohms from the attoDRY. 
		After running this command, use the appropriate <B>get VI</B> to get the 
		value stored on the computer.
		
		This value, along with the heater wire resistance, is used in calculating 
		the output power of the heater. It is stored in non-volatile memory, this 
		means that the value will not be lost, even if the attoDRY is turned off.
		
		Power = Voltage^2/((HeaterResistance + WireResistance)^2) * 
		HeaterResistance
		"""
		ADRY.querySampleHeaterResistance()


	def querySampleHeaterWireResistance():
		"""
		Requests the  resistance of the sample wires heater in Ohms from the 
		attoDRY. After running this command, use the appropriate <B>get VI</B> to 
		get the value stored on the computer.
		
		This value, along with the heater resistance, is used in calculating the 
		output power of the heater. It is stored in non-volatile memory, this means 
		that the value will not be lost, even if the attoDRY is turned off.

		Power = Voltage^2/((HeaterResistance + WireResistance)^2) * 
		HeaterResistance
		"""
		ADRY.querySampleHeaterWireResistance()


	def setDerivativeGain(DerivativeGain):
		"""
		Sets the Derivative gain. The controller that is updated depends on which 
		heater is active:
		- If no heaters are on or the sample heater is on, the <B>Sample Heater</B> 
		gain is set
		- If the VTI heater is on and a sample temperature sensor is connected, the 
		<B>VTI Heater</B> gain is set
		- If the VTI heater is on and no sample temperature sensor is connected, 
		the <B>Exchange Heater</B> gain is set
		"""
		ADRY.setDerivativeGain(ctypes.c_float(DerivativeGain))


	def setIntegralGain(IntegralGain):
		"""
		Sets the Integral gain. The controller that is updated depends on which 
		heater is active:
		- If no heaters are on or the sample heater is on, the <B>Sample Heater</B> 
		gain is set
		- If the VTI heater is on and a sample temperature sensor is connected, the 
		<B>VTI Heater</B> gain is set
		- If the VTI heater is on and no sample temperature sensor is connected, 
		the <B>Exchange Heater</B> gain is set
		"""
		ADRY.setIntegralGain(ctypes.c_float(IntegralGain))


	def setProportionalGain(ProportionalGain):
		"""
		Sets the Proportional gain. The controller that is updated depends on which 
		heater is active:
		- If no heaters are on or the sample heater is on, the <B>Sample Heater</B> 
		gain is set
		- If the VTI heater is on and a sample temperature sensor is connected, the 
		<B>VTI Heater</B> gain is set
		- If the VTI heater is on and no sample temperature sensor is connected, 
		the <B>Exchange Heater</B> gain is set
		"""
		ADRY.setProportionalGain(ctypes.c_float(ProportionalGain))


	def setSampleHeaterMaximumPower(MaximumPower):
		"""
		Sets the maximum power limit of the sample heater in Watts. After running 
		this command, use the appropriate <B>request</B> and <B>get</B> VIs to 
		check the value was stored on the attoDRY.
		
		The output power of the heater will not exceed this value. 
		
		It is stored in non-volatile memory, this means that the value will not be 
		lost, even if the attoDRY is turned off. Note: the non-volatile memory has 
		a specified life of 100,000 write/erase cycles, so you may need to be 
		careful about how often you set this value.
		"""
		ADRY.setSampleHeaterMaximumPower(ctypes.c_float(MaximumPower))


	def setSampleHeaterWireResistance(WireResistance):
		"""
		Sets the resistance of the sample heater wires in Ohms. After running this 
		command, use the appropriate <B>request</B> and <B>get</B> VIs to check the 
		value was stored on the attoDRY.
		
		This value, along with the heater resistance, is used in calculating the 
		output power of the heater. It is stored in non-volatile memory, this means 
		that the value will not be lost, even if the attoDRY is turned off.
		
		Power = Voltage^2/((HeaterResistance + WireResistance)^2) * 
		HeaterResistance
		
		It is stored in non-volatile memory, this means that the value will not be 
		lost, even if the attoDRY is turned off. Note: the non-volatile memory has 	
		a specified life of 100,000 write/erase cycles, so you may need to be 
		careful about how often you set this value.
		"""
		ADRY.setSampleHeaterWireResistance(ctypes.c_float(WireResistance))


	def setSampleHeaterPower(HeaterPowerW):
		"""
		Sets the sample heater value to the specified value
		"""
		ADRY.setSampleHeaterPower(ctypes.c_float(HeaterPowerW))


	def setSampleHeaterResistance(HeaterResistance):
		"""
		Sets the resistance of the sample heater in Ohms. After running this 
		command, use the appropriate <B>request</B> and <B>get</B> VIs to check the 
		value was stored on the attoDRY.
		
		This value, along with the heater wire resistance, is used in calculating 
		the output power of the heater. It is stored in non-volatile memory, this 
		means that the value will not be lost, even if the attoDRY is turned off.
		
		Power = Voltage^2/((HeaterResistance + WireResistance)^2) * 
		HeaterResistance
		 
		It is stored in non-volatile memory, this means that the value will not be 
		lost, even if the attoDRY is turned off. Note: the non-volatile memory has 
		a specified life of 100,000 write/erase cycles, so you may need to be 
		careful about how often you set this value.
		"""
		ADRY.setSampleHeaterResistance(ctypes.c_float(HeaterResistance))


	def startLogging(savepath,TimeSelection,Append):
		"""
		Starts logging data to the file specifed by <B>Path</B>. 

		If the file does not exist, it will be created.
		The TimeSelection is given as 
		#define Enum__1Second 0
		#define Enum__5Seconds 1
		#define Enum__30Seconds 2
		#define Enum__1Minute 3
		#define Enum__5Minutes 4
		"""
		Savepath = savepath.encode('utf-8')
		ADRY.startLogging(ctypes.c_char_p(Savepath).value,ctypes.c_int(TimeSelection).value,ctypes.c_int(Append).value)


	def startSampleExchange():
		"""
		Starts the sample exchange procedure
		"""
		ADRY.startSampleExchange()


	def stopLogging():
		"""
		Stops logging data
		"""
		ADRY.stopLogging()


	def sweepFieldToZero():
		"""
		Initiates the "Zero Field" command, as on the touch screen
		"""
		ADRY.sweepFieldToZero()


	def togglePump():
		"""
		Starts and stops the pump. If the pump is running, it will stop it. If the 
		pump is not running, it will be started.
		"""
		ADRY.togglePump()


	def toggleStartUpShutdown():
		"""
		Toggles the start up/shutdown procedure. If the attoDRY is started up, the 
		shut down procedure will be run and vice versa
		"""
		ADRY.toggleStartUpShutdown()


	def uploadSampleTemperatureCalibrationCurve(loadpath):
		"""
		Starts the upload of a <B>.crv calibration curve file</B> to the <B>sample 
		temperature sensor</B>
		"""
		Loadpath = loadpath.encode('utf-8')
		ADRY.uploadSampleTemperatureCalibrationCurve(ctypes.c_char_p(Loadpath).value)


	def uploadTemperatureCalibrationCurve(loadpath,UserCurveNumber):
		"""
		Starts the upload of a <B>.crv calibration curve file</B> to the specified 
		<B>User Curve Number</B> on the temperature monitor. Use a curve number of 
		1 to 8, inclusive
		"""
		Loadpath = loadpath.encode('utf-8')
		ADRY.uploadTemperatureCalibrationCurve(ctypes.c_int(UserCurveNumber).value,ctypes.c_char_p(Loadpath).value)


	def setVTIHeaterPower(VTIHeaterPowerW):
		"""
		AttoDRY_Interface_setVTIHeaterPower
		"""
		ADRY.setVTIHeaterPower(ctypes.c_float(VTIHeaterPowerW))


	def queryReservoirTsetColdSample():
		"""
		AttoDRY_Interface_queryReservoirTsetColdSample
		"""
		ADRY.queryReservoirTsetColdSample()


	def getReservoirTsetColdSample():
		"""
		AttoDRY_Interface_getReservoirTsetColdSample
		"""
		ReservoirTsetColdSampleK = ctypes.c_float()
		ADRY.getReservoirTsetColdSample(ctypes.byref(ReservoirTsetColdSampleK))
		return ReservoirTsetColdSampleK.value


	def setReservoirTsetWarmMagnet(ReservoirTsetWarmMagnetW):
		"""
		AttoDRY_Interface_setReservoirTsetWarmMagnet
		"""
		ADRY.setReservoirTsetWarmMagnet(ctypes.c_float(ReservoirTsetWarmMagnetW))


	def setReservoirTsetColdSample(SetReservoirTsetColdSampleK):
		"""
		AttoDRY_Interface_setReservoirTsetColdSample
		"""
		ADRY.setReservoirTsetColdSample(ctypes.c_float(SetReservoirTsetColdSampleK))


	def setReservoirTsetWarmSample(ReservoirTsetWarmSampleW):
		"""
		AttoDRY_Interface_setReservoirTsetWarmSample
		"""
		ADRY.setReservoirTsetWarmSample(ctypes.c_float(ReservoirTsetWarmSampleW))


	def queryReservoirTsetWarmSample():
		"""
		AttoDRY_Interface_queryReservoirTsetWarmSample
		"""
		ADRY.queryReservoirTsetWarmSample()


	def queryReservoirTsetWarmMagnet():
		"""
		AttoDRY_Interface_queryReservoirTsetWarmMagnet
		"""
		ADRY.queryReservoirTsetWarmMagnet()


	def getReservoirTsetWarmSample():
		"""
		AttoDRY_Interface_getReservoirTsetWarmSample
		"""
		ReservoirTsetWarmSampleK = ctypes.c_float()
		ADRY.getReservoirTsetWarmSample(ctypes.byref(ReservoirTsetWarmSampleK))
		return ReservoirTsetWarmSampleK.value


	def getReservoirTsetWarmMagnet():
		"""
		AttoDRY_Interface_getReservoirTsetWarmMagnet
		"""
		ReservoirTsetWarmMagnetK = ctypes.c_float()
		ADRY.getReservoirTsetWarmMagnet(ctypes.byref(ReservoirTsetWarmMagnetK))
		return ReservoirTsetWarmMagnetK.value


	def getCryostatInPressure():
		"""
		ATTODRY2100 ONLY. Gets the pressure at the Cryostat Inlet
		"""
		CryostatInPressureMbar = ctypes.c_float()
		ADRY.getCryostatInPressure(ctypes.byref(CryostatInPressureMbar))
		return CryostatInPressureMbar.value


	def getCryostatInValve():
		"""
		ATTODRY2100 ONLY. Gets the current status of the Cryostat In valve.
		"""
		valveStatus = ctypes.c_int()
		ADRY.getCryostatInValve(ctypes.byref(valveStatus))
		return valveStatus.value


	def getCryostatOutPressure():
		"""
		Gets the Cryostat Outlet pressure
		"""
		CryostatOutPressureMbar = ctypes.c_float()
		ADRY.getCryostatOutPressure(ctypes.byref(CryostatOutPressureMbar))
		return CryostatOutPressureMbar.value


	def getCryostatOutValve():
		"""
		ATTODRY2100 ONLY. Gets the current status of the Cryostat Out valve.
		"""
		valveStatus = ctypes.c_int()
		ADRY.getCryostatOutValve(ctypes.byref(valveStatus))
		return valveStatus.value


	def getDumpInValve():
		"""
		ATTODRY2100 ONLY. Gets the current status of the Dump In volume valve. 
		"""
		valveStatus = ctypes.c_int()
		ADRY.getDumpInValve(ctypes.byref(valveStatus))
		return valveStatus.value


	def getDumpOutValve():
		"""
		ATTODRY2100 ONLY. Gets the current status of the outer volume valve. 
		"""
		valveStatus = ctypes.c_int()
		ADRY.getDumpOutValve(ctypes.byref(valveStatus))
		return valveStatus.value


	def getDumpPressure():
		"""
		ATTODRY2100 ONLY. Gets the pressure at the Dump
		"""
		DumpPressureMbar = ctypes.c_float()
		ADRY.getDumpPressure(ctypes.byref(DumpPressureMbar))
		return DumpPressureMbar.value


	def getReservoirHeaterPower():
		"""
		ATTODRY2100 ONLY. Gets the pressure at the Dump
		"""
		ReservoirHeaterPowerW = ctypes.c_float()
		ADRY.getReservoirHeaterPower(ctypes.byref(ReservoirHeaterPowerW))
		return ReservoirHeaterPowerW.value


	def getReservoirTemperature():
		"""
		ATTODRY2100 ONLY. Gets the pressure at the Dump
		"""
		ReservoirTemperatureK = ctypes.c_float()
		ADRY.getReservoirTemperature(ctypes.byref(ReservoirTemperatureK))
		return ReservoirTemperatureK.value


	def toggleCryostatInValve():
		"""
		ATTODRY2100 ONLY. Toggles the Cryostat In valve. If it is closed, it will 
		open and if it is open, it will close. 
		"""
		ADRY.toggleCryostatInValve()


	def toggleCryostatOutValve():
		"""
		ATTODRY2100 ONLY. Toggles the Cryostat Out valve. If it is closed, it will 
		open and if it is open, it will close. 
		"""
		ADRY.toggleCryostatOutValve()


	def toggleDumpInValve():
		"""
		ATTODRY2100 ONLY. Toggles the inner volume valve. If it is closed, it will 
		open and if it is open, it will close.  
		"""
		ADRY.toggleDumpInValve()


	def toggleDumpOutValve():
		"""
		ATTODRY2100 ONLY. Toggles the outer volume valve. If it is closed, it will 
		open and if it is open, it will close. 
		"""
		ADRY.toggleDumpOutValve()


	def get40KStageTemperature():
		"""
		ATTODRY1100 ONLY. Gets the current temperature of the 40K Stage, in Kelvin
		"""
		StageTemperatureK = ctypes.c_float()
		ADRY.get40KStageTemperature(ctypes.byref(StageTemperatureK))
		return StageTemperatureK.value


	def getHeliumValve():
		"""
		ATTODRY1100 ONLY. Gets the current status of the helium valve. True is 
		opened, false is closed.
		"""
		valveStatus = ctypes.c_int()
		ADRY.getHeliumValve(ctypes.byref(valveStatus))
		return valveStatus.value


	def getInnerVolumeValve():
		"""
		ATTODRY1100 ONLY. Gets the current status of the inner volume valve. True 
		is opened, false is closed.
		"""
		valveStatus = ctypes.c_int()
		ADRY.getInnerVolumeValve(ctypes.byref(valveStatus))
		return valveStatus.value


	def getOuterVolumeValve():
		"""
		ATTODRY1100 ONLY. Gets the current status of the outer volume valve. True 
		is opened, false is closed.
		"""
		valveStatus = ctypes.c_int()
		ADRY.getOuterVolumeValve(ctypes.byref(valveStatus))
		return valveStatus.value


	def getPressure():
		"""
		ATTODRY1100 ONLY. Gets the current presure in the valve junction block, in 
		mbar. 
		"""
		PressureMbar = ctypes.c_float()
		ADRY.getPressure(ctypes.byref(PressureMbar))
		return PressureMbar.value


	def getPumpValve():
		"""
		ATTODRY1100 ONLY. Gets the current status of the pump valve. True is 
		opened, false is closed.
		"""
		valveStatus = ctypes.c_int()
		ADRY.getPumpValve(ctypes.byref(valveStatus))
		return valveStatus.value


	def getTurbopumpFrequency():
		"""
		ATTODRY1100 ONLY. Gets the current frequency of the turbopump.
		"""
		TurbopumpFrequencyHz = ctypes.c_float()
		ADRY.getTurbopumpFrequency(ctypes.byref(TurbopumpFrequencyHz))
		return TurbopumpFrequencyHz.value


	def isExchangeHeaterOn():
		"""
		Checks to see if the exchange/vti heater is on. 'On' is defined as PID 
		control is active or a constant heater power is set. 
		"""
		ExchangeHeaterStatus = ctypes.c_int()
		ADRY.isExchangeHeaterOn(ctypes.byref(ExchangeHeaterStatus))
		return ExchangeHeaterStatus.value


	def toggleExchangeHeaterControl():
		"""
		This command only toggles the exchange/vti temperature controller. If a 
		sample temperature sensor is connected, this will be controlled, otherwise 
		the temperature of the exchange tube will be used
 		"""
		ADRY.toggleExchangeHeaterControl()


	def toggleHeliumValve():
		"""
		ATTODRY1100 ONLY. Toggles the helium valve. If it is closed, it will open 
		and if it is open, it will close.
 		"""
		ADRY.toggleHeliumValve()


	def toggleInnerVolumeValve():
		"""
		ATTODRY1100 ONLY. 
		Toggles the inner volume valve. If it is closed, it will open and if it is 
		open, it will close.
 		"""
		ADRY.toggleInnerVolumeValve()


	def toggleOuterVolumeValve():
		"""
		ATTODRY1100 ONLY. Toggles the outer volume valve. If it is closed, it will 
		open and if it is open, it will close. 
 		"""
		ADRY.toggleOuterVolumeValve()


	def togglePumpValve():
		"""
		ATTODRY1100 ONLY. Toggles the pump valve. If it is closed, it will open and 
		if it is open, it will close. 
 		"""
		ADRY.togglePumpValve()


	def getBreakVac800Valve():
		"""
		ATTODRY800 ONLY. Gets the current status of the BreakVacuum valve. 
		"""
		valveStatus = ctypes.c_int()
		ADRY.getTurbopumpFrequency(ctypes.byref(valveStatus))
		return valveStatus.value


	def toggleSampleSpace800Valve():
		"""
		ATTODRY800 ONLY. Toggles the SampleSpace valve. If it is closed, it will 
		open and if it is open, it will close.
 		"""
		ADRY.toggleSampleSpace800Valve()


	def getPump800Valve():
		"""
		ATTODRY800 ONLY. Gets the current status of the Pump valve. 
		"""
		valveStatus = ctypes.c_int()
		ADRY.getPump800Valve(ctypes.byref(valveStatus))
		return valveStatus.value


	def getSampleSpace800Valve():
		"""
		ATTODRY800 ONLY. Gets the current status of the SampleSpace valve.
		"""
		valveStatus = ctypes.c_int()
		ADRY.getSampleSpace800Valve(ctypes.byref(valveStatus))
		return valveStatus.value


	def togglePump800Valve():
		"""
		ATTODRY800 ONLY. Toggles the Pump valve. If it is closed, it will open and 
		if it is open, it will close.
 		"""
		ADRY.togglePump800Valve()


	def toggleBreakVac800Valve():
		"""
		ATTODRY800 ONLY. Toggles the BreakVacuum valve. If it is closed, it will 
		open and if it is open, it will close. 
 		"""
		ADRY.toggleBreakVac800Valve()


	def getPressure800():
		"""
		ATTODRY800 ONLY. Gets the pressure at the Cryostat Inlet.
		"""
		CryostatInPressureMbar = ctypes.c_float()
		ADRY.getPressure800(ctypes.byref(CryostatInPressureMbar))
		return CryostatInPressureMbar.value


	def GetTurbopumpFrequ800():
		"""
		ATTODRY800 ONLY. Gets the current frequency of the turbopump.
		"""
		TurbopumpFrequencyHz = ctypes.c_float()
		ADRY.GetTurbopumpFrequ800(ctypes.byref(TurbopumpFrequencyHz))
		return TurbopumpFrequencyHz.value
    
class AttoDry800:
    def __init__(self, adress):
        AttoDry.begin(2)
        AttoDry.connect(adress)
        self.set_options = []
        self.get_options = ['Field', '4K_Temp']
        
