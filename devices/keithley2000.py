from pymeasure.instruments.keithley import Keithley2000

class keithley2000():
    def __init__(self, adress):
        self.adress = adress
        self.meter = Keithley2000(adress)
        
        self.set_options = ['Volt_DC_range', 'Volt_AC_range', 'Curr_DC_range', 'Curr_AC_range',
                            'Res_2W_range', 'Res_4W_range']
        self.get_options = ['Volt_DC', 'Volt_AC', 'Curr_DC', 'Curr_AC', 'Res_2W', 'Res_4W', 'Period',
                            'Frequency', 'Temperature']
        '''
        self.loggable = ['Mode', 'Curr_DC_range', 'Curr_DC_reference', 'Curr_DC_NPLC',
                         'Curr_AC_range', 'Curr_AC_reference', 'Curr_AC_NPLC', 'Curr_AC_bandwidth', 
                         'Volt_DC_range', 'Volt_DC_reference', 'Volt_DC_NPLC',
                         'Volt_AC_range', 'Volt_AC_reference', 'Volt_AC_NPLC', 'Volt_AC_bandwidth',
                         'Res_2W_range', 'Res_2W_reference', 'Res_2W_NPLC',
                         'Res_4W_range', 'Res_4W_reference', 'Res_4W_NPLC',
                         'Trigger_count', 'Trigger_delay']
        '''
        
    def Volt_DC(self):
        self.meter.mode = 'voltage'
        return self.meter.voltage
    
    def Volt_AC(self):
        self.meter.mode = 'voltage ac'
        return self.meter.voltage
    
    def Curr_DC(self):
        self.meter.mode = 'current'
        return self.meter.current
    
    def Curr_AC(self):
        self.meter.mode = 'current ac'
        
    def Res_2W(self):
        self.meter.mode = 'resistance'
        return self.meter.resistance
        
    def Res_4W(self):
        self.meter.mode = 'resistance 4W'
        return self.meter.resistance
    
    def Period(self):
        self.meter.mode = 'PER'
        return self.meter.period
    
    def Frequency(self):
        self.meter.mode = 'FREQ'
        return self.meter.frequency
    
    def set_Volt_DC_range(self, value=1):
        "[0, 1010]"
        
        self.meter.voltage_range = round(float(value), 2)
        
    def set_Volt_AC_range(self, value = 1):
        "[0, 757.5]"
        
        self.meter.voltage_ac_range = round(float(value), 2)
        
    def set_Curr_DC_range(self, value = 1):
        "[0, 3.1]"
        
        self.meter.current_range = round(float(value), 2)
        
    def set_Curr_AC_range(self, value = 1):
        "[0, 3.1]"
        
        self.meter.current_ac_range = round(float(value), 2)
        
        
    def set_Res_2W_range(self, value = 1):
        "[0, 120e6]"
        
        self.meter.resistance_range = round(float(value), 2)
        
    def set_Res_4W_range(self, value = 1):
        "[0, 120e6]"
        
        self.meter.resistance_4W_range = round(float(value), 2)
        
    def Mode(self):
        return self.meter.mode
    
    def Curr_DC_range(self):
        return self.meter.current_range
    
    def Curr_DC_reference(self):
        return self.meter.current_reference
    
    def Curr_DC_NPLC(self):
        return self.meter.current_nplc
    
    def Curr_AC_range(self):
        return self.meter.current_ac_range
    
    def Curr_AC_reference(self):
        return self.meter.current_ac_reference
    
    def Curr_AC_NPLC(self):
        return self.meter.current_ac_nplc
    
    def Curr_AC_bandwidth(self):
        return self.meter.current_ac_bandwidth
    
    def Volt_DC_range(self):
        return self.meter.voltage_range
    
    def Volt_DC_reference(self):
        return self.meter.voltage_reference
    
    def Volt_DC_NPLC(self):
        return self.meter.voltage_nplc
    
    def Volt_AC_range(self):
        return self.meter.voltage_ac_range
    
    def Volt_AC_reference(self):
        return self.meter.voltage_ac_reference
    
    def Volt_AC_NPLC(self):
        return self.meter.voltage_ac_nplc
    
    def Volt_AC_bandwidth(self):
        return self.meter.voltage_ac_bandwidth
    
    def Res_2W_range(self):
        return self.meter.resistance_range
    
    def Res_2W_reference(self):
        return self.meter.resistance_reference
    
    def Res_2W_NPLC(self):
        return self.meter.resistance_nplc
    
    def Res_4W_range(self):
        return self.meter.resistance_4w_range
    
    def Res_4W_reference(self):
        return self.meter.resistance_4w_reference
    
    def Res_4W_NPLC(self):
        return self.meter.resistance_4w_nplc
    
    def Trigger_count(self):
        return self.meter.trigger_count
    
    def Trigger_delay(self):
        return self.meter.trigger_delay
    
def main():
    device = keithley2000(adress = 'GPIB0::4::INSTR')
    device.set_Volt_DC_range(1)
    r = device.Volt_DC_range()
    print(r)
    
if __name__ == '__main__':
    main()
    
        
        