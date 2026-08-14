# -*- coding: utf-8 -*-

# Example of how to use the attoDRYDLL in Python 3.7. This example is done using an attoDRY2100std with a 64bit python.
# Please ensure LV runtime environment 16 32bit and LV VISA are installed (the DLL relies on both)
# Ensure that the Cryostat can be properly connected using the 'attoDRY LabView Interface'.exe. Disconnect to free the COM port.



# here you can read more about Python ctypes to call C functions as it's used extensively in this example:
# https://docs.python.org/3/library/ctypes.html
# Examples
# https://pgi-jcns.fz-juelich.de/portal/pages/using-c-from-python.html
#

import ctypes as ct
import time
import os

#import the correct DLL for your cryostat: std, or vector magnet version, for 32 or 64bit python:
#adjust loc=... accordingly.
#ensure that this file is saved locally and not on a network drive!
loc = r".\01 DLLs for different Cryostat Versions\standard\64 bit\AttoDryInterfaceLib64bit.dll"
if not os.path.isfile(loc):
    print("DLL not found")
else:
    print("DLL found")
#%% Load dll:
lib = ct.CDLL(loc)

#%% prepare settings for connection

running  = ct.c_int(0)
userTemp = ct.c_float(-1.0)
sampleTemp = ct.c_float(-1.0)

# copied from the sourcecode of the C Library
#define AttoDRY_Interface_Device_attoDRY1100 0
#define AttoDRY_Interface_Device_attoDRY2100 1
#define AttoDRY_Interface_Device_attoDRY800 2

# lib.AttoDRY_Interface_begin.restype = ct.c_int
# If function has another return value use example above.

lib.AttoDRY_Interface_begin.argtypes = (ct.c_ushort, )
#send 1 for attoDRY2100, 2 for attoDRY800.
err1 = lib.AttoDRY_Interface_begin(ct.c_ushort(1))
print("err1", err1)

lib.AttoDRY_Interface_Connect.argtypes = (ct.c_char_p, )
#adjust COM port
err2 = lib.AttoDRY_Interface_Connect(ct.c_char_p(b"COM4"))  
print("err2", err2)

#try to connect to cryostat:

lib.AttoDRY_Interface_isDeviceInitialised.argtypes = (ct.POINTER(ct.c_int), )
while running.value == 0:
    err3 = lib.AttoDRY_Interface_isDeviceInitialised(ct.byref(running))
    print("err3", err3, "running", running.value)
    time.sleep(1)
    
#The block below reads the user temperature i.e. the setpoint, not the current value. Sets it to 109K and re-reads it.

lib.AttoDRY_Interface_getUserTemperature.argtypes = (ct.POINTER(ct.c_float), )
err4 = lib.AttoDRY_Interface_getUserTemperature(ct.byref(userTemp))
print("err4", err4, "userTemp", userTemp.value)

#read the sample T 6 times
for i in range(6):
    err6 = lib.AttoDRY_Interface_getSampleTemperature(ct.byref(sampleTemp))
    print("err6", err6, "SampleTemp", sampleTemp.value)
    time.sleep(1)

#disconnect the cryostat to free the COM Port:
lib.AttoDRY_Interface_Disconnect()

#lib.AttoDRY_Interface_end()