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

class AttoDry2100():
    
    def __init__(self, adress):
            
        self.cryo = ct.CDLL(path_to_dll)
        self.running  = ct.c_int(0)
        self.userTemp = ct.c_float()
        self._userField = ct.c_float()
        self.sampleTemp = ct.c_float()
        self.cryoField = ct.c_float()
        self.isControllingTemp = ct.c_int()
        self.isControllingField = ct.c_int()
        self.VTITemp = ct.c_float(-1.0)
        self._P = ct.c_float(-1.0)
        self._I = ct.c_float(-1.0)
        self._D = ct.c_float(-1.0)
        self.samHeater = ct.c_float(-1.0)
        self.VTIHeater = ct.c_float(-1.0)
        self.cryo.AttoDRY_Interface_begin.argtypes = (ct.c_ushort, )
        #define AttoDRY_Interface_Device_attoDRY1100 0
        #define AttoDRY_Interface_Device_attoDRY2100 1
        #define AttoDRY_Interface_Device_attoDRY800 2
        self.cryo.AttoDRY_Interface_begin(ct.c_ushort(1))
        self.cryo.AttoDRY_Interface_Connect.argtypes = (ct.c_char_p, )
        bytes_adress = bytes(adress, encoding='utf8')
        self.cryo.AttoDRY_Interface_Connect(ct.c_char_p(bytes_adress))
        self.cryo.AttoDRY_Interface_isDeviceInitialised.argtypes = (ct.POINTER(ct.c_int), )
        self.cryo.AttoDRY_Interface_isDeviceInitialised(ct.byref(self.running))
        
        self.set_options = ['Temp', 'Field', 'ToggleTemp', 'ToggleField', 'P', 'I', 'D']
        self.get_options = ['Temp', 'Field', 'UserTemperaure', 'UserField', 'ToggleTemp', 'ToggleField', 'VTI_Temp', 'P', 'I', 'D', 'Sam_Heater', 'VTI_Heater']
        self.sweepable = [True, True, False, False, False, False, True, False, False, False, False, False]
        
        self.eps = [0.03, 0.001, 0.1, 0.001, None, None, 0.1, None, None, None, None, None]
        self.maxspeed = [None, None, None, None, None, None, None, None, None, None, None, None]
               
    def Temp(self):
        #get sample temperature
        self.cryo.AttoDRY_Interface_getSampleTemperature(ct.byref(self.sampleTemp))
        T = self.sampleTemp.value
        T = float(T)
        return T
    
    def Field(self):
        #get cryostat magnetic field
        self.cryo.AttoDRY_Interface_getMagneticField(ct.byref(self.cryoField))
        H = self.cryoField.value
        H = float(H)
        return H
    
    def ToggleTemp(self):
        #get value if cryostat is controlling sample temperature
        self.cryo.AttoDRY_Interface_isControllingTemperature(ct.byref(self.isControllingTemp))
        ans = self.isControllingTemp.value
        ans = bool(ans)
        return ans
    
    def ToggleField(self):
        #get value if cryostat is controlling Field
        self.cryo.AttoDRY_Interface_isControllingField(ct.byref(self.isControllingField))
        ans = self.isControllingField.value
        ans = bool(ans)
        return ans
    
    def UserTemperature(self):
        #get user temperature
        self.cryo.AttoDRY_Interface_getUserTemperature(ct.byref(self.userTemp))
        T = self.userTemp.value
        T = float(T)
        return T
    
    def set_ToggleTemp(self, value):
        #toggling\untoggling sample temp
        #0 - Untoggle, 1 - Toggle
        value = bool(value)
        print(f'Toggling? {self.ToggleTemp()}, set: {value}')
        
        def toggle(value):
            self.cryo.AttoDRY_Interface_toggleFullTemperatureControl.argtypes = (ct.c_ushort, )
            self.cryo.AttoDRY_Interface_toggleFullTemperatureControl(ct.c_ushort(value))
        
        t = self.ToggleTemp()
        
        if value and t:
            pass
        elif value and not t:
            toggle(1)
        elif not value and not t:
            pass
        elif not value and t:
            toggle(0)
    
    def set_ToggleField(self, value):
        #toggling\untoggling magnetic field
        #0 - Untoggle, 1 - Toggle
        value = bool(value)
        print(f'Toggling? {self.ToggleField()}, set: {value}')
        
        def toggle(value):
            self.cryo.AttoDRY_Interface_toggleMagneticFieldControl.argtypes = (ct.c_ushort, )
            self.cryo.AttoDRY_Interface_toggleMagneticFieldControl(ct.c_ushort(value))
        

        if value and self.ToggleField():
            pass
        elif value and not self.ToggleField():
            toggle(1)
        elif not value and not self.ToggleField():
            pass
        elif not value and self.ToggleField():
            toggle(0)
    
    def UserField(self):
        #get user temperature
        self.cryo.AttoDRY_Interface_getUserTemperature(ct.byref(self._userField))
        H = self._userField.value
        H = float(H)
        return H
    
    def VTI_Temp(self):
        #get sample temperature
        self.cryo.AttoDRY_Interface_getVtiTemperature(ct.byref(self.VTITemp))
        T = self.VTITemp.value
        T = float(T)
        return T
    
    def P(self):
        #get proportional gain
        self.cryo.AttoDRY_Interface_getProportionalGain(ct.byref(self._P))
        P = self._P.value
        P = float(P)
        return P
    
    def I(self):
        #get integral gain
        self.cryo.AttoDRY_Interface_getIntegralGain(ct.byref(self._I))
        I = self._I.value
        I = float(I)
        return I
    
    def D(self):
        #get derivative gain
        self.cryo.AttoDRY_Interface_getDerivativeGain(ct.byref(self._D))
        D = self._D.value
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
        self.cryo.AttoDRY_Interface_getVtiHeaterPower(ct.byref(self.VTIHeater))
        VH = self.VTIHeater.value
        VH = float(VH)
        return VH
    
    def set_Temp(self, value: float, speed: float = None):
        #set user temperature
        self.userTemp = ct.c_float(value)
        self.cryo.AttoDRY_Interface_setUserTemperature(self.userTemp)
        if not self.ToggleTemp():
            print('Temperature was not toggled, now controlling')
            self.set_ToggleTemp(True)
        
    def set_Field(self, value: float, speed: float = None):
        #set user temperature
        self._userField = ct.c_float(value)
        self.cryo.AttoDRY_Interface_setUserMagneticField(self._userField)
        if not self.ToggleField():
            print('Field was not toggled, now controlling')
            self.set_ToggleField(True)
        
        
    def set_P(self, value: float):
        #set proportional gain
        self.P = ct.c_float(value)
        self.cryo.AttoDRY_Interface_setProportionalGain(self.P)
        
    def set_I(self, value: float):
        #set integral gain
        self.I = ct.c_float(value)
        self.cryo.AttoDRY_Interface_setIntegralGain(self.I)
        
    def set_D(self, value: float):
        #set derivative gain
        self.D = ct.c_float(value)
        self.cryo.AttoDRY_Interface_setDerivativeGain(self.D)
        
    def error_status(self):
        length = 500
        ErrorStatus = ct.create_string_buffer(length)
        l = ct.c_int(length)
        self.cryo.AttoDRY_Interface_getAttodryErrorStatus(ct.byref(ErrorStatus), l)
        return ErrorStatus.value.decode('utf-8')
        
    def downloadSampleTemperatureSensorCalibrationCurve(self, savepath):
        Savepath = savepath.encode('utf-8')
        self.cryo.AttoDRY_Interface_downloadSampleTemperatureSensorCalibrationCurve(ct.c_char_p(Savepath).value)

    def close(self):
        self.cryo.AttoDRY_Interface_Disconnect()

        #self.cryo.AttoDRY_Interface_end()
        
        
def main():
    device = AttoDry2100(adress='COM4')
    try:
        print(device.error_status())
        #device.set_Temp(4)
        #device.set_ToggleField(1)
        #device.set_Field(0.01)
    except Exception as ex:
        print(f'Exception happened initializing AttoDry2100: {ex}')
    finally:
        device.close()

if __name__ == '__main__':
    main()
    
        
        