class Heater:
    def __init__(self, device):
        self.device = device
        self.interface_name = "com.attocube.cryostat.interface.heater"

    def getHeaterPower(self, channelNumber):
        # type: (int) -> (float)
        """
        Gets the heater power

        Parameters:
            channelNumber: 
                    
        Returns:
            errorNumber: No error = 0
            heater_power: :param channelNumber:
                    
        """
        
        response = self.device.request(self.interface_name + ".getHeaterPower", [channelNumber, ])
        self.device.handleError(response)
        return response[1]                

    def initializeHeater(self, channelNumber):
        # type: (int) -> ()
        """
        Initialized the heater

        Parameters:
            channelNumber: 
                    
        """
        
        response = self.device.request(self.interface_name + ".initializeHeater", [channelNumber, ])
        self.device.handleError(response)
        return                 

    def startHeaterOpenLoopPower(self, channelNumber, power):
        # type: (int, float) -> ()
        """
        Starts the heater in open loop mode with fixed power

        Parameters:
            channelNumber: 
            power: 
                    
        """
        
        response = self.device.request(self.interface_name + ".startHeaterOpenLoopPower", [channelNumber, power, ])
        self.device.handleError(response)
        return                 

    def stopHeater(self, channelNumber):
        # type: (int) -> ()
        """
        Stops the heater

        Parameters:
            channelNumber: 
                    
        """
        
        response = self.device.request(self.interface_name + ".stopHeater", [channelNumber, ])
        self.device.handleError(response)
        return                 

