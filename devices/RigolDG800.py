from pymeasure.instruments import Instrument
import pyvisa as visa
from pyvisa import constants
import numpy as np

rm = visa.ResourceManager()


def get(device, command):
    '''device = rm.open_resource() where this function gets all devices initiaals such as adress, baud_rate, data_bits and so on; 
    command = string Standart Commands for Programmable Instruments (SCPI)'''
    return device.query(command)
    # return np.random.random(1)

class RigolDG800():
    def __init__(self, adress = '192.168.0.102'):
        
        if not adress.startswith('COM'):
            if not adress.startswith('TCPIP'):
                adress = f'TCPIP0::{adress}::inst0::INSTR'
        
        self.device = rm.open_resource(adress)
        
        self.set_options = ['freq1', 'freq2', 'ampl1', 'ampl2', 'offset1', 'offset2', 'phas1', 'phas2', 'dc1', 'outp1', 'outp2']
        
    def apply_settings1(self, value: list = ['SIN', 1000, 5, 0, 0]):
        """Set the function shape of the output

        Parameters
        ----------
        value = (shape, freq, ampl, offset, phase)
        shape: SIN SQU RAMP PULS NOIS DC HARM ARB SEQ
        freq: float
        ampl: float
        offset: float
        phase: float
        """
        
        _type = value[0]
        _freq = value[1]
        _ampl = value[2]
        _offset = value[3]
        _phase = value[4]
        
        self.device.write(f':SOUR1:APPL:{_type} {_freq},{_ampl},{_offset},{_phase}')
    
    def apply_settings2(self, value: list = ['SIN', 1000, 5, 0, 0]):
        """Set the function shape of the output

        Parameters
        ----------
        value = (shape, freq, ampl, offset, phase)
        shape: SIN SQU RAMP PULS NOIS DC HARM ARB SEQ
        freq: float
        ampl: float
        offset: float
        phase: float
        """
        
        _type = value[0]
        _freq = value[1]
        _ampl = value[2]
        _offset = value[3]
        _phase = value[4]
        
        self.device.write(f':SOUR2:APPL:{_type} {_freq},{_ampl},{_offset},{_phase}')
       
    def settings1(self) -> list:
        """

        Returns
        -------
        tuple of settings for a specific channel in the format

        """
        
        ans = get(self.device, ':SOUR1:APPL?')
        if type(ans) == str:
            try:
                ans = ans.split(',')
                _type = str(ans[0][1:])
                _freq = float(ans[1])
                _ampl = float(ans[2])
                _offset = float(ans[3])
                _phase = float(ans[4][:-2])
                ans = [_type, _freq, _ampl, _offset, _phase]
            except Exception as ex:
                print(f'Exception happened calling settings for channel 1: {ex}')
                ans = [None, None, None, None]
        else:
            ans = [None, None, None, None]
        return ans
    
    def settings2(self) -> list:
        """

        Returns
        -------
        String of settings for a specific channel

        """
        
        ans = get(self.device, ':SOUR2:APPL?')
        if type(ans) == str:
            try:
                ans = ans.split(',')
                _type = str(ans[0][1:])
                _freq = float(ans[1])
                _ampl = float(ans[2])
                _offset = float(ans[3])
                _phase = float(ans[4][:-2])
                ans = [_type, _freq, _ampl, _offset, _phase]
            except Exception as ex:
                print(f'Exception happened calling settings for channel 1: {ex}')
                ans = [None, None, None, None]
        else:
            ans = [None, None, None, None]
        return ans
    
    def freq1(self):
        ans = self.settings1()[1]
        return ans
    
    def freq2(self):
        ans = self.settings2()[1]
        return ans
    
    def ampl1(self):
        ans = self.settings1()[2]
        return ans
    
    def ampl2(self):
        ans = self.settings2()[2]
        return ans
    
    def offset1(self):
        ans = self.settings1()[3]
        return ans
    
    def offset2(self):
        ans = self.settings2()[3]
        return ans
    
    def phas1(self):
        ans = self.settings1()[4]
        return ans
    
    def phas2(self):
        ans = self.settings2()[4]
        return ans
    
    def dc1(self):
        settings = self.settings1()
        _type = settings[0]
        if not _type == 'PULS':
            ans = 50
        else:
            ans = get(self.device, ':SOURce1:FUNCtion:PULSe:DCYCle?')
        return ans
    
    def dc2(self):
        settings = self.settings2()
        _type = settings[0]
        if not _type == 'PULS':
            ans = 50
        else:
            ans = get(self.device, ':SOURce2:FUNCtion:PULSe:DCYCle?')
        return ans
    
    def set_type1(self, value):
        
        settings = self.settings1()
        try:
            value = str(value)
        except ValueError:
            value = 0
        settings[0] = value
            
        self.apply_settings1(settings)
    
    def set_type2(self, value):
        
        settings = self.settings1()
        try:
            value = str(value)
        except ValueError:
            value = 0
        settings[0] = value
            
        self.apply_settings2(settings)
    
    def set_freq1(self, value):
        
        settings = self.settings1()
        try:
            value = float(value)
        except ValueError:
            value = 0
        settings[1] = value
            
        self.apply_settings1(settings)
    
    def set_freq2(self, value):
        
        settings = self.settings2()
        try:
            value = float(value)
        except ValueError:
            value = 0
        settings[1] = value
        
        self.apply_settings2(settings)
    
    def set_ampl1(self, value):
        
        settings = self.settings1()
        try:
            value = float(value)
        except ValueError:
            value = 0
        settings[2] = value
            
        self.apply_settings1(settings)
    
    def set_ampl2(self, value):
        
        settings = self.settings2()
        try:
            value = float(value)
        except ValueError:
            value = 0
        settings[2] = value
            
        self.apply_settings2(settings)
        
    def set_offset1(self, value):
        
        settings = self.settings1()
        try:
            value = float(value)
        except ValueError:
            value = 0
        settings[3] = value
            
        self.apply_settings1(settings)
    
    def set_offset2(self, value):
        
        settings = self.settings2()
        try:
            value = float(value)
        except ValueError:
            value = 0
        settings[3] = value
        
        self.apply_settings2(settings)
    
    def set_phas1(self, value):
        
        settings = self.settings1()
        try:
            value = float(value)
        except ValueError:
            value = 0
        settings[4] = value
            
        self.apply_settings1(settings)
    
    def set_phas2(self, value):
        
        settings = self.settings2()
        try:
            value = float(value)
        except ValueError:
            value = 0
        settings[4] = value
            
        self.apply_settings2(settings)
        
    def set_dc1(self, value):
        
        settings = self.settings1()
        try:
            value = float(value)
        except ValueError:
            value = 0
        settings[0] = 'PULS'
        
        self.apply_settings1(settings)
        self.device.write(f':SOURce1:FUNCtion:PULSe:DCYCle {value}')
        
    def set_dc2(self, value):
        
        settings = self.settings2()
        try:
            value = float(value)
        except ValueError:
            value = 0
        settings[0] = 'PULS'
        
        self.apply_settings2(settings)
        self.device.write(f':SOURce2:FUNCtion:PULSe:DCYCle {value}')
        
    def set_outp1(self, value: int = 0):
        """

        Parameters
        ----------
        value : 0 - off, 1 - on

        Returns
        -------
        None.

        """
        self.device.write(f':OUTP1:STATE {value}')
    
    def set_outp2(self, value):
        """

        Parameters
        ----------
        value : 0 - off, 1 - on

        Returns
        -------
        None.

        """
        self.device.write(f':OUTP2:STATE {value}')
    
    def set_custom_waveform1(self, waveform: list = [0, 1, 2, 3, 4, 5, 6, 7]):
        
        voltages = np.array(waveform, dtype = float)

        # get length and point spacing
        npts = len(voltages)

        # center and normalize voltages
        offset = np.mean(voltages)
        voltages -= offset
        maxv = max(voltages)
        minv = min(voltages)

        norm = max(abs(maxv), abs(minv))
        vpp = abs(maxv-minv)
        voltages = voltages / norm

        # set amp values to counteract normalization
        self.set_offset1(offset)
        self.set_ampl1(vpp)

        # make sure data is sent in small enough groups
        npartitions = int(np.ceil(npts / self.ARB_MAX_SEND))
        volts_send = np.array_split(voltages, npartitions)

        # send data in groups
        for i in range(npartitions):

            # get data to send
            volts = volts_send[i]
            v = ''
            for _v in volts:
                v+=f'{_v},'
            volts = v[:-1]

            if i+1 < npartitions:
                flag = 'CON'
            else:
                flag = 'END'

            header = f'SOUR1:DATA:DAC16 VOLT,{flag},'

            # write voltages to out
            self.device.write(f'{header}{volts}')
    
    def set_custom_waveform2(self, waveform: str = '0,1'):
        
        voltages = np.array(waveform, dtype = float)

        # get length and point spacing
        npts = len(voltages)

        # center and normalize voltages
        offset = np.mean(voltages)
        voltages -= offset
        maxv = max(voltages)
        minv = min(voltages)

        norm = max(abs(maxv), abs(minv))
        vpp = abs(maxv-minv)
        voltages = voltages / norm

        # set amp values to counteract normalization
        self.set_offset1(offset)
        self.set_ampl1(vpp)

        # make sure data is sent in small enough groups
        npartitions = int(np.ceil(npts / self.ARB_MAX_SEND))
        volts_send = np.array_split(voltages, npartitions)

        # send data in groups
        for i in range(npartitions):

            # get data to send
            volts = volts_send[i]
            v = ''
            for _v in volts:
                v+=f'{_v},'
            volts = v[:-1]

            if i+1 < npartitions:
                flag = 'CON'
            else:
                flag = 'END'

            header = f'SOUR2:DATA:DAC16 VOLT,{flag},'

            # write voltages to out
            self.device.write(f'{header}{volts}')
            
    def outp1(self):
        
        ans = get(self.device, f':OUTP1:STATE?')
        return ans

    def outp2(self):
        
        ans = get(self.device, f':OUTP2:STATE?')
        return ans
    
def main():
    device = RigolDG800()
    try:
        device.set_type1('PULS')
        device.set_freq1(1000000)
        device.set_ampl1(3)
        device.set_phas1(0)
        device.set_dc1(1)
        device.set_type2('PULS')
        device.set_freq2(1000000)
        device.set_ampl2(3)
        device.set_phas2(350)
        device.set_dc2(1)
    except Exception as ex:
        print(f'Exception happened: {ex}')
        device.device.close()

if __name__ == '__main__':
    main()