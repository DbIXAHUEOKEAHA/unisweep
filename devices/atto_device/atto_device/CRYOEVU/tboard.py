class Tboard:
    def __init__(self, device):
        self.device = device
        self.interface_name = "com.attocube.cryostat.interface.tboard"

    def autotunePIDError(self):
        # type: () -> (int)
        """
        Gets last autotune error
        Returns:
            errorNumber: No error = 0
            Autotune_errorcode: 
                    
        """
        
        response = self.device.request(self.interface_name + ".autotunePIDError")
        self.device.handleError(response)
        return response[1]                

    def autotunePIDRunning(self):
        # type: () -> (bool)
        """
        Check whether PID autotune is currently running
        Returns:
            errorNumber: No error = 0
            running: 
                    
        """
        
        response = self.device.request(self.interface_name + ".autotunePIDRunning")
        self.device.handleError(response)
        return response[1]                

    def autotunePIDStage(self):
        # type: () -> (int)
        """
        Gets last autotune stage
        Returns:
            errorNumber: No error = 0
            Autotune_errorcode: 
                    
        """
        
        response = self.device.request(self.interface_name + ".autotunePIDStage")
        self.device.handleError(response)
        return response[1]                

    def downloadCalibrationCurve(self, channel):
        # type: (int) -> (str)
        """
        Gets the sensor calibration curve

        Parameters:
            channel: 
                    
        Returns:
            errorNumber: No error = 0
            calibration_data: 
                    
        """
        
        response = self.device.request(self.interface_name + ".downloadCalibrationCurve", [channel, ])
        self.device.handleError(response)
        return response[1]                

    def downloadCalibrationCurve340(self, channel):
        # type: (int) -> (str)
        """
        Gets the sensor .340 calibration curve

        Parameters:
            channel: 
                    
        Returns:
            errorNumber: No error = 0
            calibration_data: 
                    
        """
        
        response = self.device.request(self.interface_name + ".downloadCalibrationCurve340", [channel, ])
        self.device.handleError(response)
        return response[1]                

    def getHeaterPIDChannel(self, channelNumber):
        # type: (int) -> (float, float, float)
        """
        Start heating in zone mode

        Parameters:
            channelNumber: 
                    
        Returns:
            errorNumber: No error = 0
            p_output: 
            i_output: 
            d_output: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getHeaterPIDChannel", [channelNumber, ])
        self.device.handleError(response)
        return response[1], response[2], response[3]                

    def getHeaterSetpointChannel(self, channelNumber):
        # type: (int) -> (float)
        """
        Start heating in zone mode

        Parameters:
            channelNumber: 
                    
        Returns:
            errorNumber: No error = 0
            set_point: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getHeaterSetpointChannel", [channelNumber, ])
        self.device.handleError(response)
        return response[1]                

    def getHeaterZoneSettingsChannel(self, channelNumber):
        # type: (int) -> (float, float, float, float, float, int, float)
        """
        Get heater zone settings channel

        Parameters:
            channelNumber: 
                    
        Returns:
            errorNumber: No error = 0
            upperbound: Upper temperature bound of zone
            p_output: 
            i_output: 
            d_output: 
            manualOutput: 
            heatingRange: 0 -> off, 1 -> attocube OEM on, 1 -> 335, 336 Low, , 2 -> 335, 336 Medium, , 3 -> 335, 336 High
            rampRate: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getHeaterZoneSettingsChannel", [channelNumber, ])
        self.device.handleError(response)
        return response[1], response[2], response[3], response[4], response[5], response[6], response[7]                

    def getRawSensorInput(self, channelNumber):
        # type: (int) -> (float)
        """
        Get raw sensor input.

        Parameters:
            channelNumber: 
                    
        Returns:
            errorNumber: No error = 0
            Raw_sensor_input: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getRawSensorInput", [channelNumber, ])
        self.device.handleError(response)
        return response[1]                

    def getResistance(self, channelNumber):
        # type: (int) -> (float)
        """
        Gets the resistance

        Parameters:
            channelNumber: 
                    
        Returns:
            errorNumber: No error = 0
            resistance: :param channelNumber:
                    
        """
        
        response = self.device.request(self.interface_name + ".getResistance", [channelNumber, ])
        self.device.handleError(response)
        return response[1]                

    def getTemperature(self, channelNumber):
        # type: (int) -> (float)
        """
        Gets the temperature

        Parameters:
            channelNumber: 
                    
        Returns:
            errorNumber: No error = 0
            temperature: :param channelNumber:
                    
        """
        
        response = self.device.request(self.interface_name + ".getTemperature", [channelNumber, ])
        self.device.handleError(response)
        return response[1]                

    def isHeatingChannel(self, channelNumber):
        # type: (int) -> (bool)
        """
        Start heating in zone mode

        Parameters:
            channelNumber: 
                    
        Returns:
            errorNumber: No error = 0
            isHeating: 
                    
        """
        
        response = self.device.request(self.interface_name + ".isHeatingChannel", [channelNumber, ])
        self.device.handleError(response)
        return response[1]                

    def setHeaterPIDChannel(self, channelNumber, p_input, i_input, d_input):
        # type: (int, float, float, float) -> ()
        """
        Start heating in zone mode

        Parameters:
            channelNumber: 
            p_input: 
            i_input: 
            d_input: 
                    
        """
        
        response = self.device.request(self.interface_name + ".setHeaterPIDChannel", [channelNumber, p_input, i_input, d_input, ])
        self.device.handleError(response)
        return                 

    def setHeaterSetpointChannel(self, channelNumber, setpoint):
        # type: (int, float) -> ()
        """
        Start heating in zone mode

        Parameters:
            channelNumber: 
            setpoint: Temperature set point
                    
        """
        
        response = self.device.request(self.interface_name + ".setHeaterSetpointChannel", [channelNumber, setpoint, ])
        self.device.handleError(response)
        return                 

    def setHeaterZoneSettingsChannel(self, channelNumber, zone, upperbound, p_input, i_input, d_input, manualOutput, heatingRange, rampRate):
        # type: (int, int, float, float, float, float, float, int, float) -> ()
        """
        Start heating in zone mode

        Parameters:
            channelNumber: 
            zone: 
            upperbound: Upper temperature bound of zone
            p_input: 
            i_input: 
            d_input: 
            manualOutput: 
            heatingRange: 0 -> off, 1 -> attocube OEM on, 1 -> 335, 336 Low, , 2 -> 335, 336 Medium, , 3 -> 335, 336 High
            rampRate: 
                    
        """
        
        response = self.device.request(self.interface_name + ".setHeaterZoneSettingsChannel", [channelNumber, zone, upperbound, p_input, i_input, d_input, manualOutput, heatingRange, rampRate, ])
        self.device.handleError(response)
        return                 

    def startHeatingChannel(self, channelNumber):
        # type: (int) -> ()
        """
        Start heating

        Parameters:
            channelNumber: 
                    
        """
        
        response = self.device.request(self.interface_name + ".startHeatingChannel", [channelNumber, ])
        self.device.handleError(response)
        return                 

    def startHeatingOpenLoopChannel(self, channelNumber, power):
        # type: (int, float) -> ()
        """
        Start heating in zone mode

        Parameters:
            channelNumber: 
            power: 
                    
        """
        
        response = self.device.request(self.interface_name + ".startHeatingOpenLoopChannel", [channelNumber, power, ])
        self.device.handleError(response)
        return                 

    def startHeatingZoneModeChannel(self, channelNumber):
        # type: (int) -> ()
        """
        Start heating in zone mode

        Parameters:
            channelNumber: 
                    
        """
        
        response = self.device.request(self.interface_name + ".startHeatingZoneModeChannel", [channelNumber, ])
        self.device.handleError(response)
        return                 

    def stopHeatingChannel(self, channelNumber):
        # type: (int) -> ()
        """
        Stop heating

        Parameters:
            channelNumber: 
                    
        """
        
        response = self.device.request(self.interface_name + ".stopHeatingChannel", [channelNumber, ])
        self.device.handleError(response)
        return                 

    def uploadCalibrationCurve(self, channel, curveData):
        # type: (int, str) -> ()
        """
        Sets the sensor calibration curve    may time out, but the upload will still work

        Parameters:
            channel: 
            curveData: calibration data
                    
        """
        
        response = self.device.request(self.interface_name + ".uploadCalibrationCurve", [channel, curveData, ])
        self.device.handleError(response)
        return                 

    def uploadCalibrationCurve340(self, channel, curveData):
        # type: (int, str) -> ()
        """
        Sets the sensor .340 calibration curve    may time out, but the upload will still work

        Parameters:
            channel: 
            curveData: calibration data
                    
        """
        
        response = self.device.request(self.interface_name + ".uploadCalibrationCurve340", [channel, curveData, ])
        self.device.handleError(response)
        return                 

