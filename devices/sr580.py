import pyvisa as visa
import numpy as np
import time

rm = visa.ResourceManager()

# Write command to a device and get it's output
def get(device, command):
    # return np.round(np.random.random(1), 1)
    return device.query(command)

class sr580():
    def __init__(self, adress = 'COM1'):
        self.device = rm.open_resource(
            adress, write_termination = '\n', read_termination = '\n', 
            baud_rate = 9600)
        
        self.set_options = ['DC_cur', 'compl_volt', 'gain', 'analog_input', 'speed']
        self.get_options = ['DC_cur', 'compl_volt', 'gain', 'analog_input', 'speed']
        
        self.sweepable = [False, False, False, False, False]
        self.eps = [None, None, None, None, None]
        self.maxspeed = [None, None, None, None, None]
        
        self.dict_gain = {1e-9: 'G1nA', 1e-8: 'G10nA', 1e-7: 'G100nA', 1e-6: 'G1uA',
                          1e-5: 'G10uA', 1e-4: 'G100uA', 1e-3: 'G1mA', 1e-2: 'G10mA',
                          5e-2: 'G50mA'} #value in amperes to Z value 
    
    def close(self):
        self.device.close()
    
    def set_DC_cur(self, value: float):
        value = float(value)
        self.device.write('CURR {value}')
        
    def set_compl_volt(self, value: float):
        value = float(value)
        self.device.write('VOLT {value}')
        
    def set_gain(self, value: float = 1e-6):
        
        try:
            value = float(value)
        except ValueError as ve:
            print(f'Exception happened while setting sr580 gain: {ve}. Input value is {value}')
            value = 1e-6
        possible_list = list(self.dict_gain.keys())
        closest_list = np.array(possible_list) - value
        closest_value_idx = np.argmin(closest_list)
        closest_value = list(self.dict_gain.values())[closest_value_idx]
        self.device.write(f'GAIN {closest_value}')
    
    def set_analog_input(self, value):
        if value == 'ON' or value == 'On' or value == 'on' or value == 1:
            value = 'ON'
        elif value == 'OFF' or value == 'Off' or value == 'off' or value == 0:
            value = 'OFF'
        else:
            print(f'Exception happened while setting input gain: possible values are 0 (off) or 1 (on). Input value is {value}')
            value = 'OFF'

        self.device.write(f'INPT {value}')
        
    def set_speed(self, value):
        if value == 'FAST' or value == 'Fast' or value == 'fast' or value == 0:
            value = 'FAST'
        elif value == 'SLOW' or value == 'Slow' or value == 'slow' or value == 1:
            value = 'SLOW'
        else:
            print(f'Exception happened while setting input gain: possible values are 0 (slow) or 1 (fast). Input value is {value}')
            value = 'SLOW'

        self.device.write(f'RESP {value}')
        
    def DC_cur(self):
        ans = get(self.device, 'CURR?')
        try:
            ans = float(ans)
        except ValueError as ve:
            print(f'Exception happened reading SR580 DC_cur: {ve}. Output is {ans}')
            ans = np.nan
        return ans
    
    def compl_volt(self):
        ans = get(self.device, 'VOLT?')
        try:
            ans = float(ans)
        except ValueError as ve:
            print(f'Exception happened reading SR580 compl_volt: {ve}. Output is {ans}')
            ans = np.nan
        return ans
    
    def gain(self):
        ans = get(self.device, 'GAIN?')
        
        for ind, val in enumerate(list(self.dict_gain.values())):
            if ans == val.upper():
                ans = list(self.dict_gain.keys())[ind]
                break
            ans = np.nan
            
        return ans
    
    def analog_input(self):
        ans = get(self.device, 'INPT?')
        
        if ans == 'OFF':
            ans = 0
        elif ans == 'ON':
            ans = 1
        else:
            ans = np.nan
        
        return ans
        
    def speed(self):
        ans = get(self.device, 'RESP?')
        
        if ans == 'SLOW':
            ans = 0
        elif ans == 'FAST':
            ans = 1
        else:
            ans = np.nan
        
        return ans

        