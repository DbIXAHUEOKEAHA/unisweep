class Scrollpump:
    def __init__(self, device):
        self.device = device
        self.interface_name = "com.attocube.cryostat.interface.scrollPump"

    def getFrequency(self):
        # type: () -> (float)
        """
        Gets the scroll pump frequency
        Returns:
            errorNumber: No error = 0
            scroll_pump_frequency: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getFrequency")
        self.device.handleError(response)
        return response[1]                

    def getStatus(self):
        # type: () -> (bool)
        """
        Gets the scroll pump status
        Returns:
            errorNumber: No error = 0
            scroll_pump_status: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getStatus")
        self.device.handleError(response)
        return response[1]                

    def getStatusString(self):
        # type: () -> (str)
        """
        Gets the scroll pump status as string
        Returns:
            errorNumber: No error = 0
            scroll_pump_status_string: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getStatusString")
        self.device.handleError(response)
        return response[1]                

    def startFullSpeed(self):
        # type: () -> ()
        """
        Starts the scroll pump at full speed
        """
        
        response = self.device.request(self.interface_name + ".startFullSpeed")
        self.device.handleError(response)
        return                 

    def startStandbySpeed(self):
        # type: () -> ()
        """
        Starts the scroll pump at standby speed
        """
        
        response = self.device.request(self.interface_name + ".startStandbySpeed")
        self.device.handleError(response)
        return                 

    def stop(self):
        # type: () -> ()
        """
        Stops the scroll pump
        """
        
        response = self.device.request(self.interface_name + ".stop")
        self.device.handleError(response)
        return                 

