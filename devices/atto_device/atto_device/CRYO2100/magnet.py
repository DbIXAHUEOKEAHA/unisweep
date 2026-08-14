class Magnet:
    def __init__(self, device):
        self.device = device
        self.interface_name = "com.attocube.cryostat.interface.magnet"

    def downloadCalibrationCurve(self):
        # type: () -> (str)
        """
        Gets the magnet sensor calibration curve
        Returns:
            errorNumber: No error = 0
            calibration_data: 
                    
        """
        
        response = self.device.request(self.interface_name + ".downloadCalibrationCurve")
        self.device.handleError(response)
        return response[1]                

    def downloadCalibrationCurve340(self):
        # type: () -> (str)
        """
        Gets the magnet sensor .340 calibration curve
        Returns:
            errorNumber: No error = 0
            calibration_data: 
                    
        """
        
        response = self.device.request(self.interface_name + ".downloadCalibrationCurve340")
        self.device.handleError(response)
        return response[1]                

    def getDefaultRampRate(self, index, channel):
        # type: (int, int) -> (float, float)
        """
        Get the factory defaults for the Ramp Rates

        Parameters:
            index: 
            channel: 
                    
        Returns:
            errorNumber: No error = 0
            range: 
            rate: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getDefaultRampRate", [index, channel, ])
        self.device.handleError(response)
        return response[1], response[2]                

    def getDrivenMode(self, channel):
        # type: (int) -> (bool)
        """
        Checks if Magnet is in driven Mode (equivalent to NOT getPersistentMode)

        Parameters:
            channel: 
                    
        Returns:
            errorNumber: No error = 0
            drivenMode_on_or_off: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getDrivenMode", [channel, ])
        self.device.handleError(response)
        return response[1]                

    def getFieldControl(self, channel):
        # type: (int) -> (bool)
        """
        Get whether the magnetic field is being controlled

        Parameters:
            channel: 
                    
        Returns:
            errorNumber: No error = 0
            field_control_status: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getFieldControl", [channel, ])
        self.device.handleError(response)
        return response[1]                

    def getFieldsInLeads(self, channel):
        # type: (int) -> (float)
        """
        Gets the current in the Leads but in Field units

        Parameters:
            channel: 
                    
        Returns:
            errorNumber: No error = 0
            field: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getFieldsInLeads", [channel, ])
        self.device.handleError(response)
        return response[1]                

    def getH(self, channel):
        # type: (int) -> (float)
        """
        Gets the magnetic field

        Parameters:
            channel: 
                    
        Returns:
            errorNumber: No error = 0
            field: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getH", [channel, ])
        self.device.handleError(response)
        return response[1]                

    def getHSetPoint(self, channel):
        # type: (int) -> (float)
        """
        Gets the magnetic field set point

        Parameters:
            channel: 
                    
        Returns:
            errorNumber: No error = 0
            setPoint: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getHSetPoint", [channel, ])
        self.device.handleError(response)
        return response[1]                

    def getHSetPoint3D(self):
        # type: () -> (float, float, float)
        """
        Gets the magnetic field set points
        Returns:
            errorNumber: No error = 0
            setPointZ: 
            setPointY: 
            setPointX: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getHSetPoint3D")
        self.device.handleError(response)
        return response[1], response[2], response[3]                

    def getHState(self, channel):
        # type: (int) -> (str)
        """
        Gets the magnetic field state for a channel

        Parameters:
            channel: 
                    
        Returns:
            errorNumber: No error = 0
            state: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getHState", [channel, ])
        self.device.handleError(response)
        return response[1]                

    def getInputFilterSettings(self):
        # type: () -> (bool, int, int)
        """
        Gets the magnet input filter settings
        Returns:
            errorNumber: No error = 0
            off_or_on: 
            point: 
            window: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getInputFilterSettings")
        self.device.handleError(response)
        return response[1], response[2], response[3]                

    def getIsInQuenchState(self):
        # type: () -> (bool)
        """
        Whether the cryo is currently in quench state
        Returns:
            errorNumber: No error = 0
            state: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getIsInQuenchState")
        self.device.handleError(response)
        return response[1]                

    def getLeadsHot(self):
        # type: () -> (bool)
        """
        Checks if current is running in the PS Leads
        Returns:
            errorNumber: No error = 0
            onOrOff: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getLeadsHot")
        self.device.handleError(response)
        return response[1]                

    def getMagnetChannelName(self, channel):
        # type: (int) -> (str)
        """
        Gets the Name of magnets

        Parameters:
            channel: 
                    
        Returns:
            errorNumber: No error = 0
            name: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getMagnetChannelName", [channel, ])
        self.device.handleError(response)
        return response[1]                

    def getNumDefaultRampRates(self, channel):
        # type: (int) -> (int)
        """
        Gets the number of default RampRates

        Parameters:
            channel: 
                    
        Returns:
            errorNumber: 
            NumberOfRates: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getNumDefaultRampRates", [channel, ])
        self.device.handleError(response)
        return response[1]                

    def getNumRampRates(self, channel):
        # type: (int) -> (int)
        """
        Return the number of RampRates

        Parameters:
            channel: 
                    
        Returns:
            errorNumber: 
            num: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getNumRampRates", [channel, ])
        self.device.handleError(response)
        return response[1]                

    def getNumberOfMagnetChannels(self):
        # type: () -> (int)
        """
        Gets the number of magnets
        Returns:
            errorNumber: No error = 0
            channels: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getNumberOfMagnetChannels")
        self.device.handleError(response)
        return response[1]                

    def getPause3D(self):
        # type: () -> (bool)
        """
        Checks if at least one of the power supply channels is paused
        Returns:
            errorNumber: No error = 0
            paused: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getPause3D")
        self.device.handleError(response)
        return response[1]                

    def getPersistentMode(self, channel):
        # type: (int) -> (bool)
        """
        Checks if Magnet is in persistent mode (equivalent to NOT getDrivenMode)

        Parameters:
            channel: 
                    
        Returns:
            errorNumber: No error = 0
            drivenMode_on_or_off: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getPersistentMode", [channel, ])
        self.device.handleError(response)
        return response[1]                

    def getPersistentMode3D(self):
        # type: () -> (bool)
        """
        Gets combined persistent mode
        Returns:
            errorNumber: No error = 0
            present: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getPersistentMode3D")
        self.device.handleError(response)
        return response[1]                

    def getPersistentSwitchHeaterStatus(self, channel):
        # type: (int) -> (bool)
        """
        Gets the state of the Persistent Heater

        Parameters:
            channel: 
                    
        Returns:
            errorNumber: No error = 0
            state: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getPersistentSwitchHeaterStatus", [channel, ])
        self.device.handleError(response)
        return response[1]                

    def getPersistentSwitchPresent(self, channel):
        # type: (int) -> (bool)
        """
        Gets whether the persistent switch option is present for a channel

        Parameters:
            channel: 
                    
        Returns:
            errorNumber: No error = 0
            present: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getPersistentSwitchPresent", [channel, ])
        self.device.handleError(response)
        return response[1]                

    def getRampRate(self, channel, index):
        # type: (int, int) -> (float, float)
        """
        Get ramp rate at index for channel

        Parameters:
            channel: 
            index: 
                    
        Returns:
            errorNumber: No error = 0
            range: 
            rate: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getRampRate", [channel, index, ])
        self.device.handleError(response)
        return response[1], response[2]                

    def getResistance(self):
        # type: () -> (float)
        """
        Gets the magnet temperature resistance. There is only one for all magnets
        Returns:
            errorNumber: No error = 0
            resistance: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getResistance")
        self.device.handleError(response)
        return response[1]                

    def getTemperature(self):
        # type: () -> (float)
        """
        Gets the magnet temperature. There is only one for all magnets
        Returns:
            errorNumber: No error = 0
            temperature: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getTemperature")
        self.device.handleError(response)
        return response[1]                

    def getVolt(self, channel):
        # type: (int) -> (float)
        """
        Gets the magnetic field voltage

        Parameters:
            channel: 
                    
        Returns:
            errorNumber: No error = 0
            field: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getVolt", [channel, ])
        self.device.handleError(response)
        return response[1]                

    def resetQuenchState(self):
        # type: () -> ()
        """
        Let's reset the quench event
        """
        
        response = self.device.request(self.interface_name + ".resetQuenchState")
        self.device.handleError(response)
        return                 

    def setDrivenMode(self, channel, onOrOff):
        # type: (int, bool) -> ()
        """
        Set driven mode for a specific channel

        Parameters:
            channel: 
            onOrOff: drivenMode on or off
                    
        """
        
        response = self.device.request(self.interface_name + ".setDrivenMode", [channel, onOrOff, ])
        self.device.handleError(response)
        return                 

    def setHSetPoint(self, channel, setPoint):
        # type: (int, float) -> ()
        """
        Sets the magnetic field set point

        Parameters:
            channel: 
            setPoint: 
                    
        """
        
        response = self.device.request(self.interface_name + ".setHSetPoint", [channel, setPoint, ])
        self.device.handleError(response)
        return                 

    def setHSetPoint3D(self, setPointZ, setPointY, setPointX):
        # type: (float, float, float) -> ()
        """
        Sets the magnetic field set points

        Parameters:
            setPointZ: 
            setPointY: 
            setPointX: 
                    
        """
        
        response = self.device.request(self.interface_name + ".setHSetPoint3D", [setPointZ, setPointY, setPointX, ])
        self.device.handleError(response)
        return                 

    def setInputFilterSettings(self, filterOn, numberOfPoints, windowSize):
        # type: (bool, int, int) -> ()
        """
        Sets the magnet input filter settings

        Parameters:
            filterOn: 
            numberOfPoints: 
            windowSize: 
                    
        """
        
        response = self.device.request(self.interface_name + ".setInputFilterSettings", [filterOn, numberOfPoints, windowSize, ])
        self.device.handleError(response)
        return                 

    def setPause3D(self, onOff):
        # type: (bool) -> ()
        """
        Sets the pause state of the power supply channels

        Parameters:
            onOff: 
                    
        """
        
        response = self.device.request(self.interface_name + ".setPause3D", [onOff, ])
        self.device.handleError(response)
        return                 

    def setPersistentMode3D(self, onOff):
        # type: (bool) -> ()
        """
        Sets the combined persistent mode

        Parameters:
            onOff: 
                    
        """
        
        response = self.device.request(self.interface_name + ".setPersistentMode3D", [onOff, ])
        self.device.handleError(response)
        return                 

    def setRampRate(self, channel, index, range_this, rate):
        # type: (int, int, float, float) -> ()
        """
        Change the ramp rates

        Parameters:
            channel: 
            index: 
            range_this: 
            rate: 
                    
        """
        
        response = self.device.request(self.interface_name + ".setRampRate", [channel, index, range_this, rate, ])
        self.device.handleError(response)
        return                 

    def startFieldControl(self, channel):
        # type: (int) -> ()
        """
        Starts the magnetic field control

        Parameters:
            channel: 
                    
        """
        
        response = self.device.request(self.interface_name + ".startFieldControl", [channel, ])
        self.device.handleError(response)
        return                 

    def stopFieldControl(self, channel):
        # type: (int) -> ()
        """
        Stops the magnetic field control

        Parameters:
            channel: 
                    
        """
        
        response = self.device.request(self.interface_name + ".stopFieldControl", [channel, ])
        self.device.handleError(response)
        return                 

    def uploadCalibrationCurve(self, calibrationData):
        # type: (str) -> ()
        """
        Sets the magnet sensor calibration curve    may time out, but the upload will still work

        Parameters:
            calibrationData: 
                    
        """
        
        response = self.device.request(self.interface_name + ".uploadCalibrationCurve", [calibrationData, ])
        self.device.handleError(response)
        return                 

    def uploadCalibrationCurve340(self, calibrationData):
        # type: (str) -> ()
        """
        Sets the magnet sensor .340 calibration curve    may time out, but the upload will still work

        Parameters:
            calibrationData: 
                    
        """
        
        response = self.device.request(self.interface_name + ".uploadCalibrationCurve340", [calibrationData, ])
        self.device.handleError(response)
        return                 

