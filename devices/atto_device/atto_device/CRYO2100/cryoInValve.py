class Cryoinvalve:
    def __init__(self, device):
        self.device = device
        self.interface_name = "com.attocube.cryostat.interface.cryoInValve"

    def close(self):
        # type: () -> ()
        """
        Closes the cryostat in valve
        """
        
        response = self.device.request(self.interface_name + ".close")
        self.device.handleError(response)
        return                 

    def getStatus(self):
        # type: () -> (bool)
        """
        Gets the cryostat in valve status
        Returns:
            errorNumber: No error = 0
            cryostat_in_valve_status: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getStatus")
        self.device.handleError(response)
        return response[1]                

    def open(self):
        # type: () -> ()
        """
        Opens the cryostat in valve
        """
        
        response = self.device.request(self.interface_name + ".open")
        self.device.handleError(response)
        return                 

