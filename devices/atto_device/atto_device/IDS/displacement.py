class Displacement:
    def __init__(self, device):
        self.device = device
        self.interface_name = "com.attocube.ids.displacement"

    def getMeasurementEnabled(self):
        # type: () -> (bool)
        """
        This function can be used to see if the measurement is running
        Returns:
            errNo: errNo
            value_enable: enable true = enabled; false = disabled
                    
        """
        
        response = self.device.request(self.interface_name + ".getMeasurementEnabled")
        self.device.handleError(response)
        return response[1]                

    def getAverageN(self):
        # type: () -> (int)
        """
        Reads-out the averaging (lowpass) parameter N.
        Returns:
            errNo: errNo
            value_averageN: averageN A value from 0 to 24
                    
        """
        
        response = self.device.request(self.interface_name + ".getAverageN")
        self.device.handleError(response)
        return response[1]                

    def setAverageN(self, value):
        # type: (int) -> ()
        """
        Sets the averaging (lowpass) parameter N.

        Parameters:
            value: AverageN value from 0 to 24
                    
        """
        
        response = self.device.request(self.interface_name + ".setAverageN", [value, ])
        self.device.handleError(response)
        return                 

    def linProc(self, axis, fringesnbr, samplesperfringe, set):
        # type: (int, int, int, int) -> (int, int)
        """
        Important note: This function is not actively supported anymore.

        Parameters:
            axis: [0|1|2]
            fringesnbr: Number of fringes to be acquired
            samplesperfringe: Number of samples per fringe
            set: 0 = evaluate current nonlinear amplitude /n1 = perform linearization and upload look up table /n2 = Clear look up table /n3 = Perform only calculation of Phi file
                    
        Returns:
            errNo: errNo
            value_lintable: lintable String, which contains all 512 phase related correction values
            value_nonlinearamp: nonlinearamp String which contains the residual positive and negative maximal nonlinear amplitude
                    
        """
        try:
            self.device.tcp.settimeout(100.0)
        
            response = self.device.request(self.interface_name + ".linProc", [axis, fringesnbr, samplesperfringe, set, ])
            self.device.handleError(response)
            return response[1], response[2]                
        finally:
            self.device.tcp.settimeout(10)
        

    def getSignalQuality(self, axis, ignoreFunctionError=True):
        # type: (int) -> (int, int)
        """
        This function can be used to monitor the alignment contrast (peak-to-peak of the basic /ninterference signal amplitude) and the basline (its offset) during a running /nmeasurement.

        Parameters:
            axis: [0|1|2]
                    
        Returns:
            value_warningNo: warningNo Warning code, can be converted into a string using the errorNumberToString function
            value_contrast: contrast Contrast of the base band signal in ‰
            value_baseline: baseline Offset of the contrast measurement in ‰
                    
        """
        
        response = self.device.request(self.interface_name + ".getSignalQuality", [axis, ])
        self.device.handleError(response, ignoreFunctionError)
        return response[0], response[1], response[2]                

    def getAxisSignalQuality(self, axis, ignoreFunctionError=True):
        # type: (int) -> (int, int)
        """
        This function can be used to monitor the alignment contrast (peak-to-peak of the basic /ninterference signal amplitude) and the basline (its offset) during a running /nmeasurement.

        Parameters:
            axis: [0|1|2]
                    
        Returns:
            value_warningNo: warningNo Warning code, can be converted into a string using the errorNumberToString function
            value_contrast: contrast Contrast of the base band signal in ‰
            value_baseline: baseline Offset of the contrast measurement in ‰
                    
        """
        
        response = self.device.request(self.interface_name + ".getAxisSignalQuality", [axis, ])
        self.device.handleError(response, ignoreFunctionError)
        return response[0], response[1], response[2]                

    def getReferencePosition(self, axis, ignoreFunctionError=True):
        # type: (int) -> (float)
        """
        The reference position information is estimated at the measurement initialization procedure or on reset.

        Parameters:
            axis: [0|1|2]
                    
        Returns:
            value_warningNo: warningNo Warning code, can be converted into a string using the errorNumberToString function
            value_position: position reference position of the axis in pm
                    
        """
        
        response = self.device.request(self.interface_name + ".getReferencePosition", [axis, ])
        self.device.handleError(response, ignoreFunctionError)
        return response[0], response[1]                

    def getReferencePositions(self, ignoreFunctionError=True):
        # type: () -> (float, float, float)
        """
        The reference position information is estimated at the measurement initialization procedure or on reset.
        Returns:
            value_warningNo: warningNo Warning code, can be converted into a string using the errorNumberToString function
            value_position1: position0 position of the axis 0 in pm
            value_position2: position1 position of the axis 1 in pm
            value_position3: position2 position of the axis 2 in pm
                    
        """
        
        response = self.device.request(self.interface_name + ".getReferencePositions")
        self.device.handleError(response, ignoreFunctionError)
        return response[0], response[1], response[2], response[3]                

    def getAbsolutePosition(self, axis, ignoreFunctionError=True):
        # type: (int) -> (float)
        """
        The absolute position information is estimated at the measurement initialization procedure.

        Parameters:
            axis: [0|1|2]
                    
        Returns:
            value_warningNo: warningNo Warning code, can be converted into a string using the errorNumberToString function
            value_position: position position of the axis in pm
                    
        """
        
        response = self.device.request(self.interface_name + ".getAbsolutePosition", [axis, ])
        self.device.handleError(response, ignoreFunctionError)
        return response[0], response[1]                

    def getAbsolutePositions(self, ignoreFunctionError=True):
        # type: () -> (float, float, float)
        """
        The absolute position information is estimated at the measurement initialization /nprocedure.
        Returns:
            value_warningNo: warningNo Warning code, can be converted into a string using the errorNumberToString function
            value_position1: position0 position of the axis 0 in pm
            value_position2: position1 position of the axis 1 in pm
            value_position3: position2 position of the axis 2 in pm
                    
        """
        
        response = self.device.request(self.interface_name + ".getAbsolutePositions")
        self.device.handleError(response, ignoreFunctionError)
        return response[0], response[1], response[2], response[3]                

    def getAxisDisplacement(self, axis, ignoreFunctionError=True):
        # type: (int) -> (float)
        """
        Reads out the displacement value of a specific measurement axis.

        Parameters:
            axis: [0|1|2]
                    
        Returns:
            value_warningNo: warningNo Warning code, can be converted into a string using the errorNumberToString function
            value_displacement: displacement Displacement of the axis in pm
                    
        """
        
        response = self.device.request(self.interface_name + ".getAxisDisplacement", [axis, ])
        self.device.handleError(response, ignoreFunctionError)
        return response[0], response[1]                

    def getAxesDisplacement(self, ignoreFunctionError=True):
        # type: () -> (float, float, float)
        """
        Reads out the displacement values of all three measurement axes.
        Returns:
            value_warningNo: warningNo Warning code, can be converted into a string using the errorNumberToString function
            value_displacement1: displacement0 displacement of the axis 0 in pm
            value_displacement2: displacement1 displacement of the axis 1 in pm
            value_displacement3: displacement2 displacement of the axis 2 in pm
                    
        """
        
        response = self.device.request(self.interface_name + ".getAxesDisplacement")
        self.device.handleError(response, ignoreFunctionError)
        return response[0], response[1], response[2], response[3]                

