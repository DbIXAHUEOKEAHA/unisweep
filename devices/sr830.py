from pymeasure.instruments.srs import SR830

import pyvisa as visa

rm = visa.ResourceManager()

# Write command to a device and get it's output
def get(device, command):
    '''device = rm.open_resource() where this function gets all devices initiaals such as adress, baud_rate, data_bits and so on; 
    command = string Standart Commands for Programmable Instruments (SCPI)'''
    #return np.round(np.random.random(1), 1) #to test the program without device it would return random numbers
    return device.query(command)

class my_SR830(SR830):
    
    from pymeasure.instruments import Instrument
    
    IDN = Instrument.measurement("*IDN?",
                               """ Reads the Identification """
                               )

class sr830():

    def __init__(self, adress='GPIB0::3::INSTR'):

        self.sr830 = my_SR830(adress)
        self.sr830.reset_buffer()
        self.adress = adress
        
        self.set_options = ['amplitude', 'frequency', 'phase', 'sensitivity', 
                            'time_constant', 'low_pass_filter_slope', 'synchronous_filter_status',
                            'AUX1_output', 'AUX2_output', 'AUX3_output', 'AUX4_output', 'Write']

        self.get_options = ['x', 'y', 'r', 'Θ', 'sensitivity', 
                            'time_constant', 'low_pass_filter_slope', 'synchronous_filter_status',
                            'AUX1_input', 'AUX2_input', 'AUX3_input', 'AUX4_input', 
                            'amplitude', 'frequency', 'phase', 'Read']
        
        self.loggable = ['IDN', 'sample_frequency', 'Θ', 'sensitivity', 'time_constant', 
                         'frequency', 'low_pass_filter_slope', 'X_offset_percent', 'X_expansion_value', 
                         'Y_offset_percent', 'Y_expansion_value', 'synchronous_filter_status', 
                         'amplifier_status', 'error_status', 'input_config', 
                         'input_grounding', 'input_coupling', 'input_notch_config', 'ref_source', 
                         'ref_source_trig']
        
    def IDN(self):
        answer = self.sr830.IDN
        if type(answer) != list:
            answer = self.sr830.IDN
            if type(answer) != list:
                answer = 'Error in buffer'
        return answer
    
    def Write(self):
        return self.Read()
    
    def Read(self):
        device = rm.open_resource(
            self.adress)
        answer = device.read()
        device.close()
        return answer

    def x(self):
        return self.sr830.x

    def y(self):
        return self.sr830.y

    def r(self):
        return self.sr830.magnitude

    def Θ(self):
        return self.sr830.theta

    def frequency(self):
        return self.sr830.frequency

    def phase(self):
        return self.sr830.phase

    def amplitude(self):
        return self.sr830.sine_voltage

    def sensitivity(self):
        return self.sr830.sensitivity

    def time_constant(self):
        return self.sr830.time_constant

    def low_pass_filter_slope(self):
        return self.sr830.filter_slope

    def synchronous_filter_status(self):
        return self.sr830.filter_synchronous

    def AUX1_input(self):
        return self.sr830.aux_in_1

    def AUX2_input(self):
        return self.sr830.aux_in_2

    def AUX3_input(self):
        return self.sr830.aux_in_3

    def AUX4_input(self):
        return self.sr830.aux_in_4
    
    def set_write(self, value):
        device = rm.open_resource(
            self.adress)
        device.write(value)
        device.close()

    def set_frequency(self, value=30.0):
        self.sr830.frequency = value

    def set_phase(self, value=0.0):
        self.sr830.phase = value

    def set_amplitude(self, value=0.5):
        self.sr830.sine_voltage = value

    def set_sensitivity(self, value=24):
        self.sr830.sensitivity = value

    def set_time_constant(self, value=19):
        self.sr830.time_constant = value

    def set_low_pass_filter_slope(self, value=3):
        self.sr830.filter_slope = value

    def set_synchronous_filter_status(self, value=0):
        self.sr830.filter_synchronous = value

    def set_AUX1_output(self, value=0):
        self.sr830.aux_out_1 = value

    def set_AUX2_output(self, value=0):
        self.sr830.aux_out_2 = value

    def set_AUX3_output(self, value=0):
        self.sr830.aux_out_3 = value

    def set_AUX4_output(self, value=0):
        self.sr830.aux_out_4 = value
        
    def sample_frequency(self):
        return self.sr830.sample_frequency
    
    def X_offset_percent(self):
        return self.sr830.get_scaling('X')[0]
    
    def X_expansion_value(self):
        return self.sr830.get_scaling('X')[1]
    
    def Y_offset_percent(self):
        return self.sr830.get_scaling('Y')[0]
    
    def Y_expansion_value(self):
        return self.sr830.get_scaling('Y')[1]
    
    def amplifier_status(self):
        return self.sr830.lia_status
    
    def error_status(self):
        return self.sr830.err_status
    
    def input_config(self):
        return self.sr830.input_config
    
    def input_grounding(self):
        return self.sr830.input_grounding
    
    def input_coupling(self):
        return self.sr830.input_coupling
    
    def input_notch_config(self):
        return self.sr830.input_notch_config
    
    def ref_source(self):
        return self.sr830.reference_source
    
    def ref_source_trig(self):
        return self.sr830.reference_source_trigger
        
def main():
    device = sr830('GPIB0::1::INSTR')
    loggable = device.loggable
    for param in loggable:
        print(f'{param} = {getattr(device, param)()}')

    
if __name__ == '__main__':
    main()        
        