import numpy as np
np.set_printoptions(threshold = np.inf)
from scipy.signal import savgol_filter,find_peaks
import matplotlib.pyplot as plt
import TeledyneLeCroyPy
import time
from scipy.stats import binned_statistic

#Inspired by https://github.com/SengerM/TeledyneLeCroyPy

class Waverunner9000():
    def __init__(self, adress = '169.254.28.243'):
        if adress.startswith('TCPIP0'):
            self.adress = adress
        else:
            self.adress = f'TCPIP0::{adress}::inst0::INSTR'
        self.device = TeledyneLeCroyPy.LeCroyWaveRunner(self.adress)
        self.device.write('CORD HI') # High-Byte first
        self.device.write('COMM_FORMAT DEF9,WORD,BIN') # Communication Format: DEF9 (this is the #9 specification; WORD (reads the samples as 2 Byte integer; BIN (reads in Binary)
        self.device.write('CHDR OFF') # Command Header OFF (fewer characters to transfer)
        self.n_channel = 1

        self.get_options = []
        self.set_options = []
        self.measured_Time = [None, None, None, None]
        self.measured_Amplitude = [None, None, None, None]
        
        self._probability1 = np.nan
        self._probability2 = np.nan
        self._probability3 = np.nan
        self._probability4 = np.nan
        
        for i in [1,2,3,4]:
            self.__dict__[f'Time{i}'] = lambda i = i: self.Time(n = i)
            self.__dict__[f'Amplitude{i}'] = lambda i = i: self.Amplitude(n = i)
            self.__dict__[f'_time{i}'] = lambda i = i: self._time(n = i)
            self.__dict__[f'_ampl{i}'] = lambda i = i: self._ampl(n = i)
            self.__dict__[f'window{i}'] = lambda i = i: self.window(channel = i)
            self.__dict__[f'probability{i}'] = lambda i = i: self.probability(channel = i)
            #self.__dict__[f'correlator{i}'] = lambda i = i: self.correlator(channel = i)
            self.get_options.append(f'Time{i}')
            self.get_options.append(f'Amplitude{i}')
            self.get_options.append(f'window{i}')
            self.get_options.append(f'probability{i}')
            #self.get_options.append(f'correlator{i}')
            
            #self.set_options.append(f'Correlator{i}')
            
            self.__dict__[f'correlator_value{i}'] = 0
            self.__dict__[f'stat{i}'] = np.array([0])
            
        get_opts = ['TDIV']
        
        for i in get_opts:
            self.get_options.append(i)
            
        self.set_options.append('TDIV')
            
        self.VALID_TDIVs = {'1NS': 1e-9,'2NS': 2e-9, '5NS': 5e-9,'10NS': 10e-9,'20NS': 20e-9,
                            '50NS': 50e-9,'100NS': 100e-9,'200NS': 200e-9,'500NS': 500e-9,'1US': 1e-6,
                            '2US': 2e-6,'5US': 5e-6,'10US': 10e-6,'20US': 20e-6,'50US': 50e-6,
                            '100US': 100e-6,'200US': 200e-6,'500US':500e-6,'1MS': 1e-3,'2MS': 2e-3,
                            '5MS': 5e-3,'10MS': 10e-3,'20MS': 20e-3,'50MS': 50e-3,'100MS': 100e-3,
                            '200MS': 200e-3,'500MS': 500e-3,'1S': 1,'2S': 2,'5S': 5,'10S': 10,'20S': 20,
                            '50S': 50,'100S': 100}
        
<<<<<<< HEAD
        self.sparcing = 200
        self._npoints = 100000
=======
        self.sparcing = 1
        self._npoints = 5000000
>>>>>>> 555c29c9bdf7e38315a660134f1ee159cc0af24a
        self.first_point = 0
        self.segment_number = 0
        self.set_config()
        
        self.trashold = 0.010
        self.offset = 0.005
        self.freq = 500000
        self.window_div = 50e-3 / 10

    def Waveform(self):
        self.device.wait_for_single_trigger()
        data = self.device.get_waveform(n_channel=1)
        return data['waveforms']
    
    def TDIV(self):
        ans = self.device.query('TDIV?')
        return ans
    
    def npoints(self):
        return self._npoints
    
    def set_npoints(self, value):
        self._npoints = value
        self.set_config()
    
    def set_config(self):
        self.device.write(f'WAVEFORM_SETUP SP,{self.sparcing},NP,{self._npoints},FP,{self.first_point},SN,{self.segment_number}')
    
    def set_TDIV(self, value):
        if type(value) == str:
            if not value in list(self.VALID_TDIVs.keys()):
                value = '10MS'
        else:
            try:
                value = float(value)
                value = list(self.VALID_TDIVs.keys())[np.argmin(abs(np.array(list(self.VALID_TDIVs.values())) - value))]
            except ValueError:
                value = '10MS'
        self.device.set_tdiv(value)

    def _time(self, n:int):
        n = int(n)
        data = self.device.get_waveform(n_channel=n)
        ans = data['waveforms'][0]['Time (s)']
        return ans
    
    def _ampl(self, n:int):
        n = int(n)
        self.device.set_trig_mode('AUTO')
        data = self.device.get_waveform(n_channel=n)
        self.device.set_trig_mode('SINGLE')
        ans = data['waveforms'][0]['Amplitude (V)']
        return ans
    
    def Time(self, n:int):
        n = int(n)
        channels = [1,2,3,4]
        channels.remove(n)
        '''
        if self.measured_Time[n-1] is None: #None was queried
            data = self.device.get_waveform(n_channel=n)
            ans = data['waveforms'][0]['Time (s)']
            aux = data['waveforms'][0]['Amplitude (V)']
            for i in channels:
                data = self.device.get_waveform(n_channel=i)
                self.measured_Time[i-1] = data['waveforms'][0]['Time (s)']
                self.measured_Amplitude[i-1] = data['waveforms'][0]['Amplitude (V)']
        else:
            ans = self.measured_Time[n-1]
            aux = self.measured_Amplitude[n-1]
        self.measured_Time[n-1] = None
        self.measured_Amplitude[n-1] = aux
        '''
        data = self.device.get_waveform(n_channel=n)
        ans = data['waveforms'][0]['Time (s)']#[:self._npoints]
        #aux = data['waveforms'][0]['Amplitude (V)']
        answer = ''
        for i in ans:
            answer += str(i)
            answer += ','
        answer = answer[:-1]
        return answer
    
    def Amplitude(self, n):
        n = int(n)
        channels = [1,2,3,4]
        channels.remove(n)
        '''
        if self.measured_Amplitude[n-1] is None: #None was queried
            data = self.device.get_waveform(n_channel=n)
            aux = data['waveforms'][0]['Time (s)']
            ans = data['waveforms'][0]['Amplitude (V)']
            for i in channels:
                data = self.device.get_waveform(n_channel=i)
                self.measured_Time[i-1] = data['waveforms'][0]['Time (s)']
                self.measured_Amplitude[i-1] = data['waveforms'][0]['Amplitude (V)']
        else:
            aux = self.measured_Time[n-1]
            ans = self.measured_Amplitude[n-1]
        self.measured_Amplitude[n-1] = None
        self.measured_Time[n-1] = aux
        '''
        data = self.device.get_waveform(n_channel=n)
        #aux = data['waveforms'][0]['Time (s)']
        ans = data['waveforms'][0]['Amplitude (V)']#[:self._npoints]
        answer = ''
        for i in ans:
            answer += str(i)
            answer += ','
        answer = answer[:-1]
        return answer
    
    def read_window(self, channel: int = 1):
        """
        Parameters
        ----------
        
        freq : float
            Frequency of applied wave.
        
        channel : int
            Channel number. The default is 1.
            
        trashold : float [Volts]
            Value of the state limit. When any value in the bin is greater than trashold, the bin is counted as 1, otherwise as 0.
            Default is 0.005 [Volts]
            
        offset : float [Volt]
            Value of the backgound.
            Default is 0.04 [Volts]

        Returns
        -------
        Array of states, where each value represent a state of the bin, correspondent to a single wave oscillation.
        
        Example
        -------
        [0, 0, 1, 0, 1, 0] would mean that the whole window readout time lasted 6 oscillations periods and burst happened 
        during 3rd and 5th oscillation.

        """
        
        try:
            self.freq = int(self.freq)
        except ValueError:
            return [0]
        
        sparcing = 5
        npoints = int(2e6)
        firstpoint = 0
        segmentnumber = 0
        self.device.write(f'WAVEFORM_SETUP SP,{sparcing},NP,{npoints},FP,{firstpoint},SN,{segmentnumber}') #apply settings
        
        tdiv = self.window_div
        self.set_TDIV(tdiv)
        T = tdiv * 10 #Screen has 10 divisions
        
        nbins = max(1, T * self.freq) #Number of bins
        nbins = int(nbins)
        
        a = self.__dict__[f'_ampl{channel}']() - self.offset
        t = self.__dict__[f'_time{channel}']()*sparcing
    
        
        peak_ind = 0
        bin_idx = a.shape[0] // nbins #nuber of points in each bin
        peaks, _ = find_peaks(a, height = self.trashold, distance = bin_idx) #index of peaks
        
        if peaks.shape[0] == 0:
            
            '''
            sh = 200
            
            plt.plot(t[:sh], a[:sh])
            plt.hlines(y = self.trashold, xmin = 0, xmax = t[:sh].max(), color = 'orange', alpha = 0.5)
            plt.xlim((0, t[sh]))
            plt.xlabel('Time, s')
            plt.ylabel('Voltage, V')
            plt.show()
            '''
            
            self.__dict__[f'stat{channel}'] = np.zeros(nbins)
            return np.zeros(nbins)
        
        
        peak_ind = peaks[0] % bin_idx 
        
        #shift
        if peak_ind >= bin_idx // 4 * 3 or peak_ind <= bin_idx // 4:
            a = a[bin_idx // 2:]
            t = t[bin_idx // 2:]
            t = t - t[0]
        
        bin_edges = [0]
        
        dt = np.max(t) / nbins
        for i in range(nbins):
            bin_edges.append(dt*(i+1))
        
        '''
        sh = 200
        
        plt.plot(t[:sh], a[:sh])
        plt.vlines(x = bin_edges, ymin = a[:sh].min(), ymax = a[:sh].max(), color = 'b', alpha = 0.3)
        plt.hlines(y = self.trashold, xmin = 0, xmax = t[:sh].max(), color = 'orange', alpha = 0.5)
        plt.xlim((0, t[sh]))
        plt.xlabel('Time, s')
        plt.ylabel('Voltage, V')
        plt.show()
        '''
        
        self.device.set_trig_mode('AUTO')
        
        def stat_func(a, trashold = self.trashold):
            a = np.abs(a)
            return any(a >= trashold) #return 1 if overshoots trashold
        
        stat, _, _ = binned_statistic(t, a, stat_func, nbins)
        self.__dict__[f'stat{channel}'] = stat
        
        return stat
    
    def window(self, channel: int = 1, n = 100):
        wind = self.read_window(channel)[:n]
        answer = ''
        for i in wind:
            answer += f'{i},'
        return answer[:-1]
        
    def correlation(self, values: list, n: int = 1):
        """

        Parameters
        ----------
        values : list
            List of bins state from self.read_window().
        n : int
            Order of correlation.

        Returns
        -------
        n-th correlator

        """
        
        s = 0
        if n == 0:
            n = -values.shape[0]
            
        try:
            n = int(n)
        except ValueError:
            n = -values.shape[0]
            
        for i, _ in enumerate(values[:-n]):
            s += values[i]*values[i+n]
        s = s / values.shape[0]
        return s
    
    def set_Correlator(self,channel, value, speed = None):
        self.__dict__[f'correlator_value{channel}'] = value
    
    def correlator(self, channel: int):
        return self.correlation_n(channel, 100)
        #return self.correlation(self.__dict__[f'stat{channel}'], self.__dict__[f'correlator_value{channel}'])
    
    def probability(self, channel: int = 1):
        #return self.correlation(self.__dict__[f'stat{channel}'], 0)
        return self.__dict__[f'_probability{channel}']    
        
    def correlation_n(self, channel: int = 1, n: int = 100):
        """

        Parameters
        ----------
        values : list
            List of bins state from self.read_window().
        n : int
            Order of correlation.
            default is 100

        Returns
        -------
        string of 0-th to n-th correlators. Example: '0,0,0,1,0,0,1,1,0,0'

        """
        cor = []
        for i in range(n):
            cor.append(self.correlation(self.__dict__[f'stat{channel}'], i))
        ans = ''
        for i in cor:
            ans += f'{i},'
        return ans[:-1]
    
    def read_auto_correlator(self, channel: int = 1, iterat = 1, sh = 100):
        stat = self.read_window()
        n = np.arange(0, sh+1, 1)
        correlation = np.zeros_like(n, dtype = float)
        cor_n = self.correlation_n()
        print(cor_n)
        for i in range(iterat):
            cor = []
            stat = self.read_window()
            print(stat[:50])
            for i in n:
                cor.append(self.correlation(stat, i))
            cor = np.array(cor, dtype = float)
            correlation += cor
        
        correlation /= iterat
        
        m = correlation[0]
        print(f'Mean is {m}')
        m = np.ones_like(n) * m
        plt.plot(n, correlation, 'o-', label = 'Data', color = 'darkblue')
        plt.plot(n, m**2, '--', color = 'crimson', label = 'Uncorrelated', alpha = 0.5)
        plt.legend()
        plt.xlabel('n-th neighbor')
        plt.ylabel('Correlation')
        plt.show()
    
    def close(self):
        self.device.resource.close()
    
def main():
    device = Waverunner9000()
    
<<<<<<< HEAD
    device.read_auto_correlator(iterat = 10)
=======
    import pandas as pd
    import os
    
    folder = r'C:\Users\graphene\Desktop\Dima\Lab\Unisweep\Data\250123\data_files'
    filename = 'data7'
    
    filename = os.path.join(folder, f'{filename}.csv')
    
    t = device.Time1()
    a = device.Amplitude1()
    
    t = t.split(',')
    t = [float(i) for i in t]
    
    a = a.split(',')
    a = [float(i) for i in a]
    
    plt.plot(t, a)
    plt.show()
>>>>>>> 555c29c9bdf7e38315a660134f1ee159cc0af24a
    
    d = {'Time': t, 'Ampl': a}
    df = pd.DataFrame(d)
    df.to_csv(filename, index = False)
    device.close()

if __name__ == '__main__':
    main()