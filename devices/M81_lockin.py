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
        
        self.smu_source = device.get_source_module(2)
        self.smu_measure = device.get_measure_module(2)
        
        self.set_options = ['LI_current_amplitude', 'LI_voltage_amplitude', 'LI_frequency',
                            'LI_time_constant', 'LI_low_pass_filter_slope', 'LI_dc_current_bias', 'LI_dc_voltage_bias']
        
        self.get_options = ['LI_x', 'LI_y', 'LI_r', 'LI_theta',
                            'LI_time_constant', 'LI_low_pass_filter_slope', 
                            'LI_current_amplitude', 'LI_voltage_amplitude', 'LI_frequency', 'LI_phase', 
                            'LI_dc_current_bias', 'LI_dc_voltage_bias', 'LI_dc_bias_read']
        
        self.loggable = ['LI_time_constant', 'LI_low_pass_filter_slope', 'LI_frequency', 'LI_phase']
        
    def LI_current_amplitude(self):
        ans = self.smu_source.get_current_amplitude()
        return ans
    
    def LI_voltage_amplitude(self):
        ans = self.smu_source.get_voltage_amplitude()
        return ans

    def LI_frequency(self):
        ans = self.smu_source.get_frequency()
        return ans
    
    def LI_phase(self):
        ans = self.smu_source.get_sync_phase_shift()
        return ans
    
    def LI_dc_current_bias(self):
        ans = self.smu_source.get_current_offset()
        return ans
    
    def LI_dc_voltage_bias(self):
        ans = self.smu_source.get_voltage_offset()
        return ans

    def LI_time_constant(self):
        ans = self.smu_measure.get_lock_in_time_constant()
        return ans
    
    def LI_low_pass_filter_slope(self):
        ans = self.smu_measure.get_lock_in_rolloff()
        return ans
    
    def LI_x(self):
        ans = self.smu_measure.get_lock_in_x()
        return ans
    
    def LI_y(self):
        ans = self.smu_measure.get_lock_in_y()
        return ans
    
    def LI_r(self):
        ans = self.smu_measure.get_lock_in_r()
        return ans
    
    def LI_theta(self):
        ans = self.smu_measure.get_lock_in_theta()
        return ans
    
    def LI_dc_bias_read(self):
        ans = self.smu_measure.get_lock_in_dc()
        return ans
    
    def set_LI_current_amplitude(self, value, speed = None):
        #value in amperes
        value *= sqrt(2)
        self.smu_source.set_current_amplitude(value)
        
    def set_LI_voltage_amplitude(self, value, speed = None):
        #value in volts
        value *= sqrt(2)
        self.smu_source.set_voltage_amplitude(value)
        
    def set_LI_frequency(self, value, speed = None):
        self.smu_source.set_frequency(value)
        
    def set_LI_time_constant(self, value, speed = None):
        self.smu_measure.set_lock_in_time_constant(value)
        
    def set_LI_low_pass_filter_slope(self, value, speed = None):
        try:
            value = 'R'+int(value)
        except ValueError:
            value = 'R12'
        self.smu_measure.set_lock_in_rolloff(value)
        
    def set_LI_dc_voltage_bias(self, value, speed = None):
        self.smu_source.set_voltage_offset(value)
        
    def set_LI_dc_current_bias(self, value, speed = None):
        self.smu_source.set_current_offset(value)
        

    def close(self):
        self.M81_connection.close()
        
def main():
    device = M81_lockin('GPIB0::9::INSTR.LI')
    loggable = device.loggable
    for param in loggable:
        print(f'{param} = {getattr(device, param)()}')
    
if __name__ == '__main__':
    main()