import pyvisa as visa
import numpy as np
rm = visa.ResourceManager()

def get(device, command):
    '''device = rm.open_resource() where this function gets all devices initiaals such as adress, baud_rate, data_bits and so on; 
    command = string Standart Commands for Programmable Instruments (SCPI)'''
    return device.query(command)
    #return np.random.random(1)

class sim928():

    def __init__(self, adress):
        '''
        Establish connection, create shorthand for read,r, write,w and ask, a
        store sweep parameters here
        '''
        self.adress = adress
        self.sim928 = rm.open_resource(self.adress, baud_rate=115200,
                                   data_bits=8, write_termination='\r', read_termination='\r')
        
        self.set_options = ['volt', 'override', 'output']
        self.get_options = ['volt', 'batts']

        self.sim928.write('PSTA ON')  # status register pulse only (instead of latch)

    def volt(self):
        ''' returns voltage
        '''
        value = get(self.sim928, 'VOLT?')
        return value
                    
    def set_volt(self, value):
        ''' sets voltage
        '''
        self.sim928.write('VOLT '+str(value))
        
    def batts(self):
        ''' returns the battery state'''
        value = get(self.sim928, 'BATS?')
        return value
        
    def set_override(self, *args, **kwargs):
        ''' switches the Battery '''
        return self.sim928.write('BCOR')        
        
    def set_output(self, value=0):
        '''
        Set output on/off True/False
        '''
        value = int(value)
        if value == 1:
            self.sim928.write('OPON')
        else:
            self.sim928.write('OPOF')