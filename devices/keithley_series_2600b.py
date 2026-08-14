import pyvisa as visa
from pymeasure.instruments.keithley.keithley2600 import Channel
from pymeasure.instruments import Instrument
from pymeasure.instruments.validators import truncated_range
import numpy as np
import time

rm = visa.ResourceManager()

# Write command to a device and get it's output
def get(device, command):
    # return np.round(np.random.random(1), 1)
    return device.query(command)


class My_Keithley_2600(Instrument):
    def __init__(self, adapter, **kwargs):
        super().__init__(
            adapter,
            "Keithley 2600 SourceMeter",
            **kwargs
        )
        self.ChA = My_Channel(self, 'a')
        self.ChB = My_Channel(self, 'b')

class My_Channel(Channel):

    """
    Auxillary class made to deal with tolerance. Original class allow to source micro, this class allow nano.
    """
    source_current = Instrument.control(
        'source.leveli', 'source.leveli=%.9f',
        """ Property controlling the applied source current """,
        validator=truncated_range,
        values=[-1.5, 1.5]
    )

    compliance_current = Instrument.control(
        'source.limiti', 'source.limiti=%.9f',
        """ Property controlling the source compliance current """,
        validator=truncated_range,
        values=[-1.5, 1.5]
    )

    source_voltage = Instrument.control(
        'source.levelv', 'source.levelv=%.9f',
        """ Property controlling the applied source voltage """,
        validator=truncated_range,
        values=[-200, 200]
    )

    compliance_voltage = Instrument.control(
        'source.limitv', 'source.limitv=%.9f',
        """ Property controlling the source compliance voltage """,
        validator=truncated_range,
        values=[-200, 200]
    )



class keithley_series_2600b():
    
    def __init__(self, adress = 'GPIB0::04::INSTR'):
        self.k26 = My_Keithley_2600(adress)
        
        self.address = adress
        
        self.set_options = ['A_source_current', 'A_compl_current', 'B_source_current', 'B_compl_current',
                            'A_source_voltage', 'A_compl_voltage', 'B_source_voltage', 'B_compl_voltage',
                            'A_NPLC', 'B_NPLC']
        
        self.get_options = ['A_current', 'A_source_current', 'A_compl_current', 'B_current', 'B_source_current', 'B_compl_current',
                            'A_voltage', 'A_source_voltage', 'A_compl_voltage', 'B_voltage', 'B_source_voltage', 'B_compl_voltage', 
                            'A_NPLC', 'B_NPLC']
        
        #self.sweepable = [True, False, True, False, True, False, True, False, False, False]
        #self.maxspeed = [0.01, None, 0.01, None, 5, None, 5, None, None, None]
        
    def open(self):
        self.device = rm.open_resource(
            self.adress)
        
    def FREQ(self):
        #self.freq = self.k26.ChA.line_frequency
        #TODO line frequency command
        self.freq = 50
        
    def A_NPLC(self):
        self.A_nplc = self.k26.ChA.measure_nplc
        return self.A_nplc
    
    def B_NPLC(self):
        self.B_nplc = self.k26.ChB.measure_nplc
        return self.B_nplc
        
    def A_current(self):
        self.cur_A_current = self.k26.ChA.current
        return self.cur_A_current
    
    def B_current(self):
        self.cur_B_current = self.k26.ChB.current
        return self.cur_B_current
        
    def A_source_current(self):
        self.cur_A_source_current = self.k26.ChA.source_current
        return self.cur_A_source_current
    
    def B_source_current(self):
        self.cur_B_source_current = self.k26.ChB.source_current
        return self.cur_B_source_current
    
    def A_compl_current(self):
        return self.k26.ChA.compliance_current
    
    def B_compl_current(self):
        return self.k26.ChB.compliance_current
    
    def A_voltage(self):
        self.cur_A_voltage = self.k26.ChA.voltage
        return self.cur_A_voltage
    
    def B_voltage(self):
        self.cur_B_voltage = self.k26.ChB.voltage
        return self.cur_B_voltage
        
    def A_source_voltage(self):
        self.cur_A_source_voltage = self.k26.ChA.source_voltage
        return self.cur_A_source_voltage
    
    def B_source_voltage(self):
        self.cur_B_source_voltage = self.k26.ChB.source_voltage
        return self.cur_B_source_voltage
    
    def A_compl_voltage(self):
        return self.k26.ChA.compliance_voltage
    
    def B_compl_voltage(self):
        return self.k26.ChB.compliance_voltage
    
    def A_resistance(self):
        return self.k26.ChA.resistance
    
    def B_resistance(self):
        return self.k26.ChB.resistance
    
    def set_A_NPLC(self, value):
        self.k26.ChA.measure_nplc = value
        
    def set_B_NPLC(self, value):
        self.k26.ChB.measure_nplc = value
        
    def set_A_source_current(self, value: float, speed = None):
        self.A_source_current()
        
        self.k26.ChA.source_output = 'ON'
        self.k26.ChA.source_mode = 'current'
        #self.k26.ChA.auto_range_source()
        
        self.k26.ChA.source_current = value
            
    def set_B_source_current(self, value: float, speed = None):
        self.B_source_current()
        
        self.k26.ChB.source_output = 'ON'
        self.k26.ChB.source_mode = 'current'
       # self.k26.ChB.auto_range_source()
        
        self.k26.ChB.source_current = value
            
    def set_A_source_voltage(self, value: float, speed = None):
        self.A_source_voltage()
        
        self.k26.ChA.source_output = 'ON'
        self.k26.ChA.source_mode = 'voltage'
      #  self.k26.ChA.auto_range_source()
        
        self.k26.ChA.source_voltage = value
    def set_B_source_voltage(self, value: float, speed = None):
        self.B_source_voltage()
        
        self.k26.ChB.source_output = 'ON'
        self.k26.ChB.source_mode = 'voltage'
       # self.k26.ChB.auto_range_source()
        
        self.k26.ChB.source_voltage = value
        
def main():
    device = keithley_series_2600b()
    #device.set_A_source_current(-0.00001998)
    
if __name__ == '__main__':
    main()