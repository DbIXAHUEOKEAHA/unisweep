class Pressures:
    def __init__(self, device):
        self.device = device
        self.interface_name = "com.attocube.cryostat.interface.pressures"

    def getCryoInPressure(self):
        # type: () -> (float)
        """
        Gets the cryostat in pressure
        Returns:
            errorNumber: No error = 0
            cryostat_in_pressure: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getCryoInPressure")
        self.device.handleError(response)
        return response[1]                

    def getCryoOutPressure(self):
        # type: () -> (float)
        """
        Gets the cryostat out pressure
        Returns:
            errorNumber: No error = 0
            cryostat_out_pressure: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getCryoOutPressure")
        self.device.handleError(response)
        return response[1]                

    def getDumpPressure(self):
        # type: () -> (float)
        """
        Gets the dump pressure
        Returns:
            errorNumber: No error = 0
            dump_pressure: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getDumpPressure")
        self.device.handleError(response)
        return response[1]                

