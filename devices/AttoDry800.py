# -*- coding: utf-8 -*-

# Example of how to use the attoDRYDLL in Python 3.7. This example is done using an attoDRY2100std with a 64bit python.
# Please ensure LV runtime environment 16 32bit and LV VISA are installed (the DLL relies on both)
# Ensure that the Cryostat can be properly connected using the 'attoDRY LabView Interface'.exe. Disconnect to free the COM port.



# here you can read more about Python ctypes to call C functions as it's used extensively in this example:
# https://docs.python.org/3/library/ctypes.html
# Examples
# https://pgi-jcns.fz-juelich.de/portal/pages/using-c-from-python.html
#

#The following library is written by Mikhail Kravtsov based on the example provided by the AttoDry support and is integrated with UniSweep. https://github.com/DbIXAHUEOKEAHA/NUS_experiment

import ctypes as ct
import time
import os

if not __name__ == '__main__':
    path_to_dll = r"devices\attoDRY800_example\01 DLLs for different Cryostat Versions\standard\64 bit\AttoDryInterfaceLib64bit.dll"
else:
    path_to_dll = r"attoDRY800_example\01 DLLs for different Cryostat Versions\standard\64 bit\AttoDryInterfaceLib64bit.dll"

lib = ct.CDLL(path_to_dll)

class AttoDry800():
    
    def __init__(self, adress):
            
        self.cryo = ct.CDLL(path_to_dll)
        self.running  = ct.c_int(0)
        self.userTemp = ct.c_float(-1.0)
        self.sampleTemp = ct.c_float(-1.0)
        self.VTITemp = ct.c_float(-1.0)
        self.P = ct.c_float(-1.0)
        self.O = ct.c_float(-1.0)
        self.D = ct.c_float(-1.0)
        self.samHeater = ct.c_float(-1.0)
        self.VTIHeater = ct.c_float(-1.0)
        self.cryo.AttoDRY_Interface_begin.argtypes = (ct.c_ushort, )
        #define AttoDRY_Interface_Device_attoDRY1100 0
        #define AttoDRY_Interface_Device_attoDRY2100 1
        #define AttoDRY_Interface_Device_attoDRY800 2
        self.cryo.AttoDRY_Interface_begin(ct.c_ushort(2))
        self.cryo.AttoDRY_Interface_Connect.argtypes = (ct.c_char_p, )
        bytes_adress = bytes(adress, encoding = 'utf-8')
        self.cryo.AttoDRY_Interface_Connect(ct.c_char_p(bytes_adress))
        self.cryo.AttoDRY_Interface_isDeviceInitialised.argtypes = (ct.POINTER(ct.c_int), )
        self.cryo.AttoDRY_Interface_isDeviceInitialised(ct.byref(self.running))
        
        self.set_options = ['Temp', 'P', 'I', 'D']
        self.get_options = ['Temp', 'VTI_Temp', 'P', 'I', 'D', 'Sam_Heater', 'VTI_Heater']
        
        self.eps = [0.25, None, None, None]
        
    def Temp(self):
        #get sample temperature
        self.cryo.AttoDRY_Interface_getSampleTemperature(ct.byref(self.sampleTemp))
        T = self.sampleTemp.value
        T = float(T)
        return T
    
    def VTI_Temp(self):
        #get sample temperature
        self.cryo.AttoDRY_Interface_getVTITemperature(ct.byref(self.VTITemp))
        T = self.VTITemp.value
        T = float(T)
        return T
    
    def P(self):
        #get proportional gain
        self.cryo.AttoDRY_Interface_getProportionalGain(ct.byref(self.P))
        P = self.P.value
        P = float(P)
        return P
    
    def I(self):
        #get integral gain
        self.cryo.AttoDRY_Interface_getIntegralGain(ct.byref(self.I))
        I = self.I.value
        I = float(I)
        return I
    
    def D(self):
        #get derivative gain
        self.cryo.AttoDRY_Interface_getDerivativeGain(ct.byref(self.D))
        D = self.D.value
        D = float(D)
        return D
    
    def Sam_Heater(self):
        #get sample heater power
        self.cryo.AttoDRY_Interface_getSampleHeaterPower(ct.byref(self.samHeater))
        SH = self.samHeater.value
        SH = float(SH)
        return SH
    
    def VTI_Heater(self):
        #get sample heater power
        self.cryo.AttoDRY_Interface_getVTIHeaterPower(ct.byref(self.VTIHeater))
        VH = self.VTIHeater.value
        VH = float(VH)
        return VH
    
    def set_Temp(self, value: float, speed: float = None):
        #set user temperature
        self.userTemp = ct.c_float(value)
        self.cryo.AttoDRY_Interface_setUserTemperature(self.userTemp)
        
    def set_P(self, value: float, speed: float = None):
        #set proportional gain
        self.P = ct.c_float(value)
        self.cryo.AttoDRY_Interface_setProportionalGain(self.P)
        
    def set_I(self, value: float, speed: float = None):
        #set integral gain
        self.I = ct.c_float(value)
        self.cryo.AttoDRY_Interface_setIntegralGain(self.I)
        
    def set_D(self, value: float, speed: float = None):
        #set derivative gain
        self.D = ct.c_float(value)
        self.cryo.AttoDRY_Interface_setDerivativeGain(self.D)
        
        
        