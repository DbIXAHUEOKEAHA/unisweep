class Manual:
    def __init__(self, device):
        self.device = device
        self.interface_name = "com.attocube.ids.manual"

    def getHumidityInPercent(self, axis):
        # type: (int) -> (float)
        """
        Reads out the manually configured humidity (compensation mode 1).

        Parameters:
            axis: Axis to get the humidity for.
Parameter has to be -1 for the moment,
individual axes will be supported in the next firmware release
                    
        Returns:
            errNo: Error code, if there was an error, otherwise 0 for ok
            humidity: humidity in hPa
                    
        """
        
        response = self.device.request(self.interface_name + ".getHumidityInPercent", [axis, ])
        self.device.handleError(response)
        return response[1]                

    def getPressureInHPa(self, axis):
        # type: (int) -> (float)
        """
        Reads out the manually configured Pressure (compensation mode 1).

        Parameters:
            axis: Axis to get the pressure for.
Parameter has to be -1 for the moment,
individual axes will be supported in the next firmware release
                    
        Returns:
            errNo: Error code, if there was an error, otherwise 0 for ok
            pressure: pressure in hPa
                    
        """
        
        response = self.device.request(self.interface_name + ".getPressureInHPa", [axis, ])
        self.device.handleError(response)
        return response[1]                

    def getRefractiveIndex(self, axis):
        # type: (int) -> (float)
        """
        Reads out the manually configured value for the refractive index (compensation mode 2).

        Parameters:
            axis: Axis to get the mode for.
Parameter has to be -1 for the moment,
individual axes will be supported in the next firmware release
                    
        Returns:
            errNo: Error code, if there was an error, otherwise 0 for ok
            rindex: refractive index
                    
        """
        
        response = self.device.request(self.interface_name + ".getRefractiveIndex", [axis, ])
        self.device.handleError(response)
        return response[1]                

    def getTemperatureInDegrees(self, axis):
        # type: (int) -> (float)
        """
        Reads out the manually configured Temperature (compensation mode 1).

        Parameters:
            axis: Axis to set the temperature for.
Parameter has to be -1 for the moment,
individual axes will be supported in the next firmware release
                    
        Returns:
            errNo: Error code, if there was an error, otherwise 0 for ok
            temperature: temperature in degree celsius
                    
        """
        
        response = self.device.request(self.interface_name + ".getTemperatureInDegrees", [axis, ])
        self.device.handleError(response)
        return response[1]                

    def setHumidityInPercent(self, axis, humidity):
        # type: (int, float) -> ()
        """
        Sets the manually configured Humidity (compensation mode 1). The input range is defined to 0 to 100 % (valid range for the Ciddor Equation).

        Parameters:
            axis: Axis to set the humidity for.
Parameter has to be -1 for the moment,
individual axes will be supported in the next firmware release
            humidity: humidity in Percent
                    
        """
        
        response = self.device.request(self.interface_name + ".setHumidityInPercent", [axis, humidity, ])
        self.device.handleError(response)
        return                 

    def setPressureInHPa(self, axis, pressure):
        # type: (int, float) -> ()
        """
        Sets the manually configured Pressure (compensation mode 1). The input range is defined to 800 to 1200 hPa (valid range for the Ciddor Equation).

        Parameters:
            axis: Axis to set the pressure for-
Parameter has to be -1 for the moment,
individual axes will be supported in the next firmware release
            pressure: pressure in hPa
                    
        """
        
        response = self.device.request(self.interface_name + ".setPressureInHPa", [axis, pressure, ])
        self.device.handleError(response)
        return                 

    def setRefractiveIndex(self, axis, rindex):
        # type: (int, float) -> ()
        """
        Sets the refractive index for the direct mode (compensation mode 2). The input range is defined to be greater than 1.

        Parameters:
            axis: Axis to set the mode for.
Parameter has to be -1 for the moment,
individual axes will be supported in the next firmware release
            rindex: refractive index
                    
        """
        
        response = self.device.request(self.interface_name + ".setRefractiveIndex", [axis, rindex, ])
        self.device.handleError(response)
        return                 

    def setTemperatureInDegrees(self, axis, temperature):
        # type: (int, float) -> ()
        """
        Sets the manually configured Temperature (compensation mode 1). The input range is defined to -40 to +100 °C (valid range for the Ciddor Equation).

        Parameters:
            axis: Axis to set the temperature for.
Parameter has to be -1 for the moment,
individual axes will be supported in the next firmware release
            temperature: temperature in degree celcius
                    
        """
        
        response = self.device.request(self.interface_name + ".setTemperatureInDegrees", [axis, temperature, ])
        self.device.handleError(response)
        return                 

