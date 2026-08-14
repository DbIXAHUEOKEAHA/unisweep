class Main:
    def __init__(self, device):
        self.device = device
        self.interface_name = "com.attocube.cryostat.interface.main"

    def changeCryostatType(self, newType):
        # type: (str) -> ()
        """
        Change the cryostat type

        Parameters:
            newType: 
                    
        """
        
        response = self.device.request(self.interface_name + ".changeCryostatType", [newType, ])
        self.device.handleError(response)
        return                 

    def getAvailableCryostatTypes(self):
        # type: () -> (str)
        """
        Get all available cryostat types
        Returns:
            errorNumber: No error = 0
            types: CSV string of types
                    
        """
        
        response = self.device.request(self.interface_name + ".getAvailableCryostatTypes")
        self.device.handleError(response)
        return response[1]                

