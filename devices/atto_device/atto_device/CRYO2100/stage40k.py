class Stage40k:
    def __init__(self, device):
        self.device = device
        self.interface_name = "com.attocube.cryostat.interface.stage40k"

    def downloadCalibrationCurve(self):
        # type: () -> (str)
        """
        Gets the Stage40K sensor calibration curve
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
        Gets the Stage40K sensor .340 calibration curve
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
        Get Stage40K heater all zones ramp rate
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
        Get Stage40K heater zone settings

        Parameters:
            zone: Zone number
                    
        Returns:
            errorcode: Error code
            upperbound: Upper set point boundary of this zone in kelvin
            P: 
            I: 
            D: 
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
        Gets the Stage40K heater heating mode
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
        Get the number of the Stage40K heater default zones
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
        Get the number of the Stage40K heater zones
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
        Gets the Stage40K heater power
        Returns:
            errorNumber: No error = 0
            power: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getHeaterPower")
        self.device.handleError(response)
        return response[1]                

    def getHeaterRampData(self):
        # type: () -> (bool, float)
        """
        Get Stage40K heater ramp data
        Returns:
            errorcode: 
            OnOff: Ramp is on or off
            Rate: Ramp rate in Kelvin / minute. 0.1 - 100. 0.0 means ramp limit is off.
                    
        """
        
        response = self.device.request(self.interface_name + ".getHeaterRampData")
        self.device.handleError(response)
        return response[1], response[2]                

    def getHeaterRes(self):
        # type: () -> (float)
        """
        Gets the Stage40K heater resistance
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
        Gets the Stage40K heater status
        """
        
        response = self.device.request(self.interface_name + ".getHeaterStatus")
        self.device.handleError(response)
        return                 

    def getHeaterWireRes(self):
        # type: () -> (float)
        """
        Gets the Stage40K heater wire resistance
        Returns:
            errorNumber: No error = 0
            wire_resistance: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getHeaterWireRes")
        self.device.handleError(response)
        return response[1]                

    def getHeaterZoneSettings(self, zone):
        # type: (int) -> (float, float, float, float, float, int, float)
        """
        Get Stage40K heater zone settings

        Parameters:
            zone: Zone number
                    
        Returns:
            errorcode: Error code
            upperbound: Upper set point boundary of this zone in kelvin
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
        Gets the Stage40K input filter settings
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
        Gets the Stage40K heater maximum power
        Returns:
            errorNumber: No error = 0
            maxPower: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getMaxPower")
        self.device.handleError(response)
        return response[1]                

    def getPID(self):
        # type: () -> (float, float, float)
        """
        Gets the Stage40K heater PID values
        Returns:
            errorNumber: No error = 0
            proportional: 
            integral: 
            derivative: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getPID")
        self.device.handleError(response)
        return response[1], response[2], response[3]                

    def getRampControlStatus(self):
        # type: () -> (bool)
        """
        Get Stage40K heater ramp control status
        Returns:
            errorcode: 
            OnOff: Ramp is on or off
                    
        """
        
        response = self.device.request(self.interface_name + ".getRampControlStatus")
        self.device.handleError(response)
        return response[1]                

    def getRampRate(self):
        # type: () -> (float)
        """
        Get Stage40K ramp rate
        Returns:
            errorcode: 
            Rate: Ramp rate in Kelvin / minute. 0.1 - 100. 0.0 means ramp limit is off.
                    
        """
        
        response = self.device.request(self.interface_name + ".getRampRate")
        self.device.handleError(response)
        return response[1]                

    def getResistance(self):
        # type: () -> (float)
        """
        Gets the Stage40K resistance
        Returns:
            errorNumber: No error = 0
            Stage40K_resistance: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getResistance")
        self.device.handleError(response)
        return response[1]                

    def getSetPoint(self):
        # type: () -> (float)
        """
        Gets the Stage40K set point
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
        Gets the Stage40K heater status
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
        Gets the Stage40K temperature
        Returns:
            errorNumber: No error = 0
            Stage40K_temperature: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getTemperature")
        self.device.handleError(response)
        return response[1]                

    def heaterRampOff(self):
        # type: () -> ()
        """
        Set Stage40K heater ramp off
        """
        
        response = self.device.request(self.interface_name + ".heaterRampOff")
        self.device.handleError(response)
        return                 

    def heaterRampOn(self, rate):
        # type: (float) -> ()
        """
        Set Stage40K heater ramp on

        Parameters:
            rate: Ramp rate in Kelvin / minute 0.1 - 100
                    
        """
        
        response = self.device.request(self.interface_name + ".heaterRampOn", [rate, ])
        self.device.handleError(response)
        return                 

    def setD(self, value):
        # type: (float) -> ()
        """
        Sets the Stage40K heater D value

        Parameters:
            value: 
                    
        """
        
        response = self.device.request(self.interface_name + ".setD", [value, ])
        self.device.handleError(response)
        return                 

    def setHeaterAllZoneRampRates(self, rampRate):
        # type: (float) -> ()
        """
        Set Stage40K heater all zones ramp rate

        Parameters:
            rampRate: Ramp rate for this zone 0.1 100 K/min
                    
        """
        
        response = self.device.request(self.interface_name + ".setHeaterAllZoneRampRates", [rampRate, ])
        self.device.handleError(response)
        return                 

    def setHeaterPower(self, value):
        # type: (float) -> ()
        """
        Sets the Stage40K heater power

        Parameters:
            value: 
                    
        """
        
        response = self.device.request(self.interface_name + ".setHeaterPower", [value, ])
        self.device.handleError(response)
        return                 

    def setHeaterRes(self, value):
        # type: (float) -> ()
        """
        Sets the Stage40K heater resistance

        Parameters:
            value: 
                    
        """
        
        response = self.device.request(self.interface_name + ".setHeaterRes", [value, ])
        self.device.handleError(response)
        return                 

    def setHeaterWireRes(self, value):
        # type: (float) -> ()
        """
        Sets the Stage40K heater wire resistance

        Parameters:
            value: 
                    
        """
        
        response = self.device.request(self.interface_name + ".setHeaterWireRes", [value, ])
        self.device.handleError(response)
        return                 

    def setHeaterZoneSettings(self, zone, upperbound, p_input, i_input, d_input, manualOutput, heatingRange):
        # type: (int, float, float, float, float, float, int) -> ()
        """
        Set Stage40K heater zone settings

        Parameters:
            zone: Zone number
            upperbound: Upper set point boundary of this zone in kelvin
            p_input: 
            i_input: 
            d_input: 
            manualOutput: Manual output for this zone 0 to 100%
            heatingRange: Heating range see class HeaterRanges and Lake Shore 336 manual for ZONE command
                    
        """
        
        response = self.device.request(self.interface_name + ".setHeaterZoneSettings", [zone, upperbound, p_input, i_input, d_input, manualOutput, heatingRange, ])
        self.device.handleError(response)
        return                 

    def setI(self, value):
        # type: (float) -> ()
        """
        Sets the Stage40K heater I value

        Parameters:
            value: 
                    
        """
        
        response = self.device.request(self.interface_name + ".setI", [value, ])
        self.device.handleError(response)
        return                 

    def setInputFilterSettings(self, filterOn, numberOfPoints, windowSize):
        # type: (bool, int, int) -> ()
        """
        Sets the Stage40K input filter settings

        Parameters:
            filterOn: 
            numberOfPoints: 
            windowSize: 
                    
        """
        
        response = self.device.request(self.interface_name + ".setInputFilterSettings", [filterOn, numberOfPoints, windowSize, ])
        self.device.handleError(response)
        return                 

    def setMaxPower(self, value):
        # type: (float) -> ()
        """
        Sets the Stage40K heater maximum power

        Parameters:
            value: 
                    
        """
        
        response = self.device.request(self.interface_name + ".setMaxPower", [value, ])
        self.device.handleError(response)
        return                 

    def setP(self, value):
        # type: (float) -> ()
        """
        Sets the Stage40K heater P value

        Parameters:
            value: 
                    
        """
        
        response = self.device.request(self.interface_name + ".setP", [value, ])
        self.device.handleError(response)
        return                 

    def setPID(self, proportional, integral, derivative):
        # type: (float, float, float) -> ()
        """
        Sets the Stage40K heater PID values

        Parameters:
            proportional: 
            integral: 
            derivative: 
                    
        """
        
        response = self.device.request(self.interface_name + ".setPID", [proportional, integral, derivative, ])
        self.device.handleError(response)
        return                 

    def setRampRate(self, rate):
        # type: (float) -> ()
        """
        Set Stage40K ramp rate

        Parameters:
            rate: Ramp rate in Kelvin / minute. 0.1 - 100. 0.0 means ramp limit is off.
                    
        """
        
        response = self.device.request(self.interface_name + ".setRampRate", [rate, ])
        self.device.handleError(response)
        return                 

    def setSetPoint(self, setPoint):
        # type: (float) -> ()
        """
        Sets the Stage40K set point

        Parameters:
            setPoint: 
                    
        """
        
        response = self.device.request(self.interface_name + ".setSetPoint", [setPoint, ])
        self.device.handleError(response)
        return                 

    def startHeaterOpenLoopPower(self):
        # type: () -> ()
        """
        Starts the Stage40K heater in open loop mode with the previously set power
        """
        
        response = self.device.request(self.interface_name + ".startHeaterOpenLoopPower")
        self.device.handleError(response)
        return                 

    def startHeaterZoneMode(self):
        # type: () -> ()
        """
        Starts the Stage40K heater in zone mode
        """
        
        response = self.device.request(self.interface_name + ".startHeaterZoneMode")
        self.device.handleError(response)
        return                 

    def startRampControl(self):
        # type: () -> ()
        """
        Set Stage40K heater ramp control on
        """
        
        response = self.device.request(self.interface_name + ".startRampControl")
        self.device.handleError(response)
        return                 

    def startTempControl(self):
        # type: () -> ()
        """
        Starts the Stage40K heater
        """
        
        response = self.device.request(self.interface_name + ".startTempControl")
        self.device.handleError(response)
        return                 

    def stopRampControl(self):
        # type: () -> ()
        """
        Set Stage40K heater ramp control off (same as heaterRampOff())
        """
        
        response = self.device.request(self.interface_name + ".stopRampControl")
        self.device.handleError(response)
        return                 

    def stopTempControl(self):
        # type: () -> ()
        """
        Stops the Stage40K heater
        """
        
        response = self.device.request(self.interface_name + ".stopTempControl")
        self.device.handleError(response)
        return                 

    def uploadCalibrationCurve(self, calibrationData):
        # type: (str) -> ()
        """
        Sets the Stage40K sensor calibration curve    may time out, but the upload will still work

        Parameters:
            calibrationData: 
                    
        """
        
        response = self.device.request(self.interface_name + ".uploadCalibrationCurve", [calibrationData, ])
        self.device.handleError(response)
        return                 

    def uploadCalibrationCurve340(self, calibrationData):
        # type: (str) -> ()
        """
        Sets the Stage40K sensor .340 calibration curve    may time out, but the upload will still work

        Parameters:
            calibrationData: 
                    
        """
        
        response = self.device.request(self.interface_name + ".uploadCalibrationCurve340", [calibrationData, ])
        self.device.handleError(response)
        return                 

