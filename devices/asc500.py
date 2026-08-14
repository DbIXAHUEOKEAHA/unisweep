# -*- coding: utf-8 -*-
"""

@author: DbIXAHUEOKEAHA
"""

import numpy as np
from matplotlib import pyplot as plt
from ASC500_Python_Control.lib import ASC500
import time

if __name__ == '__main__':
    binPath = "ASC500_Python_Control\\Installer\\ASC500CL-V2.7.13\\"
    dllPath = "ASC500_Python_Control\\64bit_lib\\ASC500CL-LIB-WIN64-V2.7.13\\daisybase\\lib\\"
else:
    binPath = "devices\\ASC500_Python_Control\\Installer\\ASC500CL-V2.7.13\\"
    dllPath = "devices\\ASC500_Python_Control\\64bit_lib\\ASC500CL-LIB-WIN64-V2.7.13\\daisybase\\lib\\"
    
class asc500():
    def __init__(self, adress = 'COM3'):
        
        self.device = ASC500(binPath, dllPath)
        self.device.base.startServer()
        
        self.get_options = ['scanner_x', 'scanner_y', 'scanner_z', 'outp_active', 'gnd_x', 'gnd_y', 'gnd_z', 'volt_x', 'volt_y', 'volt_z', 'freq_x', 'freq_y', 'freq_z']
        self.set_options = ['scanner_x', 'scanner_y', 'scanner_z', 'scanner_XY_counter', 'outp_active', 'gnd_x', 'gnd_y', 'gnd_z', 'step_up_x', 'step_up_y', 'step_up_z', 'step_down_x', 
                            'step_down_y', 'step_down_z', 'volt_x', 'volt_y', 'volt_z', 'freq_x', 'freq_y', 'freq_z']
        
        self.set_freq_x(100)
        self.set_freq_y(100)
        self.set_freq_z(100)
        
        self.set_volt_x(40)
        self.set_volt_y(40)
        self.set_volt_z(45)
        
        self.sweepable = [False, False, False, False, False, False, False, False, False, False, False, False, False, False, False]
        
    def gnd_x(self) -> bool:
        """
        Returns mode of x-axis
        -------
        bool
        
        True = grounded
        False = ungrounded
        """
        axis = 2
        mode = self.device.coarse.getCoarseAxisMode(axis)
        if mode == 1:
            ans = False
        else:
            ans = True
        return ans
    
    def gnd_y(self) -> bool:
        """
        Returns mode of y-axis
        -------
        bool
        
        True = grounded
        False = ungrounded
        """
        axis = 3
        mode = self.device.coarse.getCoarseAxisMode(axis)
        if mode == 1:
            ans = False
        else:
            ans = True
        return ans
    
    def gnd_z(self) -> bool:
        """
        Returns mode of z-axis
        -------
        bool
        
        True = grounded
        False = ungrounded
        """
        axis = 1
        mode = self.device.coarse.getCoarseAxisMode(axis)
        if mode == 1:
            ans = False
        else:
            ans = True
        return ans
    
    def set_gnd_x(self, value):
        """
        If value == 1 or False: set x-axis ungrounded
        If value == 2 or True: set x-axis grounded
        
        Returns
        -------
        None.
        """
        axis = 2
        if value == 1 or value == False:
            set_mode = 1
        else:
            set_mode = 2
        self.device.coarse.setCoarseAxisMode(axis, set_mode)
        
    def set_gnd_y(self, value):
        """
        If value == 1 or False: set y-axis ungrounded
        If value == 2 or True: set y-axis grounded
        
        Returns
        -------
        None.
        """
        axis = 3
        if value == 1 or value == False:
            set_mode = 1
        else:
            set_mode = 2
        self.device.coarse.setCoarseAxisMode(axis, set_mode)
        
    def set_gnd_z(self, value):
        """
        If value == 1 or False: set z-axis ungrounded
        If value == 2 or True: set z-axis grounded
        
        Returns
        -------
        None.
        """
        axis = 1
        if value == 1 or value == False:
            set_mode = 1
        else:
            set_mode = 2
        self.device.coarse.setCoarseAxisMode(axis, set_mode)
        
    def outp_active(self):
        """
        Activates the output of the scanner.

        Parameters
        ----------
        None.

        Returns
        -------
        None.

        """
        # check if scanner output is already active?
        outActive = self.device.base.getParameter(self.device.base.getConst('ID_OUTPUT_STATUS'), 0 )
        time.sleep(0.1)
        return outActive
    
    def set_outp_active(self, value: int):
        """
        If value == 0 or False: set output active off
        If value == 1 or True: set set output active on
        
        """
        
        outActive = self.outp_active()
        
        if outActive == 0: #if disabled
            if value == 1 or value == True:
                self.device.base.setParameter(self.device.base.getConst('ID_OUTPUT_ACTIVATE'), 1)
                time.sleep(0.1)
        else: #if enabled
            if value == 0 or value == False:
                self.device.base.setParameter(self.device.base.getConst('ID_OUTPUT_ACTIVATE'), 0)
                time.sleep(0.1)
    
    def set_step_up_x(self, value: int = 1):
        """
        Makes 'value' number of steps up along x-axis
        
        Returns
        -------
        None.
        """
        
        try:
            value = int(value)
        except ValueError:
            value = 1
        
        axis = 2
        self.device.coarse.stepCoarseUp(axis, value)
        
    def set_step_down_x(self, value: int = 1):
        """
        Makes 'value' number of steps down along x-axis 
        
        Returns
        -------
        None.
        """
        
        try:
            value = int(value)
        except ValueError:
            value = 1
        
        axis = 2
        self.device.coarse.stepCoarseDown(axis, value)
        
    def set_step_up_y(self, value: int = 1):
        """
        Makes 'value' number of steps up along y-axis
        
        Returns
        -------
        None.
        """
        
        try:
            value = int(value)
        except ValueError:
            value = 1
        
        axis = 3
        self.device.coarse.stepCoarseUp(axis, value)
        
    def set_step_down_y(self, value: int = 1):
        """
        Makes 'value' number of steps down along y-axis 
        
        Returns
        -------
        None.
        """
        
        try:
            value = int(value)
        except ValueError:
            value = 1
        
        axis = 3
        self.device.coarse.stepCoarseDown(axis, value)
        
    def set_step_up_z(self, value: int = 1):
        """
        Makes 'value' number of steps up along z-axis
        
        Returns
        -------
        None.
        """
        
        try:
            value = int(value)
        except ValueError:
            value = 1
        
        axis = 1
        self.device.coarse.stepCoarseUp(axis, value)
        
    def set_step_down_z(self, value: int = 1):
        """
        Makes 'value' number of steps up along z-axis
        
        Returns
        -------
        None.
        """
        
        try:
            value = int(value)
        except ValueError:
            value = 1
        
        axis = 1
        self.device.coarse.stepCoarseDown(axis, value)
        
    def scanner_z(self):
        """
        Returns the position of the zcontrol
        """
        
        return self.device.zcontrol.getPositionZ()
    
    '''
    def set_scanner_z(self, value):
        """
        Set the position of the zcontrol
        """
        
        try:
            value = float(value)
        except ValueError:
            print(f'Invalid step type: expected int or float, got {type(value)}')
            value = self.scanner_z()
        
        self.device.zcontrol.setPositionZ(value)
    '''
        
    def scanner_x(self):
        """
        Returns the position of the x-scanner
        """
        
        return self.device.scanner.getPositionsXYZRel()[0]
    
    def scanner_y(self):
        """
        Returns the position of the y-scanner
        """
        
        return self.device.scanner.getPositionsXYZRel()[1]
        
    def set_scanner_up_x(self, value: float):
        """
        

        Parameters
        ----------
        value : int or float; step up

        Reads the position of zcontrol and sets a position + step

        """
        
        step = 500e-9 #500 nm step
        
        x = self.scanner_x()
        y = self.scanner_y()
        z = self.scanner_z()
        
        try:
            value = float(value)
            new_x = x + value*step
        except ValueError:
            print(f'Invalid step type: expected int or float, got {type(value)}')
            new_x = x
        
        self.device.scanner.setPositionsXYZRel([new_x, y, z])
        
    def set_scanner_down_x(self, value: float):
        """
        

        Parameters
        ----------
        value : int or float; step down

        Reads the position of zcontrol and sets a position - step

        """
        
        step = 500e-9 #500 nm step
        
        x = self.scanner_x()
        y = self.scanner_y()
        z = self.scanner_z()
        
        try:
            value = float(value)
            new_x = x - value*step
        except ValueError:
            print(f'Invalid step type: expected int or float, got {type(value)}')
            new_x = x
        
        self.device.scanner.setPositionsXYZRel([new_x, y, z])
        
    def set_scanner_up_y(self, value: float):
        """
        

        Parameters
        ----------
        value : int or float; step up

        Reads the position of zcontrol and sets a position + step

        """
        
        step = 500e-9 #500 nm step
        
        x = self.scanner_x()
        y = self.scanner_y()
        z = self.scanner_z()
        
        try:
            value = float(value)
            new_y = y + value*step
        except ValueError:
            print(f'Invalid step type: expected int or float, got {type(value)}')
            new_y = y
        
        self.device.scanner.setPositionsXYZRel([x, new_y, z])
        
    def set_scanner_down_y(self, value: float):
        """
        

        Parameters
        ----------
        value : int or float; step down

        Reads the position of zcontrol and sets a position - step

        """
        
        step = 500e-9 #500 nm step
        
        x = self.scanner_x()
        y = self.scanner_y()
        z = self.scanner_z()
        
        try:
            value = float(value)
            new_y = y - value*step
        except ValueError:
            print(f'Invalid step type: expected int or float, got {type(value)}')
            new_y = y
        
        self.device.scanner.setPositionsXYZRel([x, new_y, z])
    
    def set_scanner_up_z(self, value: float):
        """
        

        Parameters
        ----------
        value : int or float; step up

        Reads the position of zcontrol and sets a position + step

        """
        
        step = 500e-9 #500 nm step
        
        x = self.scanner_x()
        y = self.scanner_y()
        z = self.scanner_z()
        
        try:
            value = float(value)
            new_z = z + value*step
        except ValueError:
            print(f'Invalid step type: expected int or float, got {type(value)}')
            new_z = z
        
        self.device.scanner.setPositionsXYZRel([x, y, new_z])
        
    def set_scanner_down_z(self, value: float):
        """
        

        Parameters
        ----------
        value : int or float; step down

        Reads the position of zcontrol and sets a position - step

        """
        
        step = 500e-9 #500 nm step
        
        x = self.scanner_x()
        y = self.scanner_y()
        z = self.scanner_z()
        
        try:
            value = float(value)
            new_z = z - value*step
        except ValueError:
            print(f'Invalid step type: expected int or float, got {type(value)}')
            new_z = z
        
        self.device.scanner.setPositionsXYZRel([x, y, new_z])
        
    def set_scanner_x(self, value: float, speed = None):
        """
        
        Parameters:
        -------------
        value : float; target position for x scanner
        """
        
        x = self.scanner_x()
        y = self.scanner_y()
        z = self.scanner_z()
        
        try:
            if value > 100e-6:
                value = x
        except ValueError:
            value = x
        
        self.device.scanner.setPositionsXYZRel([value, y, z])
        
    def set_scanner_y(self, value: float, speed = None):
        """
        
        Parameters:
        -------------
        value : float; target position for y scanner
        """
        
        x = self.scanner_x()
        y = self.scanner_y()
        z = self.scanner_z()
        
        try:
            if value > 100e-6:
                value = y
        except ValueError:
            value = y
        
        self.device.scanner.setPositionsXYZRel([x, value, z])
        
    def set_scanner_z(self, value: float, speed = None):
        """
        
        Parameters:
        -------------
        value : float; target position for z scanner
        """
        
        x = self.scanner_x()
        y = self.scanner_y()
        z = self.scanner_z()
        
        try:
            if value > 100e-6:
                value = z
        except ValueError:
            value = z
        
        self.device.scanner.setPositionsXYZRel([x, y, value])
        
    def set_scanner_XY_counter(self, value = int, speed = None):
        
        StartX = 6.9e-6
        EndX = 9.9e-6
        DeltaX = 500e-9
        StartY = 7.4e-6
        EndY = 10.4e-6
        DeltaY = 500e-9
        
        snakemode = True
        
        X = np.linspace(StartX, EndX, int(np.abs(EndX - StartX)/DeltaX)+1)
        Y = np.linspace(StartY, EndX, int(np.abs(EndY - StartY)/DeltaY)+1)
        
        X, Y = np.meshgrid(X, Y)
        
        def reverse_odd_rows(array):
            for i in range(len(array)):
                if i % 2 == 1:  # Check if the row index is even
                    array[i] = array[i][::-1]  # Reverse the row
            return array
        
        if snakemode:
            X = reverse_odd_rows(X)
        
        i = int(value)
        
        try:
            X = X.flatten()[i]
            Y = Y.flatten()[i]
        except IndexError:
            if i > 1:
                X = X.flatten()[-1]
                Y = Y.flatten()[-1]
            else:
                X = X.flatten()[0]
                Y = Y.flatten()[0]
        
        self.set_scanner_x(X)
        self.set_scanner_y(Y)
        
    def volt_x(self):
        """
        Returns
        -------
        float: Voltage on x-axis

        """
        axis = 4
        ans = self.device.coarse.getCoarseVoltage(axis)
        return ans
    
    def volt_y(self):
        """
        Returns
        -------
        float: Voltage on y-axis

        """
        axis = 5
        ans = self.device.coarse.getCoarseVoltage(axis)
        return ans
    
    def volt_z(self):
        """
        Returns
        -------
        float: Voltage on z-axis

        """
        axis = 6
        ans = self.device.coarse.getCoarseVoltage(axis)
        return ans
    
    def set_volt_x(self, value):
        """
        set voltage on x-axis
        Returns
        -------
        None.

        """
        axis = 4
        self.device.coarse.setCoarseVoltage(axis, value)
        
    def set_volt_y(self, value):
        """
        set voltage on y-axis
        Returns
        -------
        None.

        """
        axis = 5
        self.device.coarse.setCoarseVoltage(axis, value)
        
    def set_volt_z(self, value):
        """
        set voltage on z-axis
        Returns
        -------
        None.

        """
        axis = 6
        self.device.coarse.setCoarseVoltage(axis, value)
        
    def freq_x(self):
        """
        Returns
        -------
        float: Frequency on x-axis

        """
        axis = 4
        ans = self.device.coarse.getCoarseFrequency(axis)
        return ans
    
    def freq_y(self):
        """
        Returns
        -------
        float: Frequency on y-axis

        """
        axis = 5
        ans = self.device.coarse.getCoarseFrequency(axis)
        return ans
    
    def freq_z(self):
        """
        Returns
        -------
        float: Frequency on z-axis

        """
        axis = 6
        ans = self.device.coarse.getCoarseFrequency(axis)
        return ans
    
    def set_freq_x(self, value):
        """
        set Frequency on x-axis
        Returns
        -------
        None.

        """
        axis = 4
        self.device.coarse.setCoarseFrequency(axis, value)
        
    def set_freq_y(self, value):
        """
        set Frequency on y-axis
        Returns
        -------
        None.

        """
        axis = 5
        self.device.coarse.setCoarseFrequency(axis, value)
        
    def set_freq_z(self, value):
        """
        set Frequency on z-axis
        Returns
        -------
        None.

        """
        axis = 6
        self.device.coarse.setCoarseFrequency(axis, value)
        
    def Temp(self):
        """
        Return the environment temperature from Daisy
        """
        
        T = self.device.limits.getTemperature()
        return T
    
    def set_Temp(self, value: float):
        """

        Parameters
        ----------
        value : Environment temperature

        Sets the environment temperature in Daisy

        """
        
        try:
            value = float(value)
        except ValueError:
            print(f'Unexpected type of environment temperature, expected int or flot, got {type(value)}')
            value = self.T
        
        self.device.limits.setTemperature(value)
    
    def close(self):
        #self.device.base.stopServer()
        pass

def main():
    #set_gnd_z(true)
    device = asc500()
    #device.set_outp_active(1)
    #device.set_scanner_x(1e-6)
    #device.set_scanner_y(1e-6)
    #time.sleep(2)
    #x = device.scanner_x()
    #y = device.scanner_y()
    
    #device.set_scanner_XY_counter(0)
    
    #print(f'X = {x}, Y = {y}')
    
    #device.set_gnd_y(1)
    device.close()
    #device.set_gnd_z(1)
    #device.base.stopServer()
    #device.base.startServer()
    #device.base.stopServer()
    
        
        
if __name__ == '__main__':
    main()
