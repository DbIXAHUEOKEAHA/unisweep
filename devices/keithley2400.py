import pyvisa as visa
import numpy as np
import time

rm = visa.ResourceManager()

# Write command to a device and get it's output
def get(device, command):
    # return np.round(np.random.random(1), 1)
    return device.query(command)

class keithley2400():
    
    def __init__(self, adress = 'GPIB0::11::INSTR'):
        self.sm = rm.open_resource(
            adress)
        
        self.sm.write(':SOUR:CLE:AUTO OFF') # auto on/off
        
        self.set_options = ['Volt', 'Curr', 'compl_curr', 'V_NPLC', 'I_NPLC', 'R_NPLC']
        
        self.get_options = ['Volt', 'Curr', 'Res', 'compl_curr', 'V_NPLC', 'I_NPLC', 'R_NPLC', 'line_freq', 'Sdelay', 'TDelay']
        
        self.loggable = ['IDN', 'Volt', 'Curr', 'V_NPLC', 'I_NPLC', 'R_NPLC']
        
        self.eps = [5e-7, 5e-7, None, None, None, None]
        
    def IDN(self):
        return get(self.sm, '*IDN?')[:-1]
    
    
    def Volt(self):
        try:
            answer = get(self.sm, ':MEAS:VOLT?').split(',')[0]
        except ValueError:
            answer = get(self.sm, ':MEAS:VOLT?').split(',')[0]
            
        self.cur_volt = float(answer)
            
        return float(answer)
        
    def Curr(self):
        try:
            answer = get(self.sm, ':MEAS:CURR?').split(',')[1]
        except ValueError:
            answer = get(self.sm, ':MEAS:CURR?').split(',')[1]
            
        self.cur_curr = float(answer)
            
        return float(answer)
        
    def Res(self):
        try:
            answer = get(self.sm, ':MEAS:RES?').split(',')[2]
        except ValueError:
            answer = get(self.sm, ':MEAS:RES?').split(',')[2]
        return float(answer)

    def set_I_auto_range(self):
        self.sm.write(':SENS:CURR:RANGE:AUTO 1')
        
    def off_I_auto_range(self):
        self.sm.write(':SENS:CURR:RANGE:AUTO 0')
        
    def set_V_auto_range(self):
        self.sm.write(':SENS:VOLT:RANGE:AUTO 1')
        
    def off_V_auto_range(self):
        self.sm.write(':SENS:VOLT:RANGE:AUTO 0')
        
    def set_R_auto_range(self):
        self.sm.write(':SENS:RES:RANGE:AUTO 1')
        
    def off_R_auto_range(self):
        self.sm.write(':SENS:RES:RANGE:AUTO 0')
    
    def set_Curr(self, value = 0):
        self.sm.write(':SOUR:CURR:MODE FIXED')
        self.sm.write(':SOUR:CURR ' + str(round(float(value), 9))) 
        
    def set_Volt(self, value = 0, speed = None):
        self.sm.write(':SOUR:VOLT:MODE FIXED')
        self.sm.write(':SOUR:VOLT ' + str(round(float(value), 9))) 
        
    def set_compl_curr(self, value = 0):
        self.sm.write(f':SENS:CURR:PROT {str(round(float(value), 9))}')
        
    def V_NPLC(self):
        answer = float(get(self.sm, ':SENS:VOLT:NPLC?'))
        self.vnplc = answer
        return answer
        
    def set_V_NPLC(self, value = 1):
        self.sm.write(':SENS:VOLT:NPLC ' + str(round(float(value), 2)))
        
    def I_NPLC(self):
        answer = float(get(self.sm, ':SENS:CURR:NPLC?'))
        self.inplc = answer
        return answer
        
    def set_I_NPLC(self, value = 1):
        self.sm.write(':SENS:CURR:NPLC ' + str(round(float(value), 2)))
        
    def R_NPLC(self):
        return float(get(self.sm, ':SENS:RES:NPLC?'))
        
    def set_R_NPLC(self, value = 1):
        self.sm.write(':SENS:RES:NPLC ' + str(round(float(value), 2)))
        
    def compl_curr(self):
        answer = get(self.sm, ':SENS:CURR:PROT?')
        return answer
        
    def line_freq(self):
        answer = float(get(self.sm, ':SYST:LFR?'))
        self.freq = answer
        return answer
    
    def Sdelay(self):
        answer = float(get(self.sm, ':SOUR:DEL?'))
        self.sdelay = answer
        return answer
    
    def Tdelay(self):
        answer = float(get(self.sm, ':TRIG:DEL?')) 
        self.tdelay = float(get(self.sm, ':TRIG:DEL?'))
        return answer
    
    '''
    def set_Volt(self, value, speed = None):
        """ Ramps to a target voltage from the set voltage value over
        a certain number of linear steps, each separated by a pause duration.
        """
        
        self.Volt()
        
        maxspeed = self.maxspeed[self.set_options.index('Volt')]
        
        if speed == None or speed == 'SetGet':
            speed = maxspeed
        else:
            speed = min(speed, maxspeed)
            
        if not hasattr(self, 'freq'):
            self.line_freq()
            
        if not hasattr(self, 'sdelay'):
            self.Sdelay()
            
        if not hasattr(self, 'tdelay'):
            self.Tdelay()
            
        if not hasattr(self, 'vnplc'):
            self.V_NPLC()
            
        dv = abs(float(value) - self.cur_volt)
        nsteps = dv / (speed * (self.sdelay + self.vnplc / self.freq + self.tdelay))
        nsteps = max(1, int(abs(round(nsteps))))
        
        dt = dv / speed
        dt = dt / nsteps
    
        voltages = np.linspace(
            self.cur_volt,
            value,
            nsteps
        )
        for voltage in voltages:
            self.set_V(voltage)
            time.sleep(abs(dt))
            
    def set_Curr(self, value, speed):
        """ Ramps to a target current from the set current value over
        a certain number of linear steps, each separated by a pause duration.
        """
        
        self.Curr()
        
        maxspeed = self.maxspeed[self.set_options.index('Curr')]
        
        if speed == None or speed == 'SetGet':
            speed = maxspeed
        else:
            speed = min(speed, maxspeed)
        
        if not hasattr(self, 'freq'):
            self.line_freq()
            
        if not hasattr(self, 'sdelay'):
            self.Sdelay()
            
        if not hasattr(self, 'tdelay'):
            self.Tdelay()
            
        if not hasattr(self, 'inplc'):
            self.I_NPLC()
            
        di = abs(float(value) - self.cur_curr)
        nsteps = di / (speed * (self.sdelay + self.vnplc / self.freq + self.tdelay))
        nsteps = max(int(abs(round(nsteps))))
        
        dt = di / speed
        dt = dt / nsteps
        
        currents = np.linspace(
            self.cur_curr,
            value,
            nsteps
        )
        for current in currents:
            self.set_I(current)
            time.sleep(abs(dt))
    '''
    
def main():
    device = keithley2400(adress = 'GPIB0::7::INSTR')
    loggable = device.loggable
    for param in loggable:
        print(f'{param} = {getattr(device, param)()}')
    
if __name__ == '__main__':
    main()