class Compressor:
    def __init__(self, device):
        self.device = device
        self.interface_name = "com.attocube.cryostat.interface.compressor"

    def getStatus(self):
        # type: () -> (bool)
        """
        Gets the compressor status
        Returns:
            errorNumber: No error = 0
            compressor_status: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getStatus")
        self.device.handleError(response)
        return response[1]                

    def start(self):
        # type: () -> ()
        """
        starts the compressor
        """
        
        response = self.device.request(self.interface_name + ".start")
        self.device.handleError(response)
        return                 

    def stop(self):
        # type: () -> ()
        """
        stops the compressor
        """
        
        response = self.device.request(self.interface_name + ".stop")
        self.device.handleError(response)
        return                 

