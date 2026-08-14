import pyvisa as visa
from pyvisa import constants

rm = visa.ResourceManager()


def get(device, command):
    '''device = rm.open_resource() where this function gets all devices initiaals such as adress, baud_rate, data_bits and so on; 
    command = string Standart Commands for Programmable Instruments (SCPI)'''
    return device.query(command)
    # return np.random.random(1)


class LakeShore336():

    """
    HEATER_RANGE_OFF = '0'
    HEATER_RANGE_ON  = '1'
    HEATER_RANGE_LOW = '1'
    HEATER_RANGE_MED = '2'
    HEATER_RANGE_HIGH = '3'

    CHANNEL_A = 'A'
    CHANNEL_B = 'B'
    CHANNEL_C = 'C'
    CHANNEL_D = 'D'

    CHANNELS = [CHANNEL_A, CHANNEL_B, CHANNEL_C, CHANNEL_D]
    """

    def __init__(self, adress='GPIB0::12::INSTR'):
        self.adress = adress

        self.ch_dict = {1: 'A', 2: 'B', 3: 'C', 4: 'D'}
        self.range_dict = {'off': '0', 'Off': '0', 'OFF': '0', 'low': '1', 'Low': '1', 'LOW': '1',
                           'med': '2', 'Med': '2', 'MED': '2', 'medium': '2', 'Medium': '2',
                           'MEDIUM': '2', 'high': '3', 'High': '3', 'HIGH': '3'}

        if adress.startswith('ASRL'):

            self.ls = rm.open_resource(self.adress, baud_rate=57600,
                                       data_bits=7, parity=constants.VI_ASRL_PAR_ODD,
                                       stop_bits=constants.VI_ASRL_STOP_ONE,
                                       flow_control=constants.VI_ASRL_FLOW_NONE)

        elif adress.startswith('GPIB'):
            self.ls = rm.open_resource(self.adress)

        self.set_options = ['T1', 'T2', 'T3', 'T4', 'speed1', 'speed2', 'led',
                            'heater_range1', 'heater_range2', 'heater_range3',
                            'heater_range4']

        self.get_options = ['T1', 'T2', 'T3', 'T4', 'speed1', 'speed2', 'led',
                            'heater_range1', 'heater_range2', 'heater_range3',
                            'heater_range4', 'tj_temp']
        
        self.sweepable = [True, True, True, True, False, False, False, False, False, False, False, False]
        
        self.eps = [0.005, 0.005, 0.005, 0.005, None, None, None, None, None, None, None, None]
        
        self.loggable = ['IDN', 'T1', 'T2', 'T3', 'T4', 'led',
                            'heater_range1', 'heater_range2', 'heater_range3',
                            'heater_range4', 'tj_temp']

    def IDN(self):
        return get(self.ls, '*IDN?')[:-1]

    def T1(self):
        """
        :return: Returns the temperature of the 1 channel in float, units being Kelvin
        """
        return float(get(self.ls, 'KRDG? A'))

    def T2(self):
        """
        :return: Returns the temperature of the 2 channel in float, units being Kelvin
        """
        return float(get(self.ls, 'KRDG? B'))

    def T3(self):
        """
        :return: Returns the temperature of the 3 channel in float, units being Kelvin
        """
        return float(get(self.ls, 'KRDG? C'))

    def T4(self):
        """
        :return: Returns the temperature of the 4 channel in float, units being Kelvin
        """
        return float(get(self.ls, 'KRDG? D'))
    
    '''
    def Setpoint_1(self):
        """
        Returns the setpoint on Ch1 
        """
        answer = float(get(self.ls, 'SETP? 1'))
        return answer
    
    def Setpoint_2(self):
        """
        Returns the setpoint on Ch2 
        """
        answer = float(get(self.ls, 'SETP? 2'))
        return answer
    '''

    def set_T1(self, value, speed=None):
        if speed == None or speed == 'SetGet':
            self.ls.write(f'SETP 1,{float(value)}')
        else:
            self.set_speed1(speed)
            self.ls.write(f'SETP 1,{float(value)}')

    def set_T2(self, value, speed=None):
        if speed == None or speed == 'SetGet':
            self.ls.write(f'SETP 2,{float(value)}')
        else:
            self.set_speed2(speed)
            self.ls.write(f'SETP 2,{float(value)}')

    def set_T3(self, value, speed=None):
        if speed == None or speed == 'SetGet':
            self.ls.write(f'SETP 3,{float(value)}')
        else:
            self.set_speed3(speed)
            self.ls.write(f'SETP 3,{float(value)}')

    def set_T4(self, value, speed=None):
        if speed == None or speed == 'SetGet':
            self.ls.write(f'SETP 4,{float(value)}')
        else:
            self.set_speed4(speed)
            self.ls.write(f'SETP 4,{float(value)}')

    def speed1(self):
        answer = get(self.ls, 'RAMP? 1')
        print(answer)
        value = answer.split(',')[1]
        return float(value)

    def speed2(self):
        answer = get(self.ls, 'RAMP? 2')
        print(answer)
        value=answer.split(',')[1]
        return float(value)

    def set_speed1(self, value):
        self.ls.write(f'RAMP 1,1,{float(value)}')

    def set_speed2(self, value):
        self.ls.write(f'RAMP 2,1,{float(value)}')

    def clear(self):
        self.ls.write('*CLS')

    def reset(self):
        self.ls.write('*RST')

    def set_led(self, enable):
        if enable:
            enable = 1
        else:
            enable = 0

        self.ls.write(f'LEDS {enable}')

    def led(self):
        return bool(int(get(self.ls, 'LEDS?')))

    def set_heater_range1(self, value):
        value = str(value)
        if value in list(self.range_dict.keys()):
            value = self.range_dict[value]

        self.ls.write(f'RANGE 1,{str(value)}')

    def set_heater_range2(self, value):
        value = str(value)
        if value in list(self.range_dict.keys()):
            value = self.range_dict[value]

        self.ls.write(f'RANGE 2,{str(value)}')

    def set_heater_range3(self, value):
        value = str(value)
        if value in list(self.range_dict.keys()):
            value = self.range_dict[value]

        self.ls.write(f'RANGE 3,{str(value)}')

    def set_heater_range4(self, value):
        value = str(value)
        if value in list(self.range_dict.keys()):
            value = self.range_dict[value]

        self.ls.write(f'RANGE 4,{str(value)}')

    def heater_range1(self):
        return int(get(self.ls, 'RANGE? 1'))

    def heater_range2(self):
        return int(get(self.ls, 'RANGE? 2'))

    def heater_range3(self):
        return int(get(self.ls, 'RANGE? 3'))

    def heater_range4(self):
        return int(get(self.ls, 'RANGE? 4'))

    def tj_temp(self):
        "Thermocouple junction temperature"
        return float(get(self.ls, 'TEMP?'))


def main():
    device = LakeShore336()
    loggable = device.loggable
    for param in loggable:
        print(f'{param} = {getattr(device, param)()}')


if __name__ == '__main__':
    main()
