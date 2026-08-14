class Nlc:
    def __init__(self, device):
        self.device = device
        self.interface_name = "com.attocube.ids.nlc"

    def clearLut(self, axis):
        # type: (int) -> ()
        """
        Deactivates the LUT and removes it from the device

        Parameters:
            axis: Axis [0|1|2] of the IDS
                    
        """
        
        response = self.device.request(self.interface_name + ".clearLut", [axis, ])
        self.device.handleError(response)
        return                 

    def createLut(self, axis):
        # type: (int) -> ()
        """
        Creates a new LUT for the given axis.

        Parameters:
            axis: Axis [0|1|2] of the IDS where the LUT should be generated
                    
        """
        
        response = self.device.request(self.interface_name + ".createLut", [axis, ])
        self.device.handleError(response)
        return                 

    def estimateNonlinearities(self, axis):
        # type: (int) -> ()
        """
        Estimates the nonlinearity error for the current device settings without changing or updating any settings.

        Parameters:
            axis: Axis [0|1|2] of the IDS of which the nonlinearity error is to be estimated
                    
        """
        
        response = self.device.request(self.interface_name + ".estimateNonlinearities", [axis, ])
        self.device.handleError(response)
        return                 

    def getDynamicNormalization(self, axis):
        # type: (int) -> (int)
        """
        Returns the normalization mode of a specific axis.

        Parameters:
            axis: Axis [0|1|2] of the IDS of which the normalization mode is queried
                    
        Returns:
            errNo: Error number if an error occured while getting normalization mode
            mode: Normalization Mode

    0    Dynamic normalization

    1    Normalization frozen

    2    Normalization mode determined by target velocity
                    
        """
        
        response = self.device.request(self.interface_name + ".getDynamicNormalization", [axis, ])
        self.device.handleError(response)
        return response[1]                

    def getHistogram(self, axis):
        # type: (int) -> (str)
        """
        Returns a histogram of the measured nonlinearity errors obtained from the last call of createLut or estimateNonlinearites.

        Parameters:
            axis: Axis [0|1|2] of the IDS
                    
        Returns:
            errNo: Error number if one occured during retrieving the histogram
            histogram: Json dumped histogram array
                    
        """
        
        response = self.device.request(self.interface_name + ".getHistogram", [axis, ])
        self.device.handleError(response)
        return response[1]                

    def getLut(self, axis):
        # type: (int) -> (str)
        """
        Returns the LUT determined by createLut (which can be applied by setLutApplied).

        Parameters:
            axis: Axis [0|1|2] of the IDS
                    
        Returns:
            errNo: Error number if one occured during retrieving the LUT
            lut: Json dumped LUT array with 512 integers
                    
        """
        
        response = self.device.request(self.interface_name + ".getLut", [axis, ])
        self.device.handleError(response)
        return response[1]                

    def getLutApplied(self, axis):
        # type: (int) -> (bool)
        """
        Returns whether a LUT is applied or not for a given axis.

        Parameters:
            axis: Axis [0|1|2] of the IDS of which the LUT apply rule is queried
                    
        Returns:
            errNo: Error number if an error occured while quering the LUT apply rule
            apply: True, if LUT is applied on this axis else False
                    
        """
        
        response = self.device.request(self.interface_name + ".getLutApplied", [axis, ])
        self.device.handleError(response)
        return response[1]                

    def getLutStatus(self, axis):
        # type: (int) -> (bool)
        """
        Returns if a LUT is available and if warnings or errors occurred during creation.

        Parameters:
            axis: Axis [0|1|2] of the IDS of which the status of the LUT should be returned
                    
        Returns:
            creationWarning: Error or warning number if one occured while creating the LUT, 0 in case of no error
            status: True, if a LUT exists else False
                    
        """
        
        response = self.device.request(self.interface_name + ".getLutStatus", [axis, ])
        self.device.handleError(response)
        return response[1]                

    def getNonlinearityEstimation(self):
        # type: () -> (str)
        """
        Returns the LUT created by estimateNonlinearities (read-only mode) to compensate the nonlinearity error of the device for the current device settings. If no estimation was created an array of zeros is returned.
        Returns:
            errNo: Error number if one occured loading the LUT
            lut: Json dumped LUT array with 512 integers
                    
        """
        
        response = self.device.request(self.interface_name + ".getNonlinearityEstimation")
        self.device.handleError(response)
        return response[1]                

    def getRawLut(self, axis):
        # type: (int) -> (str)
        """
        Returns the raw lut created by createLut or estimateNonlinearites.    For debugging only.

        Parameters:
            axis: Axis [0|1|2] of the IDS
                    
        Returns:
            errNo: Error number if one occured loading the lut
            raw_lut: Json dumped lut array
                    
        """
        
        response = self.device.request(self.interface_name + ".getRawLut", [axis, ])
        self.device.handleError(response)
        return response[1]                

    def getVelocityThresholds(self):
        # type: () -> (int, int)
        """
        Returns the threshold velocity (in µm/s) for mode 2 of setDynamicNormalization.
        Returns:
            errNo: Error number if an error occured
            velocityOn: Velocity of the target in µm/s when to switch the normalization on (default: 10 µm/s)
            velocityOff: Velocity of the target in µm/s when to switch the normalization off (default: 5 µm/s)
                    
        """
        
        response = self.device.request(self.interface_name + ".getVelocityThresholds")
        self.device.handleError(response)
        return response[1], response[2]                

    def setDynamicNormalization(self, axis, mode):
        # type: (int, int) -> ()
        """
        Sets the normalization mode of a specific axis.

        Parameters:
            axis: Axis [0|1|2] of the IDS of which the normalization mode should be set
            mode: Normalization Mode
    0    Dynamic normalization (default)
    1    Normalization frozen (for slow target drifts)
    2    Automatic alternation between mode 0 and 1 depending on the target velocity
                    
        """
        
        response = self.device.request(self.interface_name + ".setDynamicNormalization", [axis, mode, ])
        self.device.handleError(response)
        return                 

    def setLut(self, axis, lut):
        # type: (int, str) -> ()
        """
        Uploads a LUT for a specific axis (which can be applied by setLutApplied)

        Parameters:
            axis: Axis [0|1|2] of the IDS
            lut: Json dumped LUT array with 512 integers
                    
        """
        
        response = self.device.request(self.interface_name + ".setLut", [axis, lut, ])
        self.device.handleError(response)
        return                 

    def setLutApplied(self, axis, apply):
        # type: (int, bool) -> ()
        """
        Sets the apply rule for the given axis

        Parameters:
            axis: Axis [0|1|2] of the IDS of which the apply rule should be set
            apply: True for applying a LUT, False for disabling a LUT
                    
        """
        
        response = self.device.request(self.interface_name + ".setLutApplied", [axis, apply, ])
        self.device.handleError(response)
        return                 

    def setVelocityThresholds(self, velocityOn, velocityOff):
        # type: (int, int) -> ()
        """
        Sets the threshold velocity (in µm/s) for mode 2 of setDynamicNormalization. By default, the normalization in mode 2 is frozen for velocities below 5 µm/s and switched to dynamic mode for velocities above 10 µm/s.

        Parameters:
            velocityOn: Velocity of the target in µm/s when to switch the normalization on (default: 10 µm/s)
            velocityOff: Velocity of the target in µm/s when to switch the normalization off (default: 5 µm/s)
                    
        """
        
        response = self.device.request(self.interface_name + ".setVelocityThresholds", [velocityOn, velocityOff, ])
        self.device.handleError(response)
        return                 

