# -*- coding: utf-8 -*-
"""

@author: DbIXAHUEOKEAHA
"""

import numpy as np
from atto_device.atto_device import AMC
from atto_device.atto_device.AMC.ACS import AttoException

class amc():
    def __init__(self, adress: str = "192.168.1.4"):
        self.device = AMC(adress)
        self.device.connect()
        self.fraction = 1000
        
        self.set_options = ['gnd_1', 'gnd_2', 'gnd_3', 'step_up_1', 'step_down_1', 'step_up_2', 'step_down_2',
                            'step_up_3', 'step_down_3', 'volt_1', 'volt_2', 'volt_3', 'freq_1', 'freeq_2',
                            'freq_3', 'ampl_1', 'amplt_2', 'ampl_3', 'outp_active1', 'outp_active_2', 
                            'outp_active_3']
        self.get_options = ['position_1', 'position_2', 'position_3','gnd_1', 'gnd_2', 'gnd_3',
                            'volt_1', 'volt_2', 'volt_3', 'freq_1', 'freq_2', 'freq_3', 
                            'outp_active_1', 'outp_active_2', 'outp_active_3']
        
        for i in self.set_options:
            self.sweepable.append(False)
        
        for i in range(3):
            self.__dict__[f'position_{i+1}'] = lambda i = i: self.position(i)
            self.__dict__[f'gnd_{i+1}'] = lambda i = i: self.gnd(i)
            self.__dict__[f'volt_{i+1}'] = lambda i = i: self.volt(i)
            self.__dict__[f'freq_{i+1}'] = lambda i = i: self.freq(i)
            self.__dict__[f'ampl_{i+1}'] = lambda i = i: self.ampl(i)
            self.__dict__[f'outp_active_{i+1}'] = lambda i = i: self.outp_active(i)
            self.__dict__[f'set_position_{i+1}'] = lambda value, i = i: self.set_position(i, value * self.fraction)
            self.__dict__[f'set_gnd_{i+1}'] = lambda value, i = i: self.set_gnd(i, value)
            self.__dict__[f'set_step_up_{i+1}'] = lambda value, i = i: self.set_step_up(i, value)
            self.__dict__[f'set_step_down_{i+1}'] = lambda value, i = i: self.set_step_down(i, value)
            self.__dict__[f'set_volt_{i+1}'] = lambda value, i = i: self.set_volt(i, value * self.fraction)
            self.__dict__[f'set_freq_{i+1}'] = lambda value, i = i: self.set_freq(i, value * self.fraction)
            self.__dict__[f'set_ampl_{i+1}'] = lambda value, i = i: self.set_ampl(i, value * self.fraction)
            self.__dict__[f'set_outp_active_{i+1}'] = lambda value, i = i: self.outp_active(i, value)
            self.__dict__[f'step_{i+1}_position'] = 0
        
    def get_nan_answer(self, func):
        try:
            answer = func()
        except AttoException:
            answer = np.nan
        return answer
        
    def description(self):
        answer = self.device.description.getDeviceType()
        return answer
    
    def position(self, axis: int):
        answer = self.device.move.getPosition(axis)
        return answer // self.fraction
    
    def gnd(self, axis: int):
        answer = self.device.move.getGroundAxis(axis)
        return answer
    
    def volt(self, axis: int):
        answer = self.device.control.getCurrentOutputVoltage(axis)
        return answer // self.fraction
    
    def freq(self, axis: int):
        answer = self.device.control.getControlFrequency(axis)
        return answer // self.fraction
    
    def ampl(self, axis: int):
        answer = self.device.control.getControlAmplitude(axis)
        return answer // self.fraction
    
    def outp_active(self, axis: int):
        answer = self.device.control.getControlOutput(axis)
        return answer
    
    def capacity(self, axis: int):
        name = "Capacity Test"
        parameters = "{'capacity': 'Capacity (nF)'}, 'version': 1.0.0'}"
        answer = self.device.test.execute(name, parameters)
        return answer
    
    def set_position(self, axis: int, value: int):
        '''

        Parameters
        ----------
        axis : int
            Axis count number (int).
        value : int
            Set absolute position.

        Returns
        -------
        None.

        '''
        
        self.device.move.setControlTargetPosition(axis, value)
        self.device.move.moveReference(axis)
    
    def set_gnd(self, axis: int, value: bool):
        '''

        Parameters
        ----------
        axis : int
            Axis count number (int).
        value : bool
            True: Enable ground
            False: Disable ground

        Returns
        -------
        None.

        '''
        self.device.move.setGroundAxis(axis, value)
    
    def set_step_up(self, axis: int, value: int):
        step = value - self.__dict__[f'step_{axis+1}_position']
        try:
            step = int(step)
        except ValueError:
            step = 1
        if step >= 0:
            self.device.move.setNSteps(axis, False, step)
        else:
            self.device.move.setNSteps(axis, True, step)
        
        
        self.__dict__[f'step_{axis+1}_position'] = value
        
    def set_step_down(self, axis: int, value: int):
        step = - value + self.__dict__[f'step_{axis+1}_position']
        try:
            step = int(step)
        except ValueError:
            step = 1
        if step >= 0:
            self.device.move.setNSteps(axis, True, step)
        else:
            self.device.move.setNSteps(axis, False, step)
        
        self.__dict__[f'step_{axis+1}_position'] = value
        
    def set_volt(self, axis: int, value: int):
        self.device.control.setCurrentOutputVoltage(axis, value)
    
    def set_freq(self, axis: int, value: int):
        self.device.control.setControlFrequency(axis, value)
    
    def set_ampl(self, axis: int, value: int):
        self.device.control.setControlAmplitude(axis, value)
    
    def set_outp_active(self, axis: int, value: bool):
        self.device.control.getControlOutput(axis, value)
    
    def close(self):
        self.device.close()
    
def main():
    device = amc('192.168.1.4')
    freq_1 = device.freq_1()
    print(f'Freq1 = {freq_1}')
    pos_1 = device.position_1()
    print(f'Pos1 = {pos_1}')
    volt_1 = device.volt_1()
    print(f'Volt1 = {volt_1}')
    ampl_1 = device.ampl_1()
    print(f'Ampl1 = {ampl_1}')
    outp_active_1 = device.outp_active_1()
    print(f'Outp_active1 = {outp_active_1}')
    gnd_1 = device.gnd_1()
    print(f'gnd1 = {gnd_1}')
    device.close()
        
if __name__ == '__main__':
    main()