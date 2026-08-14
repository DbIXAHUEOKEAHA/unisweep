# -*- coding: utf-8 -*-
"""
Interface file for adapting the cryostat dll to python. In order to run this 
on your computer you must first register attoDRYLib.dll (located in the same
directory as this file) with Windows. See the header attoDRYLib.h for function
information and signatures

Created November 11th, 2022

@author: mccambria
"""



from msl.loadlib import Server32
from ctypes import c_float, c_int, c_uint16, byref, POINTER
import ctypes


class attoDRYLib32_server(Server32):

    def __init__(self, host, port, **kwargs):
        super(attoDRYLib32_server, self).__init__('attoDRYLib.dll', 'cdll', host, port)
        self.lib.AttoDRY_Interface_begin.argtypes = [c_uint16]
    
    def AttoDRY_Interface_begin(self):
        device = c_uint16(10)
        msg = self.lib.AttoDRY_Interface_begin(device)
        return msg
    
    def AttoDRY_Interface_isDeviceConnected(self):
        val = c_int(3)
        _ = self.lib.AttoDRY_Interface_isDeviceConnected(byref(val))
        return val.value
    
    def AttoDRY_Interface_isDeviceInitialised(self):
        val = c_int(3)
        _ = self.lib.AttoDRY_Interface_isDeviceInitialised(byref(val))
        return val.value

    def AttoDRY_Interface_Connect(self, com_port):
        com_port = ctypes.c_char_p(com_port)
        return self.lib.AttoDRY_Interface_Connect(com_port)

    def AttoDRY_Interface_Disconnect(self):
        return self.lib.AttoDRY_Interface_Disconnect()
    
    def AttoDRY_Interface_end(self):
        return self.lib.AttoDRY_Interface_end()
    
    def AttoDRY_Interface_get4KStageTemperature(self):
        val = c_float()
        _ = self.lib.AttoDRY_Interface_get4KStageTemperature(byref(val))
        return val.value
    
    
    