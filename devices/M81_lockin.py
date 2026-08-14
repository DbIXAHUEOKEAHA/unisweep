from lakeshore import SSMSystem
from time import sleep
from math import sqrt
import pyvisa

# Set up GPIB connection to instrument
rm = pyvisa.ResourceManager()

class M81_lockin():
    def __init__(self, adress = 'GPIB0::10::INSTR.LI'):
        self.address = adress[:-3]
        self.M81_connection = rm.open_resource(self.address)
        device = SSMSystem(connection=self.M81_connection)
        
        self.bcs = device.get_source_module(1)
        self.vs = device.get_source_module(2)
        self.vm1 = device.get_measure_module(1)
        self.vm2 = device.get_measure_module(2)
        self.cm = device.get_measure_module(3)
        
        self.set_options = ['LI1_amplitude', 'LI1_frequency',
                            'LI1_time_constant', 'LI1_low_pass_filter_slope', 'LI1_dc_bias',
                            'LI3_amplitude', 'LI3_frequency',
                            'LI3_time_constant', 'LI3_low_pass_filter_slope', 'LI3_dc_bias']
        
        self.get_options = ['LI1_x', 'LI1_y', 'LI1_r', 'LI1_theta',
                            'LI1_time_constant', 'LI1_low_pass_filter_slope', 
                            'LI2_x', 'LI2_y', 'LI2_r', 'LI2_theta',
                            'LI2_time_constant', 'LI2_low_pass_filter_slope', 
                            'LI3_x', 'LI3_y', 'LI3_r', 'LI3_theta',
                            'LI3_time_constant', 'LI3_low_pass_filter_slope',
                            'LI1_amplitude', 'LI1_frequency', 'LI1_phase', 'LI1_dc_bias',
                            'LI3_amplitude', 'LI3_frequency', 'LI3_phase', 'LI3_dc_bias']
        
        #self.loggable = ['time_constant', 'frequency', 'phase',
        #                 'low_pass_filter_slope']
        
    def LI1_amplitude(self):
        ans = self.bcs.get_current_amplitude()
        return ans

    def LI1_frequency(self):
        ans = self.bcs.get_frequency()
        return ans
    
    def LI1_phase(self):
        ans = self.bcs.get_sync_phase_shift()
        return ans
    
    def LI1_dc_bias(self):
        ans = self.bcs.get_current_offset()
        return ans
    
    def LI3_amplitude(self):
        ans = self.vs.get_voltage_amplitude()
        return ans

    def LI3_frequency(self):
        ans = self.vs.get_frequency()
        return ans
    
    def LI3_phase(self):
        ans = self.vs.get_sync_phase_shift()
        return ans
    
    def LI3_dc_bias(self):
        ans = self.vs.get_voltage_offset()
        return ans
    
    def LI3_time_constant(self):
        ans = self.cm.get_lock_in_time_constant()
        return ans
    
    def LI3_low_pass_filter_slope(self):
        ans = self.cm.get_lock_in_rolloff()
        return ans

    def LI1_time_constant(self):
        ans = self.vm1.get_lock_in_time_constant()
        return ans
    
    def LI1_low_pass_filter_slope(self):
        ans = self.vm1.get_lock_in_rolloff()
        return ans
    
    def LI1_x(self):
        ans = self.vm1.get_lock_in_x()
        return ans
    
    def LI1_y(self):
        ans = self.vm1.get_lock_in_y()
        return ans
    
    def LI1_r(self):
        ans = self.vm1.get_lock_in_r()
        return ans
    
    def LI1_theta(self):
        ans = self.vm1.get_lock_in_theta()
        return ans
    
    def LI2_time_constant(self):
        ans = self.vm2.get_lock_in_time_constant()
        return ans
    
    def LI2_low_pass_filter_slope(self):
        ans = self.vm2.get_lock_in_rolloff()
        return ans
    
    def LI2_x(self):
        ans = self.vm2.get_lock_in_x()
        return ans
    
    def LI2_y(self):
        ans = self.vm2.get_lock_in_y()
        return ans
    
    def LI2_r(self):
        ans = self.vm2.get_lock_in_r()
        return ans
    
    def LI2_theta(self):
        ans = self.vm2.get_lock_in_theta()
        return ans
    
    def LI3_time_constant(self):
        ans = self.cm.get_lock_in_time_constant()
        return ans
    
    def LI3_low_pass_filter_slope(self):
        ans = self.cm.get_lock_in_rolloff()
        return ans
    
    def LI3_x(self):
        ans = self.cm.get_lock_in_x()
        return ans
    
    def LI3_y(self):
        ans = self.cm.get_lock_in_y()
        return ans
    
    def LI3_r(self):
        ans = self.cm.get_lock_in_r()
        return ans
    
    def LI3_theta(self):
        ans = self.cm.get_lock_in_theta()
        return ans
    
    def set_LI1_amplitude(self, value, speed = None):
        #value in amperes
        self.bcs.set_current_amplitude(value)
        
    def set_LI1_frequency(self, value, speed = None):
        self.bcs.set_frequency(value)
        
    def set_LI1_time_constant(self, value, speed = None):
        self.vm1.set_lock_in_time_constant(value)
        
    def set_LI1_low_pass_filter_slope(self, value, speed = None):
        try:
            value = 'R'+int(value)
        except ValueError:
            value = 'R12'
        self.vm1.set_lock_in_rolloff(value)
        
    def set_LI1_dc_bias(self, value, speed = None):
        self.bcs.set_current_offset(value)
        
    def set_LI3_amplitude(self, value, speed = None):
        #value in amperes
        self.vs.set_voltage_amplitude(value)
        
    def set_LI3_frequency(self, value, speed = None):
        self.vs.set_frequency(value)
        
    def set_LI3_time_constant(self, value, speed = None):
        self.cm.set_lock_in_time_constant(value)
        
    def set_LI3_low_pass_filter_slope(self, value, speed = None):
        try:
            value = 'R'+int(value)
        except ValueError:
            value = 'R12'
        self.cm.set_lock_in_rolloff(value)
        
    def set_LI3_dc_bias(self, value, speed = None):
        self.vs.set_voltage_offset(value)

    def close(self):
        self.M81_connection.close()
        
def main():
    device = M81_lockin('GPIB0::10::INSTR')
    loggable = device.loggable
    for param in loggable:
        print(f'{param} = {getattr(device, param)()}')
    
if __name__ == '__main__':
    main()