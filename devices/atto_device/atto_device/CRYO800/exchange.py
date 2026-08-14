class Exchange:
    def __init__(self, device):
        self.device = device
        self.interface_name = "com.attocube.cryostat.interface.exchange"

    def downloadCalibrationCurve(self):
        # type: () -> (str)
        """
        Gets the exchange sensor calibration curve
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
        Gets the exchange sensor .340 calibration curve
        Returns:
            errorNumber: No error = 0
            calibration_data: 
                    
        """
        
        response = self.device.request(self.interface_name + ".downloadCalibrationCurve340")
        self.device.handleError(response)
        return response[1]                

    def getHeaterAllZoneRampRates(self):
        # type: () -> (float)
        """
        Get exchange heater all zones ramp rate
        Returns:
            errorcode: Error code
            rampRate: Ramp rate for this zone 0.1 100 K/min
                    
        """
        
        response = self.device.request(self.interface_name + ".getHeaterAllZoneRampRates")
        self.device.handleError(response)
        return response[1]                

    def getHeaterDefaultZoneSettings(self, zone):
        # type: (int) -> (float, float, float, float, float, int, float)
        """
        Get exchange heater zone settings

        Parameters:
            zone: Zone number
                    
        Returns:
            errorcode: Error code
            upperbound: Upper Setpoint boundary of this zone in kelvin
            P: P
            I: I
            D: D
            manualOutput: Manual output for this zone 0 to 100%
            heatingRange: Heating range see class HeaterRanges and Lake Shore 336 manual for ZONE command
            rampRate: Ramp rate for this zone 0.1 100 K/min
                    
        """
        
        response = self.device.request(self.interface_name + ".getHeaterDefaultZoneSettings", [zone, ])
        self.device.handleError(response)
        return response[1], response[2], response[3], response[4], response[5], response[6], response[7]                

    def getHeaterHeatingMode(self):
        # type: () -> (int)
        """
        Gets the exchange heater heating mode
        Returns:
            errorNumber: No error = 0
            mode: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getHeaterHeatingMode")
        self.device.handleError(response)
        return response[1]                

    def getHeaterNumberOfDefaultZones(self):
        # type: () -> (int)
        """
        Get the number of the exchange heater default zones
        Returns:
            errorcode: Error code
            number_of_zones: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getHeaterNumberOfDefaultZones")
        self.device.handleError(response)
        return response[1]                

    def getHeaterNumberOfZones(self):
        # type: () -> (int)
        """
        Get the number of the exchange heater zones
        Returns:
            errorcode: Error code
            number_of_zones: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getHeaterNumberOfZones")
        self.device.handleError(response)
        return response[1]                

    def getHeaterPower(self):
        # type: () -> (float)
        """
        Gets the exchange heater power
        Returns:
            errorNumber: No error = 0
            power: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getHeaterPower")
        self.device.handleError(response)
        return response[1]                

    def getHeaterRes(self):
        # type: () -> (float)
        """
        Gets the exchange heater resistance
        Returns:
            errorNumber: No error = 0
            resistance: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getHeaterRes")
        self.device.handleError(response)
        return response[1]                

    def getHeaterStatus(self):
        # type: () -> ()
        """
        Gets the exchange heater status
        """
        
        response = self.device.request(self.interface_name + ".getHeaterStatus")
        self.device.handleError(response)
        return                 

    def getHeaterZoneSettings(self, zone):
        # type: (int) -> (float, float, float, float, float, int, float)
        """
        Get exchange heater zone settings

        Parameters:
            zone: Zone number
                    
        Returns:
            errorcode: Error code
            upperbound: Upper Setpoint boundary of this zone in kelvin
            P: P
            I: I
            D: D
            manualOutput: Manual output for this zone 0 to 100%
            heatingRange: Heating range see class HeaterRanges and Lake Shore 336 manual for ZONE command
            rampRate: Ramp rate for this zone 0.1 100 K/min
                    
        """
        
        response = self.device.request(self.interface_name + ".getHeaterZoneSettings", [zone, ])
        self.device.handleError(response)
        return response[1], response[2], response[3], response[4], response[5], response[6], response[7]                

    def getInputFilterSettings(self):
        # type: () -> (bool, int, int)
        """
        Gets the exchange input filter settings
        Returns:
            errorNumber: No error = 0
            off_or_on: 
            point: 
            window: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getInputFilterSettings")
        self.device.handleError(response)
        return response[1], response[2], response[3]                

    def getMaxPower(self):
        # type: () -> (float)
        """
        Gets the exchange heater maximum power
        Returns:
            errorNumber: No error = 0
            maxPower: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getMaxPower")
        self.device.handleError(response)
        return response[1]                

    def getResistance(self):
        # type: () -> (float)
        """
        Gets the exchange temperature resistance
        Returns:
            errorNumber: No error = 0
            exchange_resistance: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getResistance")
        self.device.handleError(response)
        return response[1]                

    def getSetPoint(self):
        # type: () -> (float)
        """
        Gets the exchange set point
        Returns:
            errorNumber: No error = 0
            set_point: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getSetPoint")
        self.device.handleError(response)
        return response[1]                

    def getTempControlStatus(self):
        # type: () -> (bool)
        """
        Gets the exchange heater status
        Returns:
            errorNumber: No error = 0
            Status: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getTempControlStatus")
        self.device.handleError(response)
        return response[1]                

    def getTemperature(self):
        # type: () -> (float)
        """
        Gets the exchange temperature
        Returns:
            errorNumber: No error = 0
            exchange_temperature: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getTemperature")
        self.device.handleError(response)
        return response[1]                

    def setHeaterAllZoneRampRates(self, rampRate):
        # type: (float) -> ()
        """
        Set exchange heater all zones ramp rate

        Parameters:
            rampRate: Ramp rate for this zone 0.1 100 K/min
                    
        """
        
        response = self.device.request(self.interface_name + ".setHeaterAllZoneRampRates", [rampRate, ])
        self.device.handleError(response)
        return                 

    def setHeaterPower(self, value):
        # type: (float) -> ()
        """
        Sets the exchange heater power

        Parameters:
            value: 
                    
        """
        
        response = self.device.request(self.interface_name + ".setHeaterPower", [value, ])
        self.device.handleError(response)
        return                 

    def setHeaterZoneSettings(self, zone, upperbound, P, I, D, manualOutput, heatingRange):
        # type: (int, float, float, float, float, float, int) -> ()
        """
        Set exchange heater zone settings

        Parameters:
            zone: Zone number
            upperbound: Upper Setpoint boundary of this zone in kelvin
            P: P
            I: I
            D: D
            manualOutput: Manual output for this zone 0 to 100%
            heatingRange: Heating range see class HeaterRanges and Lake Shore 336 manual for ZONE command
                    
        """
        
        response = self.device.request(self.interface_name + ".setHeaterZoneSettings", [zone, upperbound, P, I, D, manualOutput, heatingRange, ])
        self.device.handleError(response)
        return                 

    def setInputFilterSettings(self, filterOn, numberOfPoints, windowSize):
        # type: (bool, int, int) -> ()
        """
        Sets the exchange input filter settings

        Parameters:
            filterOn: 
            numberOfPoints: 
            windowSize: 
                    
        """
        
        response = self.device.request(self.interface_name + ".setInputFilterSettings", [filterOn, numberOfPoints, windowSize, ])
        self.device.handleError(response)
        return                 

    def setSetPoint(self, setPoint):
        # type: (float) -> ()
        """
        Sets the exchange set point

        Parameters:
            setPoint: 
                    
        """
        
        response = self.device.request(self.interface_name + ".setSetPoint", [setPoint, ])
        self.device.handleError(response)
        return                 

    def startHeaterOpenLoopPower(self):
        # type: () -> ()
        """
        Starts the exchange heater in open loop mode with the previously set power
        """
        
        response = self.device.request(self.interface_name + ".startHeaterOpenLoopPower")
        self.device.handleError(response)
        return                 

    def startHeaterZoneMode(self):
        # type: () -> ()
        """
        Starts the exchange heater in zone mode
        """
        
        response = self.device.request(self.interface_name + ".startHeaterZoneMode")
        self.device.handleError(response)
        return                 

    def startTempControl(self):
        # type: () -> ()
        """
        Starts the exchange heater
        """
        
        response = self.device.request(self.interface_name + ".startTempControl")
        self.device.handleError(response)
        return                 

    def stopTempControl(self):
        # type: () -> ()
        """
        Stops the exchange heater
        """
        
        response = self.device.request(self.interface_name + ".stopTempControl")
        self.device.handleError(response)
        return                 

    def uploadCalibrationCurve(self, calibrationData):
        # type: (str) -> ()
        """
        Sets the exchange sensor calibration curve    May time out, but the upload will still work

        Parameters:
            calibrationData: 
                    
        """
        
        response = self.device.request(self.interface_name + ".uploadCalibrationCurve", [calibrationData, ])
        self.device.handleError(response)
        return                 

    def uploadCalibrationCurve340(self, calibrationData):
        # type: (str) -> ()
        """
        Sets the exchange sensor .340 calibration curve    May time out, but the upload will still work

        Parameters:
            calibrationData: 
                    
        """
        
        response = self.device.request(self.interface_name + ".uploadCalibrationCurve340", [calibrationData, ])
        self.device.handleError(response)
        return                 

