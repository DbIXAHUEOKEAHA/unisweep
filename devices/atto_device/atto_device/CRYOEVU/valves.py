class Valves:
    def __init__(self, device):
        self.device = device
        self.interface_name = "com.attocube.cryostat.interface.valves"

    def close(self, valveNumber):
        # type: (int) -> ()
        """
        Closes the valve

        Parameters:
            valveNumber: 0..12
                    
        """
        
        response = self.device.request(self.interface_name + ".close", [valveNumber, ])
        self.device.handleError(response)
        return                 

    def getStatus(self, valveNumber):
        # type: (int) -> (bool, bool, bool)
        """
        Gets the valve status

        Parameters:
            valveNumber: 0..11
                    
        Returns:
            errorNumber: No error = 0
            valve_status: 
            open_status_pin_status: 
            closed_status_pin_status: 
                    
        """
        
        response = self.device.request(self.interface_name + ".getStatus", [valveNumber, ])
        self.device.handleError(response)
        return response[1], response[2], response[3]                

    def open(self, valveNumber):
        # type: (int) -> ()
        """
        Opens the valve

        Parameters:
            valveNumber: 0..12
                    
        """
        
        response = self.device.request(self.interface_name + ".open", [valveNumber, ])
        self.device.handleError(response)
        return                 

