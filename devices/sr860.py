from pymeasure.instruments.srs import SR860
from pymeasure.instruments.validators import strict_discrete_set, \
    truncated_discrete_set, truncated_range

import pyvisa as visa

rm = visa.ResourceManager()

# Write command to a device and get it's output
def get(device, command):
    '''device = rm.open_resource() where this function gets all devices initiaals such as adress, baud_rate, data_bits and so on; 
    command = string Standart Commands for Programmable Instruments (SCPI)'''
    #return np.round(np.random.random(1), 1) #to test the program without device it would return random numbers
    return device.query(command)

class my_SR860(SR860):
    
    from pymeasure.instruments import Instrument
    
    xnoize = Instrument.measurement("OUTP? 8",
                               """ Reads the Xnoise value in Volts """
                               )
    
    ynoize = Instrument.measurement("OUTP? 9",
                               """ Reads the Xnoise value in Volts """
                               )
    
    FFT = Instrument.measurement("FCRY?",
                               """ Reads the amplitude of FFT on the cursor position """
                               )
    
    DC_bias = Instrument.control(
        "SOFF?", "SOFF %0.9e",
        """A floating property that represents the lock-in DC bias offset in Volts
        This property can be set.""")
        
    IDN = Instrument.measurement("*IDN?",
                               """ Reads the Identification """
                               )

    SENSITIVITIES = [
        1e-9, 2e-9, 5e-9, 10e-9, 20e-9, 50e-9, 100e-9, 200e-9,
        500e-9, 1e-6, 2e-6, 5e-6, 10e-6, 20e-6, 50e-6, 100e-6,
        200e-6, 500e-6, 1e-3, 2e-3, 5e-3, 10e-3, 20e-3,
        50e-3, 100e-3, 200e-3, 500e-3, 1
    ][::-1]

    sensitivity = Instrument.control(
        "SCAL?", "SCAL %d",
        """ A floating point property that controls the sensitivity in Volts,
        which can take discrete values from 2 nV to 1 V. Values are truncated
        to the next highest level if they are not exact. """,
        validator=truncated_discrete_set,
        values=SENSITIVITIES,
        map_values=True
    )
    
    INPUT_FILTER = ['Off', 'On']
    
    filter_synchronous = Instrument.control(
        "SYNC?", "SYNC %d",
        """A string property that represents the synchronous filter.
        This property can be set. Allowed values are:{}""".format(INPUT_FILTER),
        validator=strict_discrete_set,
        values=INPUT_FILTER,
        map_values=True
    )
    
class sr860():

    def __init__(self, adress='GPIB0::3::INSTR'):

        self.sr860 = my_SR860(adress)
        
        self.set_options = ['amplitude', 'frequency', 'phase', 'sensitivity', 
                            'time_constant', 'input_range', 'low_pass_filter_slope', 'synchronous_filter_status',
                            'AUX1_output', 'AUX2_output', 'AUX3_output', 'AUX4_output', 'dc_bias', 'Write']

        self.get_options = ['x', 'y', 'r', 'Θ', 'xnoize', 'ynoize', 'FFT', 'sensitivity', 
                            'time_constant', 'input_range', 'low_pass_filter_slope', 'synchronous_filter_status',
                            'AUX1_input', 'AUX2_input', 'AUX3_input', 'AUX4_input', 
                            'amplitude', 'frequency', 'phase', 'dc_bias', 'Read']
        
        self.SENSITIVITIES = [
            1e-9, 2e-9, 5e-9, 10e-9, 20e-9, 50e-9, 100e-9, 200e-9,
            500e-9, 1e-6, 2e-6, 5e-6, 10e-6, 20e-6, 50e-6, 100e-6,
            200e-6, 500e-6, 1e-3, 2e-3, 5e-3, 10e-3, 20e-3,
            50e-3, 100e-3, 200e-3, 500e-3, 1
        ]
        self.TIME_CONSTANTS = [
            1e-6, 3e-6, 10e-6, 30e-6, 100e-6, 300e-6, 1e-3, 3e-3, 10e-3,
            30e-3, 100e-3, 300e-3, 1, 3, 10, 30, 100, 300, 1e3,
            3e3, 10e3, 30e3
        ]
        self.ON_OFF_VALUES = ['0', '1']
        self.SCREEN_LAYOUT_VALUES = ['0', '1', '2', '3', '4', '5']
        self.EXPANSION_VALUES = ['0', '1', '2,']
        self.CHANNEL_VALUES = ['OCH1', 'OCH2']
        self.OUTPUT_VALUES = ['XY', 'RTH']
        self.INPUT_TIMEBASE = ['AUTO', 'IN']
        self.INPUT_DCMODE = ['COM', 'DIF', 'common', 'difference']
        self.INPUT_REFERENCESOURCE = ['INT', 'EXT', 'DUAL', 'CHOP']
        self.INPUT_REFERENCETRIGGERMODE = ['SIN', 'POS', 'NEG', 'POSTTL', 'NEGTTL']
        self.INPUT_REFERENCEEXTERNALINPUT = ['50OHMS', '1MEG']
        self.INPUT_SIGNAL_INPUT = ['VOLT', 'CURR', 'voltage', 'current']
        self.INPUT_VOLTAGE_MODE = ['A', 'A-B']
        self.INPUT_COUPLING = ['AC', 'DC']
        self.INPUT_SHIELDS = ['Float', 'Ground']
        self.INPUT_RANGE = ['1V', '300M', '100M', '30M', '10M']
        self.INPUT_GAIN = ['1MEG', '100MEG']
        self.INPUT_FILTER = ['Off', 'On']
        
        self.loggable = ['IDN', 'sensitivity', 'time_constant', 'frequency', 'phase',
                         'low_pass_filter_slope', 'synchronous_filter_status', 'dcmode', 
                         'reference_source', 'reference_triggermode', 'reference_externalinput',
                         'input_signal', 'input_voltage_mode', 'input_coupling', 'input_shields',
                         'input_range', 'input_current_gain', 'timebase', 'freq_ext', 
                         'freq_detected', 'signal_strength_indicator', 'noise_bandwidth']

    def IDN(self):
        return self.sr860.IDN
    
    def Write(self):
        return self.Read()
    
    def Read(self):
        device = rm.open_resource(
            self.adress)
        answer = device.read()
        device.close()
        return answer

    def x(self):
        return self.sr860.x

    def y(self):
        return self.sr860.y

    def r(self):
        return self.sr860.magnitude

    def Θ(self):
        return self.sr860.theta
    
    def FFT(self):
        return self.sr860.FFT
    
    def xnoize(self):
        return self.sr860.xnoize
    
    def ynoize(self):
        return self.sr860.ynoize

    def frequency(self):
        return self.sr860.frequency

    def phase(self):
        return self.sr860.phase

    def amplitude(self):
        return self.sr860.sine_voltage

    def sensitivity(self):
        return self.sr860.sensitivity

    def time_constant(self):
        return self.sr860.time_constant
    
    def input_range(self):
        return self.sr860.input_range

    def low_pass_filter_slope(self):
        return self.sr860.filter_slope

    def synchronous_filter_status(self):
        return self.sr860.filter_synchronous

    def AUX1_input(self):
        return self.sr860.aux_in_1

    def AUX2_input(self):
        return self.sr860.aux_in_2

    def AUX3_input(self):
        return self.sr860.aux_in_3

    def AUX4_input(self):
        return self.sr860.aux_in_4
    
    def dc_bias(self):
        return self.sr860.DC_bias
    
    def set_write(self, value):
        device = rm.open_resource(
            self.adress)
        device.write(value)
        device.close()

    def set_frequency(self, value=30.0):
        self.sr860.frequency = value

    def set_phase(self, value=0.0):
        self.sr860.phase = value

    def set_amplitude(self, value=0.5):
        self.sr860.sine_voltage = value

    def set_sensitivity(self, value=24):
        self.sr860.sensitivity = value

    def set_time_constant(self, value=19):
        self.sr860.time_constant = value
        
    def set_input_range(self, value = 3):
        self.sr830.input_range = value

    def set_low_pass_filter_slope(self, value=3):
        self.sr860.filter_slope = value

    def set_synchronous_filter_status(self, value=0):
        self.sr860.filter_synchronous = value

    def set_AUX1_output(self, value=0):
        self.sr860.aux_out_1 = value

    def set_AUX2_output(self, value=0):
        self.sr860.aux_out_2 = value

    def set_AUX3_output(self, value=0):
        self.sr860.aux_out_3 = value

    def set_AUX4_output(self, value=0):
        self.sr860.aux_out_4 = value
        
    def set_dc_bias(self, value):
        self.sr860.DC_bias = value
        
    def screen_layout(self):
        return self.sr860.screen_layout
    
    def dcmode(self):
        return self.sr860.dcmode
    
    def reference_source(self):
        return self.sr860.reference_source
    
    def reference_triggermode(self):
        return self.sr860.reference_triggermode
    
    def reference_externalinput(self):
        return self.sr860.reference_externalinput
    
    def input_signal(self):
        return self.sr860.input_signal
    
    def input_voltage_mode(self):
        return self.sr860.input_voltage_mode
    
    def input_coupling(self):
        return self.sr860.input_coupling
    
    def input_shields(self):
        return self.sr860.input_shields
    
    def input_current_gain(self):
        return self.sr860.input_current_gain
    
    def timebase(self):
        return self.sr860.gettimebase
    
    def freq_ext(self):
        return self.sr860.extfreqency
    
    def freq_detected(self):
        return self.sr860.detectedfrequency
    
    def signal_strength_indicator(self):
        return self.sr860.get_signal_strength_indicator
    
    def noise_bandwidth(self):
        return self.sr860.get_noise_bandwidth
    
    
        
def main():
    device = sr860('GPIB0::2::INSTR')
    print(device.frequency())
    loggable = device.loggable
    for param in loggable:
        print(f'{param} = {getattr(device, param)()}')
    
if __name__ == '__main__':
    main()
    