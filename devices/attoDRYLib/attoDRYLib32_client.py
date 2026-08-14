# -*- coding: utf-8 -*-
"""
Interface file for adapting the cryostat dll to python. In order to run this 
on your computer you must first register attoDRYLib.dll (located in the same
directory as this file) with Windows. See the header attoDRYLib.h for function
information and signatures

Created November 11th, 2022

@author: mccambria
"""



from msl.loadlib import Client64



class attoDRYLib32_client(Client64):

    def __init__(self):
        super(attoDRYLib32_client, self).__init__(module32='attoDRYLib32_server')

    def begin(self):
        return self.request32('AttoDRY_Interface_begin')
    
    def is_connected(self):
        return self.request32('AttoDRY_Interface_isDeviceConnected')
    
    def is_initialized(self):
        return self.request32('AttoDRY_Interface_isDeviceInitialised')
    
    def connect(self, com_port):
        return self.request32('AttoDRY_Interface_Connect', com_port)
    
    def disconnect(self):
        return self.request32('AttoDRY_Interface_Disconnect')
    
    def end(self):
        return self.request32('AttoDRY_Interface_end')

    def get_4K_stage_temp(self):
        return self.request32('AttoDRY_Interface_get4KStageTemperature')
    
if __name__ == "__main__":
    
    client = attoDRYLib32_client()
    try:
        print(client.begin())
        address = b"COM3"
        print(client.connect(address))
        print(f"Connected: {client.is_connected()}")
        print(f"Initialized: {client.is_initialized()}")
        print(client.get_4K_stage_temp())
    except Exception as exc:
        print(exc)
    finally: 
        print(client.disconnect())
        print(client.end())
    