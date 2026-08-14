import pyvisa as visa
import time

rm = visa.ResourceManager()

# Write command to a device and get it's output
def get(device, command):
    '''device = rm.open_resource() where this function gets all devices initiaals such as adress, baud_rate, data_bits and so on; 
    command = string Standart Commands for Programmable Instruments (SCPI)'''
    return device.query(command)
    #return np.random.random(1)
    
class mercuryIPS():
    def __init__(self, adress):
        '''
        adress example '192.168.05:7020'
        '''
        ip, port = tuple(adress.split(':'))
        self.adress = f'TCPIP0::{ip}::{port}::SOCKET'
        self.device = rm.open_resource(self.adress, write_termination = '\n', read_termination = '\n')
        self.get_options = ['field', 'current', 'voltage', 'field_rate', 'current_rate', 'field_target', 
                            'Magnet_T', 'action', 'PT1A', 'PT1B', 'PT2A', 'PT2B']
        self.set_options = ['field', 'current', 'field_rate', 'current_rate', 'action']
        self.sweepable = [True, True, False, False]
        self.maxspeed = [self.TMin2OeSec(0.09), 1, None, None]
        self.eps = [0.1, 0.1, None, None]
        self.actn = {'HOLD': 0, 'RTOS': 1, 'RTOZ': 2}
            
        self.check_crit()
        
    def check_crit(self):
        self.cur_T = self.Magnet_T()
        try:
            if float(self.cur_T) >= 4.4:
                self.crit_T = True
            else:
                self.crit_T = False
        except TypeError:
            self.crit_T = True
        
    def Oe2T(self, value: float):
        answer = value * 1e-4
        return answer
    
    def T2Oe(self, value: float):
        answer = value * 1e4
        return answer
    
    def OeSec2TMin(self, value: float):
        answer = value * 1e-4 * 60
        return answer
    
    def TMin2OeSec(self, value: float):
        answer = value * 1e4 / 60
        return answer
        
    #def target_field(self) -> float:
    
    def field(self) -> float:
        answer = get(self.device, 'READ:DEV:GRPZ:PSU:SIG:FLD')
        answer = answer.split(':')[-1][:-1]
        answer = float(answer)
        answer = self.T2Oe(answer)
        
        self.check_crit()
        if self.crit_T:
            return f'Magnet hot, {answer}'
        else:
            return answer        
        
    def current(self) -> float:
        answer = get(self.device, 'READ:DEV:GRPZ:PSU:SIG:CURR')
        answer = answer.split(':')[-1][:-1]
        answer = float(answer)
        self.check_crit()
        if self.crit_T:
            return f'Magnet hot, {answer}'
        else:
            return answer 
        
    def voltage(self) -> float:
        answer = get(self.device, 'READ:DEV:GRPZ:PSU:SIG:VOLT')
        answer = answer.split(':')[-1][:-1]
        answer = float(answer)
        return answer
    
    def field_rate(self) -> float:
        answer = get(self.device, 'READ:DEV:GRPZ:PSU:SIG:RFLD')
        answer = answer.split(':')[-1][:-5]
        answer = float(answer)
        answer = self.TMin2OeSec(answer)
        return answer  
    
    def current_rate(self) -> float:
        answer = get(self.device, 'READ:DEV:GRPZ:PSU:SIG:RCUR')
        answer = answer.split(':')[-1][:-5]
        answer = float(answer)
        return answer 
    
    def He_level(self): #Not working
        answer = get(self.device, 'READ:DEV:DB7.L1:LVL:SIG:HEL:LEV')
        answer = answer.split(':')[-1][:-1]
        answer = answer
        return answer
    
    def field_target(self) -> float:
        answer = get(self.device, 'READ:DEV:GRPZ:PSU:SIG:FSET')
        answer = answer.split(':')[-1][:-1]
        answer = float(answer)
        answer = self.T2Oe(answer)
        return answer
    
    def action(self):
        answer = get(self.device, 'READ:DEV:GRPZ:PSU:ACTN')
        answer = answer.split(':')[-1]
        answer = self.actn[answer]
        return answer
    
    def Magnet_T(self) -> float:
        answer = get(self.device, 'READ:DEV:MB1.T1:TEMP:SIG:TEMP')
        answer = answer.split(':')[-1][:-1]
        answer = float(answer)
        return answer 
    
    def PT1A(self) -> float:
        answer = get(self.device, 'READ:DEV:DB6.T1:TEMP:SIG:TEMP')
        answer = answer.split(':')[-1][:-1]
        answer = float(answer)
        return answer 
    
    def PT2A(self) -> float:
        answer = get(self.device, 'READ:DEV:DB8.T1:TEMP:SIG:TEMP')
        answer = answer.split(':')[-1][:-1]
        answer = float(answer)
        return answer 
    
    def PT1B(self) -> float:
        answer = get(self.device, 'READ:DEV:DB5.T1:TEMP:SIG:TEMP')
        answer = answer.split(':')[-1][:-1]
        answer = float(answer)
        return answer 
    
    def PT2B(self) -> float:
        answer = get(self.device, 'READ:DEV:DB7.T1:TEMP:SIG:TEMP')
        answer = answer.split(':')[-1][:-1]
        answer = float(answer)
        return answer 
        
    def set_field(self, value, speed = None):
        self.check_crit()
        if self.crit_T:
            return
        
        maxspeed = float(self.maxspeed[self.set_options.index('field')])
        value = float(value)
        value = self.Oe2T(value)
        if speed == None:
            speed = self.OeSec2TMin(maxspeed)
            self.set_field_rate(speed)
        elif speed == 'SetGet':
            pass
        else:
            speed = min(speed, maxspeed)
            speed = float(speed)
            speed = self.OeSec2TMin(speed)
            self.set_field_rate(speed)
        if self.action() == 1:
            time.sleep(0.1)
            self.device.write('SET:DEV:GRPZ:PSU:ACTN:HOLD')
            a = self.device.read()
            time.sleep(0.1)
        elif self.action() == 0:
            time.sleep(0.2)
            #self.reset()
        #self.device.write('SET:DEV:GRPZ:PSU:ACTN:HOLD')
        #a = self.device.read()
        time.sleep(0.1)
        self.device.write(f'SET:DEV:GRPZ:PSU:SIG:FSET:{round(float(value), 5)}')
        a = self.device.read()
        time.sleep(0.1)
        self.device.write('SET:DEV:GRPZ:PSU:ACTN:RTOS')
        a = self.device.read()
        if self.action() == 0:
            time.sleep(0.1)
            self.device.write(f'SET:DEV:GRPZ:PSU:SIG:FSET:{round(float(value), 5)}')
            a = self.device.read()
            self.device.write('SET:DEV:GRPZ:PSU:ACTN:RTOS')
            a = self.device.read()
            
    def set_current(self, value, speed = None):
        self.check_crit()
        if self.crit_T:
            return
        
        maxspeed = float(self.maxspeed[self.set_options.index('current')])
        if speed == None:
            self.set_current_rate(maxspeed)
        elif speed == 'SetGet':
            pass
        else:
            speed = min(speed, maxspeed)
            self.set_current_rate(speed)
        self.device.write('SET:DEV:GRPZ:PSU:ACTN:HOLD')
        a = self.device.read()
        self.device.write(f'SET:DEV:GRPZ:PSU:SIG:CSET:{round(float(value), 5)}')
        a = self.device.read()
        self.device.write('SET:DEV:GRPZ:PSU:ACTN:RTOS')
        a = self.device.read()
            
    def set_field_rate(self, value):
        value = abs(value)
        self.device.write(f'SET:DEV:GRPZ:PSU:SIG:RFST:{round(float(value), 5)}')
        a = self.device.read()
        
    def set_current_rate(self, value):
        value = abs(value)
        self.device.write(f'SET:DEV:GRPZ:PSU:SIG:RCST:{round(float(value), 5)}')
        a = self.device.read()
        
    def set_action(self, value):
        if value == 0:
            self.device.write('SET:DEV:GRPZ:PSU:ACTN:HOLD')
            a = self.device.read()
        elif value == 1:
            self.device.write('SET:DEV:GRPZ:PSU:ACTN:RTOS')
            a = self.device.read()
        elif value == 2:
            self.device.write('SET:DEV:GRPZ:PSU:ACTN:RTOZ')
            a = self.device.read()
        else:
            raise UserWarning(f'Only 0 (HOLD), 1 (TO SET), 2 (TO ZERO) can be set, got {value}')
        
    def close(self):
        self.device.close()
        
    def reset(self):
        self.close()
        time.sleep(0.1)
        self.device = rm.open_resource(self.adress, write_termination = '\n', read_termination = '\n')
        
        
def main():
    device = mercuryIPS(adress = '192.168.0.5:7020')
    try:
        t = device.He_level()
        print(t)
    except Exception as e:
        print(f'Exception happened: {e}')
    finally:
        device.close()
    
if __name__ == '__main__':
    main()
    
    
    
        
        