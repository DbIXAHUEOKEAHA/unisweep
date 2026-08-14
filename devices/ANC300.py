from pymeasure.instruments.attocube.anc300 import ANC300Controller, Axis
from pymeasure.instruments import Instrument
import pyvisa as visa
from pyvisa import constants

rm = visa.ResourceManager()


def get(device, command):
    '''device = rm.open_resource() where this function gets all devices initiaals such as adress, baud_rate, data_bits and so on; 
    command = string Standart Commands for Programmable Instruments (SCPI)'''
    return device.query(command)
    # return np.random.random(1)


class ANC300():
    def __init__(self, adress):
        self.device = ANC300Controller(adress, baud_rate=38400,
                                   data_bits=8, parity=constants.VI_ASRL_PAR_NONE,
                                   stop_bits=constants.VI_ASRL_STOP_ONE,
                                   flow_control=constants.VI_ASRL_FLOW_NONE, 
                                   write_termination = '\r\n', read_termination = '\r\n\s')
        
    def serial(self):
        ans = Axis(1, self.device).serial_nr()
        return ans
        
    def ver(self):
        ans = self.device.query('ver')
    
    def close(self):
        pass
        
def main():
    device = ANC300('COM5')
    try:
        v = device.ver()
        print(v)
    except Exception as ex:
        print(ex)
    finally:
        device.close()
        
if __name__ == '__main__':
    main()