class Pressures:
    def __init__(self, device):
        self.device = device
        self.interface_name = "com.attocube.cryostat.interface.pressures"

    def getSampleSpacePressure(self):
        # type: () -> (float)
        """
        Gets the sample space pressure
        Returns:
            errorNumber: No error = 0
            sample_space_pressure: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getSampleSpacePressure")
        self.device.handleError(response)
        return response[1]                

