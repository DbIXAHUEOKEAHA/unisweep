class Membranepump:
    def __init__(self, device):
        self.device = device
        self.interface_name = "com.attocube.cryostat.interface.membranePump"

    def getStatus(self):
        # type: () -> (bool)
        """
        Gets the membrane pump status
        Returns:
            errorNumber: No error = 0
            membrane_pump_status: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getStatus")
        self.device.handleError(response)
        return response[1]                

    def getStatusString(self):
        # type: () -> (str)
        """
        Gets the membrane pump status as string
        Returns:
            errorNumber: No error = 0
            membrane_pump_status_string: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getStatusString")
        self.device.handleError(response)
        return response[1]                

    def start(self):
        # type: () -> ()
        """
        starts the membrane pump
        """
        
        response = self.device.request(self.interface_name + ".start")
        self.device.handleError(response)
        return                 

    def stop(self):
        # type: () -> ()
        """
        stops the membrane pump
        """
        
        response = self.device.request(self.interface_name + ".stop")
        self.device.handleError(response)
        return                 

