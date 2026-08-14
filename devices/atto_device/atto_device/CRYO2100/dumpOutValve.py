class Dumpoutvalve:
    def __init__(self, device):
        self.device = device
        self.interface_name = "com.attocube.cryostat.interface.dumpOutValve"

    def close(self):
        # type: () -> ()
        """
        Closes the dump out valve
        """
        
        response = self.device.request(self.interface_name + ".close")
        self.device.handleError(response)
        return                 

    def getStatus(self):
        # type: () -> (bool)
        """
        Gets the dump out valve status
        Returns:
            errorNumber: No error = 0
            dump_out_valve_status: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getStatus")
        self.device.handleError(response)
        return response[1]                

    def open(self):
        # type: () -> ()
        """
        opens the dump out valve
        """
        
        response = self.device.request(self.interface_name + ".open")
        self.device.handleError(response)
        return                 

