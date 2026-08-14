import pyvisa as visa
import numpy as np
import time

rm = visa.ResourceManager()

# Write command to a device and get it's output
def get(device, command):
    '''device = rm.open_resource() where this function gets all devices initiaals such as adress, baud_rate, data_bits and so on; 
    command = string Standart Commands for Programmable Instruments (SCPI)'''
    return device.query(command)

class slider():
    def __init__(self, adress=u'COM6'):
        #adress = adress.encode("ascii")
        self.device = rm.open_resource(adress)
        self._state = np.nan
        
        self.set_options = ['close', 'open']
        self.get_options = ['state']
        
    def state(self):
        try:
            if self._state.isnan():
                return self._state
        except:
            if '001F' in self._state:
                return 0
            return 1
    
    def set_close(self, value = None):
        self._state = get(self.device, u'0fw')
    
    def set_open(self, value = None):
        self._state = get(self.device, u'0bw')
        
    def close(self):
        self.device.close()
        
def main():
    device = slider('COM6')
    try:
        device.set_open()
        time.sleep(1)
        device.set_close()
        time.sleep(1)
        device.set_open()
        print(device.state())
    except Exception as ex:
        print(ex)
    finally:
        device.close()
        
if __name__ == '__main__':
    main()
