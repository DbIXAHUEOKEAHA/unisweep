import pyvisa as visa
from pyvisa import constants

rm = visa.ResourceManager()

# Write command to a device and get it's output
def get(device, command):
    # return np.round(np.random.random(1), 1)
    return device.query(command)

class keithley2182():
    
    def __init__(self, adress = 'GPIB0::16::INSTR'):
        self.device = rm.open_resource(
            adress, write_termination='\n', read_termination='\n')
 
        self.set_options = []
        
        self.get_options = ['Volt']
        
        self.loggable = []
        
        self.eps = []
        
    def Volt(self):
        ans = get(self.device, ':FETC?')
        return ans
    
    def IDN(self):
        ans = get(self.device, '*IDN?')
        return ans
    
    def close(self):
        self.device.close()
    
def main():
    device = keithley2182()
    try:
        print(device.Volt())
    except:
        device.close()
    finally:
        device.close()
    
if __name__ == '__main__':
    main()