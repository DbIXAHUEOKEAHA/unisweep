import re
import pyvisa as visa
from pyvisa import constants

rm = visa.ResourceManager()

# Write command to a device and get it's output
def get(device, command):
    '''device = rm.open_resource() where this function gets all devices initiaals such as adress, baud_rate, data_bits and so on; 
    command = string Standart Commands for Programmable Instruments (SCPI)'''
    return device.query(command)
    #return np.random.random(1)

class TC300():

    def __init__(self, adress='ASRL3::INSTR'):
        
        self.adress = adress
        
        self.open()
        
        #self.tc = 0

        self.set_options = {'T1', 'T2', 'VMAX1', 'VMAX2', 'CURR1', 'CURR2'}

        self.get_options = {'T1', 'T2', 'VOLT1', 'VOLT2', 'CURR1', 'CURR2'}
        
        self.operation_mode_dict = {'0 ': 'Heater', '1 ': ' ', '2 ': 'Current'}
       
    def open(self):
        self.tc = rm.open_resource(self.adress, baud_rate=115200,
                                   data_bits=8, parity=constants.VI_ASRL_PAR_NONE,
                                   stop_bits=constants.VI_ASRL_STOP_ONE,
                                   flow_control=constants.VI_ASRL_FLOW_NONE,
                                   write_termination='\r', read_termination='\r')
    
    def IDN(self):
        return(get(self.tc, 'IDN?')[2:])
    
    def set_ch1(self, value):
        #Set Channel 1 status (0=Disable; 1=Enable).
        self.tc.write('EN1=' + str(value))
        
    def set_ch2(self, value):
        #Set Channel 2 status (0=Disable; 1=Enable).
        self.tc.write('EN2=' + str(value))

    def T1(self):
        # Get the CH1 target temperature; returned value is the actual temperature in °C
        value_str = get(self.tc, 'TACT1?')
        self.close()
        if value_str == '':
            self.open()
            value_str = get(self.tc, 'TACT1?')
            self.close()
        value_float = re.findall(r'\d*\.\d+|\d+', value_str)
        value_float = [float(i) for i in value_float]
        return(value_float[0])
    
    def VOLT1(self):
        #Get the CH1 Output Voltage value, with a range of 0.1 to 24.0 V 
        #and a resolution of 0.1V.
        value = get(self.tc, 'VOLT1?')
        self.close()
        if value.startswith('\n'):
            value = value[2::]
        return(value)
    
    def VOLT2(self):
        #Get the CH2 Output Voltage value, with a range of 0.1 to 24.0 V 
        #and a resolution of 0.1V.
        value = get(self.tc, 'VOLT2?')
        self.close()
        if value.startswith('\n'):
            value = value[2::]
        return(value)
    
    def CURR1(self):
        #Get the CH1 Actual Output Current Value, the range is -2000 to +2000 mA,
        #with a resolution of 1mA.
        value = get(self.tc, 'CURR1?')
        self.close()
        if value.startswith('\n'):
            value = value[2::]
        return(value)
    
    def CURR2(self):
        #Get the CH1 Actual Output Current Value, the range is -2000 to +2000 mA,
        #with a resolution of 1mA.
        value = get(self.tc, 'CURR2?')
        self.close()
        if value.startswith('\n'):
            value = value[2::]
        return(value)
    
    def set_VMAX1(self, value):
        #Set the CH1 Output Voltage Max value to value V 
        #(value ranges from 0.1 to 24, corresponding to 0.1 to 24.0 V).
        self.tc.write('VMAX1=' + str(int(value) * 10))
        self.close()
        
    def set_VMAX2(self, value):
        #Set the CH2 Output Voltage Max value to value V 
        #(value ranges from 0.1 to 24, corresponding to 0.1 to 24.0 V).
        self.tc.write('VMAX2=' + str(int(value) * 10))
        self.close()
        
    def set_CURR1(self, value):
        #Set the CH1 output current value, 
        #range is -2000 to +2000 mA, resolution of 1 mA.
        self.tc.write('CURR1=' + str(int(value)))
        self.close()
        
    def set_CURR2(self, value):
        #Set the CH2 output current value, 
        #range is -2000 to +2000 mA, resolution of 1 mA.
        self.tc.write('CURR2=' + str(int(value)))
        self.close()

    def set_T1(self, value=20):
        # Set the CH1 target temperature to value °C, the range is defined by
        # TMIN1 and TMAX1, the setting resolution of value is 1.
        #self.tc.write('EN1=1')
        self.tc.write('TSET1=' + str(int(value * 10)))
        self.close()

    def set_T1_MIN(self, t1_from=0):
        # Set the CH1 Target Temperature Min value,
        # (Range: -200 to TMAX1°C, with a resolution of 1°C).
        self.tc.write('TMIN1=' + str(t1_from))
        self.close()

    def set_T1_MAX(self, t1_to=30):
        # Set the CH1 Target Temperature Max value, n equals value
        # TMIN1 to 400°C, with a resolution of 1°C).
        self.tc.write('T1MAX=' + str(t1_to))
        self.close()

    def T2(self):
        # Get the CH2 target temperature; returned value is the actual temperature in °C
        value_str = get(self.tc, 'TACT2?')
        self.close()
        if value_str == '':
            self.open()
            value_str = get(self.tc, 'TACT2?')
            self.close()
        value_float = re.findall(r'\d*\.\d+|\d+', value_str)
        value_float = [float(i) for i in value_float]
        return(value_float[0])

    def set_T2(self, value=20):
        # Set the CH2 target temperature to value °C, the range is defined by
        # TMIN1 and TMAX1, the setting resolution of value is 1.
        #self.tc.write('EN2=1')
        self.tc.write('TSET2=' + str(int(value * 10)))
        self.close()

    def set_T2_MIN(self, t2_from=0):
        # Set the CH2 Target Temperature Min value,
        # (Range: -200 to TMAX2°C, with a resolution of 1°C).
        self.tc.write('TMIN1=' + str(t2_from))
        self.close()

    def set_T2_MAX(self, t2_to=20):
        # Set the CH2 Target Temperature Max value, n equals value
        # TMIN1 to 400°C, with a resolution of 1°C).
        self.tc.write('T1MAX=' + str(t2_to))
        self.close()
    
    def set_PID_P(self, value = 1.9):
        #Set CH1 P share parameter (Gain of P) to value, 
        #the range of value is 0 to 9.99 with a resolution of 0.01.
        self.tc.write('KP1=' + str(int(value * 100)))
        self.close()
        
    def set_PID_I(self, value = 0.01):
        #Set CH1 I share parameter (Gain of P) to value, 
        #the range of value is 0 to 9.99 with a resolution of 0.01.
        self.tc.write('TI1=' + str(int(value * 100)))
        self.close()
        
    def set_PID_D(self, value = 2.4):
        #Set CH1 D share parameter (Gain of P) to value, 
        #the range of value is 0 to 9.99 with a resolution of 0.01.
        self.tc.write('TD1=' + str(int(value * 100)))
        self.close()
        
    def PID_P(self):
        #Get CH1 P parameter
        value = get(self.tc, 'KP1?')
        self.close()
        if value.startswith('\n'):
            value = value[2::]
        return(value)
    
    def PID_I(self):
        #Get CH1 I parameter
        value = get(self.tc, 'TI1?')
        self.close()
        if value.startswith('\n'):
            value = value[2::]
        return(value)
    
    def PID_D(self):
        #Get CH1 D parameter
        value = get(self.tc, 'TD1?')
        self.close()
        if value.startswith('\n'):
            value = value[2::]
        return(value)
        
    def type1(self):
        #Get CH1 sensor type
        value = get(self.tc, 'TYPE1?')
        self.close()
        if value.startswith('\n'):
            value = value[2::]
        return(value)
    
    def type2(self):
        #Get CH2 sensor type
        value = get(self.tc, 'TYPE2?')
        self.close()
        if value.startswith('\n'):
            value = value[2::]
        return(value)

    def op_mode1(self):
        #Get CH1 operation mode
        value = get(self.tc, 'MOD1?')
        self.close()
        if value.startswith('\n'):
            value = value[2::]
        return(self.operation_mode_dict[value])
    
    def op_mode2(self):
        #Get CH1 operation mode
        value = get(self.tc, 'MOD2?')
        self.close()
        if value.startswith('\n'):
            value = value[2::]
        return(self.operation_mode_dict[value])
    
    def set_op_mode1(self, value):
        #Set CH1 operation mode
        self.tc.write('MOD1=' + str(value))
        self.close()
    
    def set_op_mode2(self, value):
        #Set CH2 operation mode
        self.tc.write('MOD2=' + str(value))
        self.close()
    
    def close(self):
        self.tc.close()