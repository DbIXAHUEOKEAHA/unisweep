class Turbopump:
    def __init__(self, device):
        self.device = device
        self.interface_name = "com.attocube.cryostat.interface.turboPump"

    def getFrequency(self):
        # type: () -> (float)
        """
        Gets the turbo pump frequency
        Returns:
            errorNumber: No error = 0
            turbo_pump_frequency: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getFrequency")
        self.device.handleError(response)
        return response[1]                

    def getStatus(self):
        # type: () -> (bool)
        """
        Gets the turbo pump status
        Returns:
            errorNumber: No error = 0
            turbo_pump_status: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getStatus")
        self.device.handleError(response)
        return response[1]                

    def getStatusString(self):
        # type: () -> (str)
        """
        Gets the turbo pump status as string
        Returns:
            errorNumber: No error = 0
            turbo_pump_status_string: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getStatusString")
        self.device.handleError(response)
        return response[1]                

    def start(self):
        # type: () -> ()
        """
        Starts the turbo pump
        """
        
        response = self.device.request(self.interface_name + ".start")
        self.device.handleError(response)
        return                 

    def stop(self):
        # type: () -> ()
        """
        Stops the turbo pump
        """
        
        response = self.device.request(self.interface_name + ".stop")
        self.device.handleError(response)
        return                 

