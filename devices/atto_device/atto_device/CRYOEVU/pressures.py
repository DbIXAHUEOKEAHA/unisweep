class Pressures:
    def __init__(self, device):
        self.device = device
        self.interface_name = "com.attocube.cryostat.interface.pressures"

    def getGaugeType(self, gaugeNumber):
        # type: (int) -> (str)
        """
        Gets the gauge type

        Parameters:
            gaugeNumber: 0..5
                    
        Returns:
            errorNumber: No error = 0
            type: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getGaugeType", [gaugeNumber, ])
        self.device.handleError(response)
        return response[1]                

    def getPressureAndVoltage(self, gaugeNumber):
        # type: (int) -> (float, float)
        """
        Gets the cryostat in pressure

        Parameters:
            gaugeNumber: 0..5
                    
        Returns:
            errorNumber: No error = 0
            pressure: 
            voltage: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getPressureAndVoltage", [gaugeNumber, ])
        self.device.handleError(response)
        return response[1], response[2]                

    def getPressureVoltage(self, gaugeNumber):
        # type: (int) -> (float)
        """
        Gets the voltage on that would be a pressure gauge

        Parameters:
            gaugeNumber: 0..5
                    
        Returns:
            errorNumber: No error = 0
            pressure_voltage: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getPressureVoltage", [gaugeNumber, ])
        self.device.handleError(response)
        return response[1]                

    def setGaugeType(self, gaugeNumber, newType):
        # type: (int, str) -> ()
        """
        Sets the gauge type

        Parameters:
            gaugeNumber: 0..5
            newType: 
                    
        """
        
        response = self.device.request(self.interface_name + ".setGaugeType", [gaugeNumber, newType, ])
        self.device.handleError(response)
        return                 

