class System:
    def __init__(self, device):
        self.device = device
        self.interface_name = "com.attocube.ids.system"

    def stopMeasurement(self):
        # type: () -> ()
        """
        Stops the displacement measurement system state.
        """
        
        response = self.device.request(self.interface_name + ".stopMeasurement")
        self.device.handleError(response)
        return                 

    def startMeasurement(self):
        # type: () -> ()
        """
        Starts the displacement measurement system state.
        """
        
        response = self.device.request(self.interface_name + ".startMeasurement")
        self.device.handleError(response)
        return                 

    def startOpticsAlignment(self):
        # type: () -> ()
        """
        Starts the optical alignment system state.
        """
        
        response = self.device.request(self.interface_name + ".startOpticsAlignment")
        self.device.handleError(response)
        return                 

    def stopOpticsAlignment(self):
        # type: () -> ()
        """
        Stops the optical alignment system state.
        """
        
        response = self.device.request(self.interface_name + ".stopOpticsAlignment")
        self.device.handleError(response)
        return                 

    def resetAxes(self):
        # type: () -> ()
        """
        Resets the position value of all measurement axes to zero.
        """
        
        response = self.device.request(self.interface_name + ".resetAxes")
        self.device.handleError(response)
        return                 

    def resetAxis(self, axis):
        # type: (int) -> ()
        """
        Resets the position value of a specific measurement axis to zero.

        Parameters:
            axis: [0|1|2]
                    
        """
        
        response = self.device.request(self.interface_name + ".resetAxis", [axis, ])
        self.device.handleError(response)
        return                 

    def resetError(self, perform):
        # type: (bool) -> ()
        """
        Resets a measurement error that can have occurred with the aim to continue the interrupted measurement.

        Parameters:
            perform: renormalization
                    
        """
        try:
            self.device.tcp.settimeout(20.0)
        
            response = self.device.request(self.interface_name + ".resetError", [perform, ])
            self.device.handleError(response)
            return                 
        finally:
            self.device.tcp.settimeout(10)
        

    def getCurrentMode(self):
        # type: () -> (str)
        """
        Reads out the current IDS system state.
        Returns:
            errNo: errNo
            value_mode: mode Values: "system idle", "measurement starting", "measurement running", "optics alignment starting", "optics alignment running", "test channels enabled"
                    
        """
        
        response = self.device.request(self.interface_name + ".getCurrentMode")
        self.device.handleError(response)
        return response[1]                

    def getFpgaVersion(self):
        # type: () -> (str)
        """
        Reads out the IDS FPGA version.
        Returns:
            errNo: errNo
            value_version: version Version in the form X.Y.Z
                    
        """
        
        response = self.device.request(self.interface_name + ".getFpgaVersion")
        self.device.handleError(response)
        return response[1]                

    def getDeviceType(self):
        # type: () -> (str)
        """
        Reads out the IDS device type.
        Returns:
            errNo: errNo
            value_type: type Type of IDS (e.g. "IDS3010")
                    
        """
        
        response = self.device.request(self.interface_name + ".getDeviceType")
        self.device.handleError(response)
        return response[1]                

    def getSystemError(self):
        # type: () -> ()
        """
        Cheks for a system error.
        """
        
        response = self.device.request(self.interface_name + ".getSystemError")
        self.device.handleError(response)
        return                 

    def getNbrFeaturesActivated(self):
        # type: () -> (int)
        """
        Reads out the amount of activated features activated on the IDS.
        Returns:
            errNo: errNo
            value_nbr: nbr Gives the number of activated features.
                    
        """
        
        response = self.device.request(self.interface_name + ".getNbrFeaturesActivated")
        self.device.handleError(response)
        return response[1]                

    def getFeaturesName(self, featurenumber):
        # type: (int) -> (str)
        """
        Converts the IDS feature number to its corresponding name.

        Parameters:
            featurenumber: Number of feature
                    
        Returns:
            errNo: errNo
            value_names: names The name of the corresponding feature
                    
        """
        
        response = self.device.request(self.interface_name + ".getFeaturesName", [featurenumber, ])
        self.device.handleError(response)
        return response[1]                

    def getInitMode(self):
        # type: () -> (int)
        """
        Returns the Initialization mode.
        Returns:
            errNo: errNo
            value_mode: mode 0 = High Accuracy Initialization; 1 = Quick Initialization
                    
        """
        
        response = self.device.request(self.interface_name + ".getInitMode")
        self.device.handleError(response)
        return response[1]                

    def setInitMode(self, mode):
        # type: (int) -> ()
        """
        Sets the mode for the initialization procedure that is performed when starting a measurement.

        Parameters:
            mode: 0 = High Accuracy Initialization; 1 = Quick Initialization
                    
        """
        
        response = self.device.request(self.interface_name + ".setInitMode", [mode, ])
        self.device.handleError(response)
        return                 

