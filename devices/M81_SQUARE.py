from lakeshore import SSMSystem
from time import sleep
from math import sqrt
import pyvisa

# Set up GPIB connection to instrument
rm = pyvisa.ResourceManager()

class M81_SQUARE():
    def __init__(self, adress = 'GPIB0::10::INSTR.SQ'):
        self.address = adress[:-3]
        self.M81_connection = rm.open_resource(self.address)
        device = SSMSystem(connection=self.M81_connection)
        
        self.bcs = device.get_source_module(1)
        self.vs = device.get_source_module(2)
        self.vm1 = device.get_measure_module(1)
        self.vm2 = device.get_measure_module(2)
        self.cm = device.get_measure_module(3)
        
        self.set_options = ['SQR_VS_voltage', 'SQR_VS_frequency', 'SQR_VS_offset', 'SQR_BCS_current', 'SQR_VS_duty', ]
        
        self.get_options = ['AC_VM1_voltage', 'AC_VM2_voltage', 'AC_CM_current', 'SQR_VS_voltage_offset']
        
        #self.loggable = ['time_constant', 'frequency', 'phase',
        #                 'low_pass_filter_slope']
        
    def AC_VM1_voltage(self):
        ans = self.vm1.get_ac()
        return ans
    
    def AC_VM2_voltage(self):
        ans = self.vm2.get_ac()
        return ans
    
    def AC_CM_current(self):
        ans = self.cm.get_ac()
        return ans
    
    def SQR_VS_voltage(self):
        ans = self.vs.get_voltage_amplitude()
        return ans
    
    def SQR_VS_voltage_offset(self):
        ans = self.vs.get_voltage_offset()
        return ans
    
    def SQR_BCS_current(self):
        ans = self.bcs.get_current_amplitude()
        return ans
    
    def SQR_VS_range(self):
        ans = self.vs.get_voltage_range()
        return ans
    
    def SQR_BCS_range(self):
        ans = self.bcs.get_current_range()
        return ans
    
    def SQR_VS_limits(self):
        low = self.vs.get_voltage_output_limit_low()
        high = self.vs.get_voltage_output_limit_high()
        return (low, high)
    
    def SQR_BCS_limits(self):
        low = self.bcs.get_current_output_limit_low()
        high = self.bcs.get_current_output_limit_high()
        return (low, high)
    
    def SQR_VS_compliance_current(self):
        ans = self.vs.get_current_limit()
        return ans
    
    def SQR_BCS_compliance_voltage(self):
        ans = self.vs.get_voltage_limit()
        return ans
    
    def set_SQR_VS_frequency(self, value, speed = None):
        self.vs.set_frequency(value)
    
    def set_SQR_VS_voltage(self, value, speed = None):
        try:
            low_limit, high_limit = self.SQR_VS_limits()
            if value < low_limit:
                value = low_limit
            elif value > high_limit:
                value = high_limit
        except ValueError:
            return
        

        self.vs.set_excitation_mode(self.vs.device.ExcitationType.VOLTAGE)
        self.vs.set_shape('SQUARE')
        self.vs.set_voltage_amplitude(value)

        self.vs.enable()
        
    def set_SQR_VS_offset(self, value, speed = None):
        
        self.vs.set_voltage_offset(value)
    
    def set_SQR_VS_duty(self, value, speed = None):
        
        self.vs.set_duty(value)
        
    def set_SQR_BCS_frequency(self, value, speed = None):
        self.bcs.set_frequency(value)
        
    def set_SQR_BCS_current(self, value, speed = None):
        try:
            low_limit, high_limit = self.SQR_BCS_limits()
            if value < low_limit:
                value = low_limit
            elif value > high_limit:
                value = high_limit
        except ValueError:
            return
        
        self.bcs.set_excitation_mode('CURRent')
        self.bcs.set_shape('SQUARE')
        self.bcs.set_current_amplitude(value)

        self.bcs.enable()
        
    def set_SQR_BCS_offset(self, value, speed = None):
        
        self.bcs.set_current_offset(value)
        
    def set_SQR_VS_compliance_current(self, value, speed = None):
        self.vs.set_current_limit(value)
        
    def set_SQR_BCS_compliance_voltage(self, value, speed = None):
        self.bcs.set_voltage_limit(value)
        
    def close(self):
        self.M81_connection.close()
        
def main():
    device = M81_SQUARE('GPIB0::10::INSTR.SQ')
    #device.set_SQR_VS_voltage(0)
    device.close()
    
if __name__ == '__main__':
    main()