class Realtime:
    def __init__(self, device):
        self.device = device
        self.interface_name = "com.attocube.ids.realtime"

    def getRtOutMode(self, tempVal):
        # type: (int) -> (int)
        """
        Reads out the current realtime output mode.

        Parameters:
            tempVal: 
                    
        Returns:
            errNo: errNo
            value_rtOutMode: rtOutMode 0 = HSSL (TTL), 1 = HSSL (LVDS), 2 = AquadB (TTL), /n3 = AquadB (LVDS), 4 = SinCos (TTL Error Signal), /n5 = SinCos (LVDS Error Signal), 6 = Linear (TTL), 7 = Linear (LVDS), /n8 = BiSS-C, 9 = Deactivated
                    
        """
        
        response = self.device.request(self.interface_name + ".getRtOutMode", [tempVal, ])
        self.device.handleError(response)
        return response[1]                

    def setRtOutMode(self, value):
        # type: (int) -> ()
        """
        Sets the real time output mode.

        Parameters:
            value: rtOutMode 0 = HSSL (TTL), 1 = HSSL (LVDS), 2 = AquadB (TTL), /n3 = AquadB (LVDS), 4 = SinCos (TTL Error Signal), /n5 = SinCos (LVDS Error Signal), 6 = Linear (TTL), 7 = Linear (LVDS), /n8 = BiSS-C, 9 = Deactivated
                    
        """
        
        response = self.device.request(self.interface_name + ".setRtOutMode", [value, ])
        if response["result"][0] == 0:
            self.apply()
        else:
            self.discard()
        self.device.handleError(response)
        return                 

    def getRtDistanceMode(self, tempVal):
        # type: (int) -> (int)
        """
        Reads out the distance mode.

        Parameters:
            tempVal: 
                    
        Returns:
            errNo: errNo
            value_linearmode: linearmode 1 = Displacement (Available in HSSL mode and Linear Mode) /n2 = Absolute Distance (Available in HSSL mode only) /n3 = Vibrometry (Available in Linear mode)
                    
        """
        
        response = self.device.request(self.interface_name + ".getRtDistanceMode", [tempVal, ])
        self.device.handleError(response)
        return response[1]                

    def setRtDistanceMode(self, value):
        # type: (int) -> ()
        """
        Sets the distance mode.

        Parameters:
            value: 1 = Displacement (HSSL mode and Linear Mode) /n2 = Absolute Distance (HSSL mode only) /n3 = Vibrometry (Linear mode)
                    
        """
        
        response = self.device.request(self.interface_name + ".setRtDistanceMode", [value, ])
        if response["result"][0] == 0:
            self.apply()
        else:
            self.discard()
        self.device.handleError(response)
        return                 

    def getResolutionBissC(self, tempVal):
        # type: (int) -> (int)
        """
        Reads out the BissC resolution.

        Parameters:
            tempVal: 
                    
        Returns:
            errNo: errNo
            value_resolution: resolution 1pm to 65535pm
                    
        """
        
        response = self.device.request(self.interface_name + ".getResolutionBissC", [tempVal, ])
        self.device.handleError(response)
        return response[1]                

    def setResolutionBissC(self, value):
        # type: (int) -> ()
        """
        Sets the BissC resolution.

        Parameters:
            value: resolution 1pm to 65535pm
                    
        """
        
        response = self.device.request(self.interface_name + ".setResolutionBissC", [value, ])
        if response["result"][0] == 0:
            self.apply()
        else:
            self.discard()
        self.device.handleError(response)
        return                 

    def getResolutionHsslLow(self, tempVal):
        # type: (int) -> (int)
        """
        Reads out the HSSL resolution low bit.#

        Parameters:
            tempVal: 
                    
        Returns:
            errNo: errNo
            value_resolution: resolution Resolution in the range of [0..46]
                    
        """
        
        response = self.device.request(self.interface_name + ".getResolutionHsslLow", [tempVal, ])
        self.device.handleError(response)
        return response[1]                

    def setResolutionHsslLow(self, value):
        # type: (int) -> ()
        """
        Sets the HSSL resolution low bit.

        Parameters:
            value: Resolution in the Range of [0..46]
                    
        """
        
        response = self.device.request(self.interface_name + ".setResolutionHsslLow", [value, ])
        if response["result"][0] == 0:
            self.apply()
        else:
            self.discard()
        self.device.handleError(response)
        return                 

    def getResolutionHsslHigh(self, tempVal):
        # type: (int) -> (int)
        """
        Reads out the HSSL resolution high bit.

        Parameters:
            tempVal: 
                    
        Returns:
            errNo: errNo
            value_resolution: resolution Resolution in the Range of [0..46]
                    
        """
        
        response = self.device.request(self.interface_name + ".getResolutionHsslHigh", [tempVal, ])
        self.device.handleError(response)
        return response[1]                

    def setResolutionHsslHigh(self, value):
        # type: (int) -> ()
        """
        Sets the HSSL resolution high bit.

        Parameters:
            value: Resolution in the Range of [0..46]
                    
        """
        
        response = self.device.request(self.interface_name + ".setResolutionHsslHigh", [value, ])
        if response["result"][0] == 0:
            self.apply()
        else:
            self.discard()
        self.device.handleError(response)
        return                 

    def getLinearRange(self, tempVal):
        # type: (int) -> (int)
        """
        Reads out the range number of Linear/Analog output mode.

        Parameters:
            tempVal: 
                    
        Returns:
            errNo: errNo
            value_rangenumber: rangenumber N, Linear Analog Range is +-2^(N+11) pm, with N /in [0, 34]
                    
        """
        
        response = self.device.request(self.interface_name + ".getLinearRange", [tempVal, ])
        self.device.handleError(response)
        return response[1]                

    def setLinearRange(self, rangenumber):
        # type: (int) -> ()
        """
        Sets the range number of Linear/Analog output mode.

        Parameters:
            rangenumber: N, Linear Analog Range is +-2^(N+11) pm, with N /in [0, 34]
                    
        """
        
        response = self.device.request(self.interface_name + ".setLinearRange", [rangenumber, ])
        self.device.handleError(response)
        return                 

    def getPeriodHsslClk(self, tempVal):
        # type: (int) -> (int)
        """
        Reads out the HSSL period clock.

        Parameters:
            tempVal: 
                    
        Returns:
            errNo: errNo
            value_period: period Period in the Range of [40ns..10200ns]
                    
        """
        
        response = self.device.request(self.interface_name + ".getPeriodHsslClk", [tempVal, ])
        self.device.handleError(response)
        return response[1]                

    def setPeriodHsslClk(self, period):
        # type: (int) -> ()
        """
        Set the HSSL period clock.

        Parameters:
            period: Period in the Range of [40ns..10200ns]
                    
        """
        
        response = self.device.request(self.interface_name + ".setPeriodHsslClk", [period, ])
        if response["result"][0] == 0:
            self.apply()
        else:
            self.discard()
        self.device.handleError(response)
        return                 

    def getPeriodHsslGap(self, tempVal):
        # type: (int) -> (int)
        """
        Reads out the HSSL period gap.

        Parameters:
            tempVal: 
                    
        Returns:
            errNo: errNo
            value_gap: gap Number of clocks
                    
        """
        
        response = self.device.request(self.interface_name + ".getPeriodHsslGap", [tempVal, ])
        self.device.handleError(response)
        return response[1]                

    def setPeriodHsslGap(self, value):
        # type: (int) -> ()
        """
        Set the HSSL gap.

        Parameters:
            value: Number of clocks
                    
        """
        
        response = self.device.request(self.interface_name + ".setPeriodHsslGap", [value, ])
        if response["result"][0] == 0:
            self.apply()
        else:
            self.discard()
        self.device.handleError(response)
        return                 

    def getPeriodSinCosClk(self, tempVal):
        # type: (int) -> (int)
        """
        Reads out the Sine-Cosine and AquadB period clock.

        Parameters:
            tempVal: 
                    
        Returns:
            errNo: errNo
            value_period: period 40ns to 10200ns
                    
        """
        
        response = self.device.request(self.interface_name + ".getPeriodSinCosClk", [tempVal, ])
        self.device.handleError(response)
        return response[1]                

    def setPeriodSinCosClk(self, value):
        # type: (int) -> ()
        """
        Sets the Sine-Cosine and AquadB period clock.

        Parameters:
            value: period 40ns to 10200ns
                    
        """
        
        response = self.device.request(self.interface_name + ".setPeriodSinCosClk", [value, ])
        if response["result"][0] == 0:
            self.apply()
        else:
            self.discard()
        self.device.handleError(response)
        return                 

    def getResolutionSinCos(self, tempVal):
        # type: (int) -> (int)
        """
        Reads out the Sine-Cosine and AquadB resolution.

        Parameters:
            tempVal: 
                    
        Returns:
            errNo: errNo
            value_resolution: resolution 1pm to 65535pm
                    
        """
        
        response = self.device.request(self.interface_name + ".getResolutionSinCos", [tempVal, ])
        self.device.handleError(response)
        return response[1]                

    def setResolutionSinCos(self, value):
        # type: (int) -> ()
        """
        Sets the Sine-Cosine and AquadB resolution.

        Parameters:
            value: resolution 1pm to 65535pm
                    
        """
        
        response = self.device.request(self.interface_name + ".setResolutionSinCos", [value, ])
        if response["result"][0] == 0:
            self.apply()
        else:
            self.discard()
        self.device.handleError(response)
        return                 

    def getHighPassCutOffFreq(self, tempVal):
        # type: (int) -> (int)
        """
        Reads out the high pass filter number of Linear/Analog output mode.

        Parameters:
            tempVal: 
                    
        Returns:
            errNo: errNo
            value_value: value N, Linear Analog High Pass Cut-Off freqency is 1600/2^N kHz, with N /in [1,24]
                    
        """
        
        response = self.device.request(self.interface_name + ".getHighPassCutOffFreq", [tempVal, ])
        self.device.handleError(response)
        return response[1]                

    def setHighPassCutOffFreq(self, value):
        # type: (int) -> ()
        """
        Sets the high pass filter number of Linear/Analog output mode.

        Parameters:
            value: N, Linear Analog High Pass Cut-Off freqency is 1600/2^N kHz, with N /in [1,24]
                    
        """
        
        response = self.device.request(self.interface_name + ".setHighPassCutOffFreq", [value, ])
        self.device.handleError(response)
        return                 

    def setAaf(self, enabled, attenuation, window):
        # type: (int, int, int) -> ()
        """
        Sets the anti-aliasing filter with assigned filter window.

        Parameters:
            enabled: 0 - disables the Anti-Aliasing Filter /n 1 - enables the Anti-Aliasing Filter
            attenuation: [3-30] dB m f_nyquist
            window: 0 = Rectangular,/n 1 = Cosine,/n 2 = Cosine^2,/n 3 = Hamming,/n 4 = Raised Cosine,/n 5 = Automatic
                    
        """
        
        response = self.device.request(self.interface_name + ".setAaf", [enabled, attenuation, window, ])
        self.device.handleError(response)
        return                 

    def getAafAttenuation(self):
        # type: () -> (int)
        """
        Returns the current attenuation at f_nyquist of the anti-aliasing filter.
        Returns:
            errNo: errNo
            value_attenuation: attenuation [3-30] dB m f_nyquist
                    
        """
        
        response = self.device.request(self.interface_name + ".getAafAttenuation")
        self.device.handleError(response)
        return response[1]                

    def getAafWindow(self):
        # type: () -> (int)
        """
        Returns the current filter window of the anti-aliasing filter.
        Returns:
            errNo: errNo
            value_window: window 0 = Rectangular,/n 1 = Cosine,/n 2 = Cosine^2,/n 3 = Hamming,/n 4 = Raised Cosine,/n 5 = Automatic
                    
        """
        
        response = self.device.request(self.interface_name + ".getAafWindow")
        self.device.handleError(response)
        return response[1]                

    def AafIsEnabled(self):
        # type: () -> (bool)
        """
        Checks if the anti-aliasing filter is enabled.
        Returns:
            errNo: errNo
            value_enabled: enabled false: Anti-Aliasing Filter is disabled /ntrue: Anti-Aliasing Filter is enabled
                    
        """
        
        response = self.device.request(self.interface_name + ".AafIsEnabled")
        self.device.handleError(response)
        return response[1]                

    def getAafEnabled(self):
        # type: () -> (bool)
        """
        Checks if the anti-aliasing filter is enabled.
        Returns:
            errNo: errNo
            value_enabled: enabled false - the Anti-Aliasing Filter is disabled /n true - the Anti-Aliasing Filter is enabled
                    
        """
        
        response = self.device.request(self.interface_name + ".getAafEnabled")
        self.device.handleError(response)
        return response[1]                

    def apply(self):
        # type: () -> ()
        """
        Applies new real time settings.
        """
        
        response = self.device.request(self.interface_name + ".apply")
        self.device.handleError(response)
        return                 

    def discard(self):
        # type: () -> ()
        """
        Discards new real time settings.
        """
        
        response = self.device.request(self.interface_name + ".discard")
        self.device.handleError(response)
        return                 

    def enableTestChannel(self, axis):
        # type: (int) -> ()
        """
        Enables the Test Channel, which can be used for estimating the maximum signal range.

        Parameters:
            axis: Test Channel Master Axis
                    
        """
        
        response = self.device.request(self.interface_name + ".enableTestChannel", [axis, ])
        self.device.handleError(response)
        return                 

    def disableTestChannel(self):
        # type: () -> ()
        """
        Disables the test channel.
        """
        
        response = self.device.request(self.interface_name + ".disableTestChannel")
        self.device.handleError(response)
        return                 

    def getTestChannelEnabled(self):
        # type: () -> (bool)
        """
        Checks if the test channel is enabled
        Returns:
            errNo: errNo
            value_enabled: enabled true = enabled, false = disabled
                    
        """
        
        response = self.device.request(self.interface_name + ".getTestChannelEnabled")
        self.device.handleError(response)
        return response[1]                

