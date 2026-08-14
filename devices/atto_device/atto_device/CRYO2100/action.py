class Action:
    def __init__(self, device):
        self.device = device
        self.interface_name = "com.attocube.cryostat.interface.action"

    def autotunePID(self, channel, tuningType):
        # type: (int, int) -> ()
        """
        Autotune heater PID

        Parameters:
            channel: Channel number
            tuningType: 0 tune P, 1 tune PI, 2 tune PID
                    
        """
        
        response = self.device.request(self.interface_name + ".autotunePID", [channel, tuningType, ])
        self.device.handleError(response)
        return                 

    def cancelCurrentCommand(self):
        # type: () -> ()
        """
        Cancels the current command
        """
        
        response = self.device.request(self.interface_name + ".cancelCurrentCommand")
        self.device.handleError(response)
        return                 

    def getCurrentCommand(self):
        # type: () -> (str)
        """
        Get current command name
        Returns:
            errorNumber: No error = 0
            current_command: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getCurrentCommand")
        self.device.handleError(response)
        return response[1]                

    def getCurrentCommandStatus(self):
        # type: () -> (str)
        """
        Get current command status
        Returns:
            errorNumber: No error = 0
            current_command: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getCurrentCommandStatus")
        self.device.handleError(response)
        return response[1]                

    def getGoToBaseRampRateSetting(self):
        # type: () -> (float)
        """
        Get sample ramp rate
        Returns:
            errorcode: 
            Rate: Ramp rate in Kelvin / minute. 0.1 - 100. 0.0 means ramp limit is off.
                    
        """
        
        response = self.device.request(self.interface_name + ".getGoToBaseRampRateSetting")
        self.device.handleError(response)
        return response[1]                

    def getSampleExchangeRampRateSetting(self):
        # type: () -> (float)
        """
        Get sample ramp rate
        Returns:
            errorcode: 
            Rate: Ramp rate in Kelvin / minute. 0.1 - 100. 0.0 means ramp limit is off.
                    
        """
        
        response = self.device.request(self.interface_name + ".getSampleExchangeRampRateSetting")
        self.device.handleError(response)
        return response[1]                

    def getWaitForEvent(self):
        # type: () -> (str)
        """
        Gets the event the cryostat waits for currently
        Returns:
            errorNumber: No error = 0
            event: event the cryostat waits for
                    
        """
        
        response = self.device.request(self.interface_name + ".getWaitForEvent")
        self.device.handleError(response)
        return response[1]                

    def goToBase(self):
        # type: () -> ()
        """
        Cool down to base temperature
        """
        
        response = self.device.request(self.interface_name + ".goToBase")
        self.device.handleError(response)
        return                 

    def goToBaseSoft(self):
        # type: () -> ()
        """
        Cool down to base temperature with fixed ramp rate
        """
        
        response = self.device.request(self.interface_name + ".goToBaseSoft")
        self.device.handleError(response)
        return                 

    def postEvent(self, eventName):
        # type: (str) -> ()
        """
        Posts the event. See: getWaitForEvent()

        Parameters:
            eventName: 
                    
        """
        
        response = self.device.request(self.interface_name + ".postEvent", [eventName, ])
        self.device.handleError(response)
        return                 

    def sampleExchange(self):
        # type: () -> ()
        """
        Start sample exchange
        """
        
        response = self.device.request(self.interface_name + ".sampleExchange")
        self.device.handleError(response)
        return                 

    def sampleExchangeSoft(self):
        # type: () -> ()
        """
        Start sample exchange with fixed ramp rate
        """
        
        response = self.device.request(self.interface_name + ".sampleExchangeSoft")
        self.device.handleError(response)
        return                 

    def setGoToBaseRampRateSetting(self, rampRate):
        # type: (float) -> ()
        """
        Set sample ramp rate

        Parameters:
            rampRate: Ramp rate in Kelvin / minute. 0.1 - 100. 0.0 means ramp limit is off.
                    
        """
        
        response = self.device.request(self.interface_name + ".setGoToBaseRampRateSetting", [rampRate, ])
        self.device.handleError(response)
        return                 

    def setSampleExchangeRampRateSetting(self, rampRate):
        # type: (float) -> ()
        """
        Set sample ramp rate

        Parameters:
            rampRate: Ramp rate in Kelvin / minute. 0.1 - 100. 0.0 means ramp limit is off.
                    
        """
        
        response = self.device.request(self.interface_name + ".setSampleExchangeRampRateSetting", [rampRate, ])
        self.device.handleError(response)
        return                 

    def shutdown(self):
        # type: () -> ()
        """
        Start shutdown
        """
        
        response = self.device.request(self.interface_name + ".shutdown")
        self.device.handleError(response)
        return                 

    def switchMagnetsOff(self):
        # type: () -> ()
        """
        Switches magnets off
        """
        
        response = self.device.request(self.interface_name + ".switchMagnetsOff")
        self.device.handleError(response)
        return                 

