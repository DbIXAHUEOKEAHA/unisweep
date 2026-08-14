import pyvisa as visa
from time import sleep, time
from pyvisa import constants

rm = visa.ResourceManager()

# Write command to a device and get it's output
def get(device, command):
    '''device = rm.open_resource() where this function gets all devices initiaals such as adress, baud_rate, data_bits and so on; 
    command = string Standart Commands for Programmable Instruments (SCPI)'''
    return device.query(command)

class ami430():
    def __init__(self, adress = 'ASRL12::INSTR'):
        self.adress = adress
        
        self.device = rm.open_resource(self.adress, baud_rate=115200,
                                   data_bits=8, parity=constants.VI_ASRL_PAR_NONE,
                                   stop_bits=constants.VI_ASRL_STOP_ONE,
                                   flow_control=constants.VI_ASRL_FLOW_NONE,
                                   write_termination='\n', read_termination='\n')
        
        #self.AMI430 = AMI430(self.adress)
        
        self.set_options = ['field', 'current', 'ramp_field_speed', 'ramp_current_speed', 'voltage_lim', 'to_zero']
        self.sweepable = [True, True, False, False, False]
        self.maxspeed = [0.0357, 0.05, None, None, None]
        self.eps = [0.01, 0.01, None, None, None]
        
        self.get_options = ['field', 'current', 'ramp_field_speed', 'ramp_current_speed', 'voltage_lim', 'coil_const', 'supply_current', 'state']
        
        self.loggable = ['voltage_lim', 'coil_const', 'state']
        
    def set_field(self, value, speed = None):
        if speed == None:
            self.ramp_to_field(value, self.maxspeed[self.set_options.index('field')])
        elif speed == 'SetGet':
            speed = self.ramp_field_speed()
            self.ramp_to_field(value, speed)
        else:
            self.ramp_to_field(value, abs(min(speed, self.maxspeed[self.set_options.index('field')])))
            
    def set_to_zero(self, *args, **kwargs):
        self.to_zero()
            
    def set_current(self, value, speed = None):
        if speed == None:
            self.ramp_to_current(value, self.maxspeed[self.set_options.index('current')])
        elif speed == 'Setget':
            speed = self.ramp_current_speed()
            self.ramp_to_current(value, speed)
        else:
            self.ramp_to_current(value, abs(min(speed, self.maxspeed[self.set_options.index('current')])))
            
    def set_target_current(self, value = 0):
        self.device.write(f'CONF:CURR:TARG {round(float(value), 5)}')
        
    def set_target_field(self, value = 0):
        self.device.write(f'CONF:FIELD:TARG {round(float(value), 5)}')
    
    def set_ramp_field_speed(self, value = 0):
        value = abs(value)
        if value > 0.0357:
            value = 0.0357
        self.device.write(f'CONF:RAMP:RATE:FIELD 1,{round(float(value), 5)},1.00')
        
    def set_ramp_current_speed(self, value = 0):
        value = abs(value)
        if value > 0.05:
            value = 0.05
        self.device.write(f'CONF:RAMP:RATE:CURR 1,{round(float(value), 5)}')
        
    def set_voltage_lim(self, value = 1.5):
        self.device.write(f'CONF:VOLT:LIM {round(float(value), 5)}')
        
    def set_coil_const(self, value = 0.1108033):
        self.device.rite(f'CONF:COIL {round(float(value), 6)}')
    
    def coil_const(self):
        answer = get(self.device, 'COIL?')
        return float(answer)
    
    def voltage_lim(self):
        answer = get(self.device, 'VOLT:LIM?')
        return float(answer)
    
    def target_current(self):
        answer = get(self.device, 'CURR:TARG?')
        return float(answer)
    
    def target_field(self):
        answer = get(self.device, 'FIELD:TARG?')
        return float(answer)
    
    def ramp_field_speed(self):
        answer = get(self.device, 'RAMP:RATE:FIELD:1?')
        return float(answer)
    
    def ramp_current_speed(self):
        answer = get(self.device, 'RAMP:RATE:CURR:1?')
        return float(answer)
    
    def field(self):
        answer = get(self.device, 'FIELD:MAG?')
        return float(answer)
        
    def current(self):
        return self.AMI430.magnet_current
    
    def supply_current(self):
        answer = get(self.device, 'CURR:SUPP?')
        return float(answer)
    
    def state(self):
        answer = get(self.device, 'STATE?')
        return float(answer)
    
    def ramp(self):
        self.device.write('RAMP')
        
    def pause(self):
        self.device.write('PAUSE')
        
    def enable_persistent_switch(self):
        """ Enables the persistent switch. """
        self.device.write("PSwitch 1")
        
    def disable_persistent_switch(self):
        """ Disables the persistent switch. """
        self.device.write("PSwitch 0")
        
    def to_zero(self, *args, **kwargs):
        self.set_field(0)
    
    def ramp_to_current(self, value, speed):
        """ Heats up the persistent switch and
        ramps the current with set ramp rate.
        """
        self.enable_persistent_switch()

        self.set_target_current(value)
        
        self.set_ramp_current_speed(speed)

        #self.wait_for_holding()

        self.ramp()

    def ramp_to_field(self, value, speed):
        """ Heats up the persistent switch and
        ramps the current with set ramp rate.
        """
        self.enable_persistent_switch()

        self.set_target_field(value)

        self.set_ramp_field_speed(speed)

        #self.wait_for_holding()

        self.ramp()

    def wait_for_holding(self, should_stop=lambda: False,
                         timeout=800, interval=0.1):
        """
        """
        t = time()
        while self.state != 2 and self.state != 3 and self.state != 8:
            sleep(interval)
            if should_stop():
                return
            if (time() - t) > timeout:
                raise Exception("Timed out waiting for AMI430 switch to warm up.")

    def shutdown(self, ramp_rate=0.0357):
        """ Turns on the persistent switch,
        ramps down the current to zero, and turns off the persistent switch.
        """
        self.enable_persistent_switch()
        self.wait_for_holding()
        self.ramp_rate_current = ramp_rate
        self.zero()
        self.wait_for_holding()
        self.disable_persistent_switch()
        super().shutdown()
    
def main():
    device = ami430()
    device.set_field(0)
    print(device.field())
    
if __name__ == '__main__':
    main()
        
        