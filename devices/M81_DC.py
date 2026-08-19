from lakeshore import SSMSystem
from time import sleep
from math import sqrt
import pyvisa
import numpy as np

# Set up GPIB connection to instrument
rm = pyvisa.ResourceManager()

class M81_DC():
    def __init__(self, adress = 'GPIB0::10::INSTR.DC'):
        self.address = adress[:-3]
        self.M81_connection = rm.open_resource(self.address)
        device = SSMSystem(connection=self.M81_connection)
        
        self.smu_source = device.get_source_module(2)
        self.smu_measure = device.get_measure_module(2)
        #self.vm1 = device.get_measure_module(1)
        #self.vm2 = device.get_measure_module(1)
        #self.cm = device.get_measure_module(3)
        
        self.set_options = ['DC_voltage', 'DC_current']
        
        self.get_options = ['DC_measure', 'DC_applied']
        
        #self.loggable = ['time_constant', 'frequency', 'phase',
        #                 'low_pass_filter_slope']
        
        
    '''    
    def DC_VM1_voltage(self):
        ans = self.vm1.get_dc()
        return ans
    
    def DC_VM2_voltage(self):
        ans = self.vm2.get_dc()
        return ans
    
    def DC_CM_current(self):
        ans = self.cm.get_dc()
        return ans
    
    def DC_VS_voltage(self):
        ans = self.vs.get_voltage_amplitude()
        return ans
    
    def DC_BCS_current(self):
        ans = self.bcs.get_current_amplitude()
        return ans
    
    def DC_VS_range(self):
        ans = self.vs.get_voltage_range()
        return ans
    
    def DC_BCS_range(self):
        ans = self.bcs.get_current_range()
        return ans
    
    def DC_VS_limits(self):
        low = self.vs.get_voltage_output_limit_low()
        high = self.vs.get_voltage_output_limit_high()
        return (low, high)
    
    def DC_BCS_limits(self):
        low = self.bcs.get_current_output_limit_low()
        high = self.bcs.get_current_output_limit_high()
        return (low, high)
    
    def DC_VS_compliance_current(self):
        ans = self.vs.get_current_limit()
        return ans
    
    def DC_BCS_compliance_voltage(self):
        ans = self.vs.get_voltage_limit()
        return ans
    
    def set_DC_VS_voltage(self, value, speed = None):
        try:
            low_limit, high_limit = self.DC_VS_limits()
            if value < low_limit:
                value = low_limit
            elif value > high_limit:
                value = high_limit
        except ValueError:
            return
        self.vs.apply_dc_voltage(level = value)
        
    def set_DC_BCS_current(self, value, speed = None):
        try:
            low_limit, high_limit = self.DC_BCS_limits()
            if value < low_limit:
                value = low_limit
            elif value > high_limit:
                value = high_limit
        except ValueError:
            return
        self.bcs.apply_dc_current(level = value)
        
    def set_DC_VS_compliance_current(self, value, speed = None):
        self.vs.set_current_limit(value)
        
    def set_DC_BCS_compliance_voltage(self, value, speed = None):
        self.bcs.set_voltage_limit(value)
    '''
    
    def DC_measure(self):
        ans = self.smu_measure.get_dc()
        return ans
    
    def DC_applied(self):
        mode = self.smu_source.get_source_function()
        if mode == 'CURRENT':
            ans = self.smu_source.get_current_amplitude()
        elif mode == 'VOLTAGE':
            ans = self.smu_source.get_voltage_amplitude()
        else:
            ans = np.nan
        return ans
    
    
    def set_DC_voltage(self, value, speed = None):
        self.smu_source.apply_dc_voltage(level = value)
    
    def set_DC_current(self, value, speed = None):
        self.smu_source.apply_dc_current(level = value)
        
    def close(self):
        self.M81_connection.close()
        
def main():
    device = M81_DC('GPIB0::9::INSTR')
    device.close()
    
if __name__ == '__main__':
    main()