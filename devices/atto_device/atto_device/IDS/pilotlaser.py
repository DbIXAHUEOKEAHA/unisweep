class Pilotlaser:
    def __init__(self, device):
        self.device = device
        self.interface_name = "com.attocube.ids.pilotlaser"

    def enable(self):
        # type: () -> ()
        """
        Enables the pilot laser.
        """
        
        response = self.device.request(self.interface_name + ".enable")
        self.device.handleError(response)
        return                 

    def disable(self):
        # type: () -> ()
        """
        Disables the pilot laser.
        """
        
        response = self.device.request(self.interface_name + ".disable")
        self.device.handleError(response)
        return                 

    def getEnabled(self):
        # type: () -> (bool)
        """
        Reads out whether the pilot laser is enabled or not.
        Returns:
            errNo: errNo
            value_enable: enable true = enabled; false = disabled
                    
        """
        
        response = self.device.request(self.interface_name + ".getEnabled")
        self.device.handleError(response)
        return response[1]                

