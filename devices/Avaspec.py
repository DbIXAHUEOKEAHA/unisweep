"""
Example showing how to communicate with an AvaSpec-2048L spectrometer.
"""
import time

# if matplotlib is available then plot the data
try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

from msl.equipment import (
    EquipmentRecord,
    ConnectionRecord,
    Backend,
)

class Avaspec():
    def __init__(self, adress):
        
        serial = '2009277U1'
        
        if adress == 'COM1':
            serial = '46387463732'
        elif adress == 'COM2':
            serial = '455272056'
        elif adress == '192.168.0.1':
            serial = '4527u1'
        
        record = EquipmentRecord(
            manufacturer='Avantes',
            model='AvaSpec-2048L',  # update for your device
            serial=serial,
            connection=ConnectionRecord(
                address='SDK::C:/AvaSpecX64-DLL_9.14.0.0/avaspecx64.dll',  # update the path to the DLL file
                backend=Backend.MSL,
            )
        )
        
        self.device = record.connect()
        #self.use_high_res_adc(False)
        
        self._dark_data = None
        
        self.Num_Pixels = self.num_pixels()
        self.Stop_Pixel = self.Num_Pixels - 1
        self.Integration_time = 5
        self.N_Average = 1
        
        num_pixels = self.num_pixels()
        cfg = self.device.MeasConfigType()
        cfg.m_StopPixel = self.Stop_Pixel
        cfg.m_IntegrationTime = self.Integration_time  # in milliseconds
        cfg.m_NrAverages = self.N_Average  # number of averages
        self.device.prepare_measure(cfg)
        
        self.set_options = ['integration_time', 'n_average']
        self.get_options = ['num_pixels', 'integration_time', 'n_average', 'wavelength', 'data', 'dark_data']
        
        self.sweepable = ['False', 'False']
        self.maxspeed = [None, None]
        
    def num_pixels(self):
        ans = self.device.get_num_pixels()
        return ans
    
    def integration_time(self):
        cfg = self.device.MeasConfigType()
        ans = cfg.m_IntegrationTime
        return ans
    
    def n_average(self):
        cfg = self.device.MeasConfigType()
        ans = cfg.m_NrAverages
        return ans
    
    def wavelength(self):
        ans = self.device.get_lambda()
        #convert to string
        answer = ''
        for i in ans:
            answer += str(i)
            answer += ','
        answer = answer[:-1]
        return answer
    
    def data(self):
        # start 1 measurement, wait until the measurement is finished, then get the data
        self.device.measure(1)
        while not self.device.poll_scan():
            time.sleep(0.01)
        _, dat = self.device.get_data()
        
        self._dark_data = self.device.get_dark_pixel_data()
        #convert to string
        answer = ''
        for i in dat:
            answer += str(i)
            answer += ','
        answer = answer[:-1]
        return answer
        
    def dark_data(self):
        answer = ''
        for i in self._dark_data:
            answer += str(i)
            answer += ','
        answer = answer[:-1]
        return answer
    
    def set_integration_time(self, value: float, speed: float = None):
        
        self.Integration_Time = value
        
        num_pixels = self.num_pixels()
        cfg = self.device.MeasConfigType()
        cfg.m_StopPixel = self.Stop_Pixel
        cfg.m_IntegrationTime = self.Integration_time  # in milliseconds
        cfg.m_NrAverages = self.N_Average  # number of averages
        self.device.prepare_measure(cfg)
        
    def set_n_average(self, value: int, speed: float = None):
        self.N_Average = value
        
        num_pixels = self.num_pixels()
        cfg = self.device.MeasConfigType()
        cfg.m_StopPixel = self.Stop_Pixel
        cfg.m_IntegrationTime = self.Integration_time  # in milliseconds
        cfg.m_NrAverages = self.N_Average  # number of averages
        self.device.prepare_measure(cfg)
        
def main():
    try:
        device = Avaspec('111.111.11.11')
        device.set_integration_time(2500)
        int_t = device.integration_time()
        print(int_t)
        data = device.data()
        print(data)
    except Exception as ex:
        print(f'Exception happened while initializing Avaspec: {ex}')
    finally:
        pass
    
if __name__ == '__main__':
    main()
        