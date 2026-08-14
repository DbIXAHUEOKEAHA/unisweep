import pyvisa as visa
import time
rm = visa.ResourceManager()

def get(device, command):
    '''device = rm.open_resource() where this function gets all devices initiaals such as adress, baud_rate, data_bits and so on; 
    command = string Standart Commands for Programmable Instruments (SCPI)'''
    return device.query(command)
    #return np.random.random(1)
    
class sim900():
    def __init__(self, adress = 'GPIB0::2::INSTR'):
        self.adress = adress
        self.sim900 = self.sim928 = rm.open_resource(self.adress)
        self.set_options = ['volt1', 'volt2', 'volt3', 'volt4', 'volt5', 'volt6', 'volt7', 'volt8']
        self.get_options = ['volt1', 'volt2', 'volt3', 'volt4', 'volt5', 'volt6', 'volt7', 'volt8']
        
    def idn(self):
        value = get(self.sim900, '*IDN?')
        return value
        
    def volt1(self):
        ''' returns voltage of 1st port
        '''
        time.sleep(0.02)
        self.sim900.write('CONN 1, "\n"')
        value = get(self.sim900, 'VOLT?')
        self.sim900.write('\n')
        return float(value)
    
    def volt2(self):
        ''' returns voltage of 2nd port
        '''
        time.sleep(0.02)
        self.sim900.write('CONN 2, "\n"')
        value = get(self.sim900, 'VOLT?')
        self.sim900.write('\n')
        return float(value)
    
    def volt3(self):
        ''' returns voltage of 3rd port
        '''
        time.sleep(0.02)
        self.sim900.write('CONN 3, "\n"')
        value = get(self.sim900, 'VOLT?')
        self.sim900.write('\n')
        return float(value)
    
    def volt4(self):
        ''' returns voltage of 4th port
        '''
        time.sleep(0.02)
        self.sim900.write('CONN 4, "\n"')
        value = get(self.sim900, 'VOLT?')
        self.sim900.write('\n')
        return float(value)

    def volt5(self):
        ''' returns voltage of 5th port
        '''
        time.sleep(0.02)
        self.sim900.write('CONN 5, "\n"')
        value = get(self.sim900, 'VOLT?')
        self.sim900.write('\n')
        return float(value)
    
    def volt6(self):
        ''' returns voltage of 6th port
        '''
        self.sim900.write('CONN 6, "\n"')
        value = get(self.sim900, 'VOLT?')
        self.sim900.write('\n')
        return float(value)
    
    def volt7(self):
        ''' returns voltage of 7th port
        '''
        time.sleep(0.02)
        self.sim900.write('CONN 7, "\n"')
        value = get(self.sim900, 'VOLT?')
        self.sim900.write('\n')
        return float(value)
    
    def volt8(self):
        ''' returns voltage of 8th port
        '''
        time.sleep(0.02)
        self.sim900.write('CONN 8, "\n"')
        value = get(self.sim900, 'VOLT?')
        self.sim900.write('\n')
        return float(value)
    
    def set_volt1(self, value):
        ''' sets voltage
        '''
        value = round(float(value), 3)
        time.sleep(0.02)
        self.sim900.write('CONN 1, "\n"')
        self.sim900.write(f'VOLT {str(value)}')
        self.sim900.write("\n")
        
    def set_volt2(self, value):
        ''' sets voltage
        '''
        time.sleep(0.02)
        value = round(float(value), 3)
        self.sim900.write('CONN 2, "\n"')
        self.sim900.write(f'VOLT {str(value)}')
        self.sim900.write("\n")
    
    def set_volt3(self, value):
        ''' sets voltage
        '''
        time.sleep(0.02)
        value = round(float(value), 3)
        self.sim900.write('CONN 3, "\n"')
        self.sim900.write(f'VOLT {str(value)}')
        self.sim900.write("\n")
        
    def set_volt4(self, value):
        ''' sets voltage
        '''
        time.sleep(0.02)
        value = round(float(value), 3)
        self.sim900.write('CONN 4 "\n"')
        self.sim900.write(f'VOLT {str(value)}')
        self.sim900.write("\n")
        
    def set_volt5(self, value):
        ''' sets voltage
        '''
        time.sleep(0.02)
        value = round(float(value), 3)
        self.sim900.write('CONN 5, "\n"')
        self.sim900.write(f'VOLT {str(value)}')
        self.sim900.write("\n")
        
    def set_volt6(self, value):
        ''' sets voltage
        '''
        time.sleep(0.02)
        value = round(float(value), 3)
        self.sim900.write('CONN 6, "\n"')
        self.sim900.write(f'VOLT {str(value)}')
        self.sim900.write("\n")
    
    def set_volt7(self, value):
        ''' sets voltage
        '''
        time.sleep(0.02)
        value = round(float(value), 3)
        self.sim900.write('CONN 7, "\n"')
        self.sim900.write(f'VOLT {str(value)}')
        self.sim900.write("\n")
        
    def set_volt8(self, value):
        ''' sets voltage
        '''
        time.sleep(0.02)
        value = round(float(value), 3)
        self.sim900.write('CONN 8, "\n"')
        self.sim900.write(f'VOLT {str(value)}')
        self.sim900.write("\n")
    
    
def main():
    device = sim900('GPIB0::2::INSTR')
    device.set_volt2(0.1)
    print(device.volt2())
    
if __name__ == '__main__':
    main()