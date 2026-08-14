class Axis:
    def __init__(self, device):
        self.device = device
        self.interface_name = "com.attocube.ids.axis"

    def getPassMode(self, tempVal):
        # type: (int) -> (int)
        """
        Reads out the current pass mode.

        Parameters:
            tempVal: 
                    
        Returns:
            errNo: errNo
            value_mode: mode 0 = single; pass 1 = dual pass
                    
        """
        
        response = self.device.request(self.interface_name + ".getPassMode", [tempVal, ])
        self.device.handleError(response)
        return response[1]                

    def setPassMode(self, mode):
        # type: (int) -> ()
        """
        Sets the desired pass mode.

        Parameters:
            mode: 0 = single pass; 1 = dual pass
                    
        """
        
        response = self.device.request(self.interface_name + ".setPassMode", [mode, ])
        if response["result"][0] == 0:
            self.apply()
        else:
            self.discard()
        self.device.handleError(response)
        return                 

    def getMasterAxis(self, tempVal):
        # type: (int) -> (int)
        """
        Returns the master axis (for more information please refer to the IDS User Manual).

        Parameters:
            tempVal: 
                    
        Returns:
            errNo: errNo
            value_masteraxis: masteraxis Axis which is operating as masteraxis [0..2]
                    
        """
        
        response = self.device.request(self.interface_name + ".getMasterAxis", [tempVal, ])
        self.device.handleError(response)
        return response[1]                

    def setMasterAxis(self, axis):
        # type: (int) -> ()
        """
        Sets the master axis (for more information please refer to the IDS User Manual).

        Parameters:
            axis: Axis which is operating as masteraxis [0..2]
                    
        """
        
        response = self.device.request(self.interface_name + ".setMasterAxis", [axis, ])
        if response["result"][0] == 0:
            self.apply()
        else:
            self.discard()
        self.device.handleError(response)
        return                 

    def apply(self):
        # type: () -> ()
        """
        Applies new axis settings.
        """
        
        response = self.device.request(self.interface_name + ".apply")
        self.device.handleError(response)
        return                 

    def discard(self):
        # type: () -> ()
        """
        Discards new axis settings.
        """
        
        response = self.device.request(self.interface_name + ".discard")
        self.device.handleError(response)
        return                 

