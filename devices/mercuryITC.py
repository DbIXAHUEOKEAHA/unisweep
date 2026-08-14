import pyvisa as visa

rm = visa.ResourceManager()

# Write command to a device and get it's output
def get(device, command):
    '''device = rm.open_resource() where this function gets all devices initiaals such as adress, baud_rate, data_bits and so on; 
    command = string Standart Commands for Programmable Instruments (SCPI)'''
    return device.query(command)
    #return np.random.random(1)
    
class mercuryITC():
    def __init__(self, adress):
        '''
        adress example '192.168.02:7020'
        '''
        ip, port = tuple(adress.split(':'))
        self.adress = f'TCPIP0::{ip}::{port}::SOCKET'
        self.device = rm.open_resource(self.adress, write_termination = '\n', read_termination = '\n')
        self.get_options = ['T_VTI', 'T_sample']
        self.set_options = ['T_VTI', 'T_sample', 'T_VTI_rate', 'T_sample_rate']
        self.sweepable = [True, True]
        self.maxspeed = [10, 10]
        self.eps = [0.01, 0.01]
        
    def T_VTI(self):
        answer = get(self.device, 'READ:DEV:MB1.T1:TEMP:SIG:TEMP')
        answer = answer.split(':')[-1][:-1]
        return answer        
        
    def T_sample(self):
        answer = get(self.device, 'READ:DEV:DB8.T1:TEMP:SIG:TEMP')
        answer = answer.split(':')[-1][:-1]
        return answer 
        
    def set_T_VTI(self, value, speed = None):
        maxspeed = float(self.maxspeed[self.set_options.index('T_VTI')])
        if speed == None:
            self.set_T_VTI_rate(maxspeed)
            self.device.write(f'SET:DEV:MB1.T1:TEMP:LOOP:TSET:{round(float(value), 3)}')
        elif speed == 'SetGet':
            self.device.write(f'SET:DEV:MB1.T1:TEMP:LOOP:TSET:{round(float(value), 3)}')
        else:
            speed = min(maxspeed, speed)
            self.speed_VTI = speed
            self.set_T_VTI_rate(speed)
            self.device.write(f'SET:DEV:MB1.T1:TEMP:LOOP:TSET:{round(float(value), 3)}')
    
    def set_T_sample(self, value, speed = None):
        maxspeed = float(self.maxspeed[self.set_options.index('T_sample')])
        if speed == None:
            self.set_T_sample_rate(maxspeed)
            self.device.write(f'SET:DEV:DB8.T1:TEMP:LOOP:TSET:{round(float(value), 3)}')
        elif speed == 'SetGet':
            self.device.write(f'SET:DEV:DB8.T1:TEMP:LOOP:TSET:{round(float(value), 3)}')
        else:
            speed = min(speed, maxspeed)
            self.speed_sample = speed
            self.set_T_sample_rate(speed)
            self.device.write(f'SET:DEV:DB8.T1:TEMP:LOOP:TSET:{round(float(value), 3)}')
    
    def set_T_VTI_rate(self, value):
        self.device.write(f'SET:DEV:MB1.T1:TEMP:LOOP:RSET:{round(float(value), 3)}')
        
    def set_T_sample_rate(self, value):
        self.device.write(f'SET:DEV:DB8.T1:TEMP:LOOP:RSET:{round(float(value), 3)}')
        
    def close(self):
        self.device.close()
    
    
def main():
    device = mercuryITC(adress = '192.168.0.2:7020')
    try:
        T = device.T_VTI()
        print(T)
    except Exception as e:
        print(f'Exception happened: {e}')
    finally:
        device.close()
    
if __name__ == '__main__':
    main()
        
        