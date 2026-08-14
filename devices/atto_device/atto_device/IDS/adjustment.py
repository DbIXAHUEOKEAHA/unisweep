class Adjustment:
    def __init__(self, device):
        self.device = device
        self.interface_name = "com.attocube.ids.adjustment"

    def getContrastInPermille(self, axis, ignoreFunctionError=True):
        # type: (int) -> (int, int, int)
        """
        This function can be used to monitor the alignment contrast (peak-to-peak of the /nbasic interference signal amplitude) and the basline (its offset) during alignment /nmode.

        Parameters:
            axis: Axis to get the value from [0..2]
                    
        Returns:
            value_warningNo: warningNo Warning code, can be converted into a string using the errorNumberToString function
            value_contast: contast Contrast of the base band signal in permille
            value_baseline: baseline Offset of the contrast measurement in permille
            value_mixcontrast: mixcontrast lower contrast measurment when measuring a mix contrast (indicated by error code)
                    
        """
        
        response = self.device.request(self.interface_name + ".getContrastInPermille", [axis, ])
        self.device.handleError(response, ignoreFunctionError)
        return response[0], response[1], response[2], response[3]                

    def getAdjustmentEnabled(self):
        # type: () -> (bool)
        """
        This function can be used to see if the adjustment is running
        Returns:
            errNo: errNo
            value_enable: enable true = enabled; false = disabled
                    
        """
        
        response = self.device.request(self.interface_name + ".getAdjustmentEnabled")
        self.device.handleError(response)
        return response[1]                

