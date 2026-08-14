import pyvisa as visa
import numpy as np
import time

rm = visa.ResourceManager()

# Write command to a device and get it's output
def get(device, command):
    # return np.round(np.random.random(1), 1)
    return device.query(command)

class QDAQ2():
    
    def __init__(self, adress = 'COM14'):
        self.ip = '192.168.1.253'
        self.qdaq = rm.open_resource(
            adress, write_termination = '\n', read_termination = '\n', 
            baud_rate = 921600, send_end = False)
        
    def IDN(self):
        answer = get(self.qdaq, '*IDN?')
        return answer
    
    def Errors(self):
        answer = get(self.qdaq, 'syst:err:all?')
        return answer
    
    def source_range1(self):
        answer = get(self.qdaq, 'sour1:range?')
        return answer

    def set_source_range1(self, value):
        if value == 'low' or value == 'LOW' or value == 'high' or value == 'HIGH':
            val = value
        elif value == 0:
            val = 'low'
        elif value == 1:
            val = 'high'
        else:
            raise Exception(f'Input range is incorrect, input 0 for low, 1 for high. Got {value}')
        self.qdaq.write(f'sour1:range {val}')
        
    def sense_range1(self):
        answer = get(self.qdaq, 'sense1:range?')
        return answer

    def set_sense_range1(self, value):
        if value == 'low' or value == 'LOW' or value == 'high' or value == 'HIGH':
            val = value
        elif value == 0:
            val = 'low'
        elif value == 1:
            val = 'high'
        else:
            raise Exception(f'Input range is incorrect, input 0 for low, 1 for high. Got {value}')
        self.qdaq.write(f'sense1:range {val}')
        
    def filter1(self):
        answer = get(self.qdaq, 'sour1:filt?')
        return answer

    def set_filter1(self, value):
        if value == 'dc' or value == 'DC' or value == 'med' or value == 'MED' or value == 'high' or value == 'HIGH':
            val = value
        elif value == 0:
            val = 'dc'
        elif value == 1:
            val = 'med'
        elif value == 2:
            val = 'high'
        else:
            raise Exception(f'Input filter is incorrect, input 0 for dc, 1 for mediium, 2 for high. Got {value}')
        self.qdaq.write(f'sour1:filt {val}')
    
    def sine_freq1(self):
        answer = get(self.qdaq, 'sour1:sine:freq?')
        return answer
    
    def set_sine_freq1(self, value):
        value = int(value)
        self.qdaq.write(f'sour1:sine:freq {value}')
        
    def slew_dc1(self):
        answer = get(self.qdaq, 'sour1:volt:slew?')
        return answer
    
    def slew_sine1(self):
        answer = get(self.qdaq, 'sour1:sine:slew?')
        return answer
    
    def mode1(self):
        answer = get(self.qdaq, 'sour1:mode?')
        return answer
    
    def set_volt1(self, value):
        self.qdaq.write(f'sour1:volt {value}')
        
    def set_sine_span1(self, value):
        self.qdaq.write(f'sour1:sine:span {value}')
        
    def init1(self):
        self.qdaq.write('sour1:sine:trig:sour imm')
        self.qdaq.write('sour1:sine:init')
    
def main():
    device = QDAQ2()
    device.set_volt1(1)
    device.set_sine_freq1(120)
    device.set_sine_span1(0.1)
    device.init1()
    print(device.Errors())
    
if __name__ == '__main__':
    main()