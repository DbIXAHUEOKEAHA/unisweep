class Cryooutvalve:
    def __init__(self, device):
        self.device = device
        self.interface_name = "com.attocube.cryostat.interface.cryoOutValve"

    def close(self):
        # type: () -> ()
        """
        Closes the cryostat out valve
        """
        
        response = self.device.request(self.interface_name + ".close")
        self.device.handleError(response)
        return                 

    def getStatus(self):
        # type: () -> (bool)
        """
        Gets the cryostat out valve status
        Returns:
            errorNumber: No error = 0
            pump_valve_status: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getStatus")
        self.device.handleError(response)
        return response[1]                

    def open(self):
        # type: () -> ()
        """
        Opens the cryostat out valve
        """
        
        response = self.device.request(self.interface_name + ".open")
        self.device.handleError(response)
        return                 

