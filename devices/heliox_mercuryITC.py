import pyvisa as visa

rm = visa.ResourceManager()

# Write command to a device and get it's output
def get(device, command):
    '''device = rm.open_resource() where this function gets all devices initiaals such as adress, baud_rate, data_bits and so on; 
    command = string Standart Commands for Programmable Instruments (SCPI)'''
    return device.query(command)
    #return np.random.random(1)
    
class heliox_mercuryITC():
    def __init__(self, adress):
        '''
        adress example '192.168.07:7020'
        '''
        ip, port = tuple(adress.split(':'))
        self.adress = f'TCPIP0::{ip}::{port}::SOCKET'
        self.device = rm.open_resource(self.adress, write_termination = '\n', read_termination = '\n')
        self.get_options = ['T_He3_Cernox', 'T_He3_low', 'T_He3_sorb', 'W_He3Pot_heater', 'W_He3Sorb_heater',
                            'T_He4_pot', 'T_1K_plate', 'W_He4Pot_heater', 'P_He4Pot_pres', 'Heliox_status']
        self.set_options = []
        self.sweepable = [True, True]
        self.maxspeed = [10, 10]
        self.eps = [0.025, 0.025]
        
    def T_He3_Cernox(self):
        answer = get(self.device, 'READ:DEV:MB1.T1:TEMP:SIG:TEMP')
        answer = answer.split(':')[-1][:-1]
        return answer
    
    def T_He3_low(self):
        answer = get(self.device, 'READ:DEV:DB8.T1:TEMP:SIG:TEMP')
        answer = answer.split(':')[-1][:-1]
        return answer
        
    def T_He3_sorb(self):
        answer = get(self.device, 'READ:DEV:MB1.T1:TEMP:SIG:TEMP')
        answer = answer.split(':')[-1][:-1]
        return answer
    
    def W_He3Pot_heater(self):
        answer = get(self.device, 'READ:DEV:DB7.H1:HTR:SIG:POWR')
        answer = answer.split(':')[-1][:-1]
        return answer
    
    def W_He3Sorb_heater(self):
        answer = get(self.device, 'READ:DEV:MB0.H1:HTR:SIG:POWR')
        answer = answer.split(':')[-1][:-1]
        return answer
    
    def T_He4_pot(self):
        answer = get(self.device, 'READ:DEV:DB6.T1:TEMP:SIG:TEMP')
        answer = answer.split(':')[-1][:-1]
        return answer
    
    def T_1K_plate(self):
        answer = get(self.device, 'READ:DEV:DB5.T1:TEMP:SIG:TEMP')
        answer = answer.split(':')[-1][:-1]
        return answer
    
    def W_He4Pot_heater(self):
        answer = get(self.device, 'READ:DEV:DB6.H1:HTR:SIG:POWR')
        answer = answer.split(':')[-1][:-1]
        return answer
    
    def P_He4Pot_pres(self):
        answer = get(self.device, 'READ:DEV:DB3.P1:PRES:SIG:PRES')
        answer = answer.split(':')[-1][:-1]
        return answer
    
    def Heliox_status(self):
        answer = get(self.device, 'READ:DEV:HelioxX:HEL:SIG:STAT')
        answer = answer.split(':')[-1][:-1]
        return answer
    
    def close(self):
        self.device.close()
    
    
def main():
    device = heliox_mercuryITC(adress = '192.168.0.7:7020')
    try:
        t = device.Heliox_status()
        print(t)
    except Exception as e:
        print(f'Exception happened: {e}')
    finally:
        device.close()
    
if __name__ == '__main__':
    main()
        
        