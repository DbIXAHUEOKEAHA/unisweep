import nidaqmx
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from scipy.stats import binned_statistic
import pandas as pd
import os
import matplotlib as mpl
mpl.rcParams['agg.path.chunksize'] = 5000000

class NI_DAQ():
    
    def __init__(self, adress):
        self.name = adress
        self.task = nidaqmx.Task()
        self.rate = 51200
        self.n_sample = int(self.rate*10)
        for i in range(4):
            self.task.ai_channels.add_ai_voltage_chan(f'{self.name}/ai{i}')
            self.__dict__[f'ch{i}_mean'] = lambda i=i: self.ch_mean(i)
            self.__dict__[f'ch{i}_array'] = lambda i=i: self.ch_array(i)
        self.task.timing.cfg_samp_clk_timing(self.rate, samps_per_chan=self.n_sample)
        
        self.set_options = ['rate', 'n_sample']
        self.get_options = ['ch0_mean', 'ch1_mean', 'ch2_mean', 'ch3_mean', 
                            'ch0_array', 'ch1_array', 'ch2_array', 'ch3_array',
                            'rate', 'n_sample', 'time', 'n_statistics', 'raw_statistics']
        self.measured_array = [None, None, None, None]
        self.measured_mean = [None, None, None, None]
         
    def set_rate(self, value: float):
         self.rate = value
         self.task.timing.cfg_samp_clk_timing(int(self.rate))
         print(f'Rate was set to {self.rate}')
         
    def set_n_sample(self, value: float):
        self.n_sample = int(value)
        print(f'N_sample was set to {self.n_sample}')
        
    def rate(self):
        return self.rate
    
    def n_sample(self):
        return self.n_sample
    
    def time(self):
        _time = (np.arange(self.n_sample) + 1) / self.rate
        _time = np.array(_time, dtype = str)
        time = ''
        for t in _time:
            time += t
            time += ','
        time = time[:-1]
        return time
    
    def ch_mean(self, i):
        if self.measured_mean[i] == None:
            self.measured_mean = self.task.read(self.n_sample)
            self.close()
            self.task = nidaqmx.Task()
            for j in range(4):
                self.task.ai_channels.add_ai_voltage_chan(f'{self.name}/ai{j}')
            self.task.timing.cfg_samp_clk_timing(self.rate, samps_per_chan=self.n_sample)
        answer = self.measured_mean[i]
        self.measured_mean[i] = None
        answer = np.array(answer).mean()
        return answer
    
    def ch_array(self, i):
        if self.measured_array[i] == None:
            self.measured_array = self.task.read(self.n_sample)
            self.close()
            self.task = nidaqmx.Task()
            for j in range(4):
                self.task.ai_channels.add_ai_voltage_chan(f'{self.name}/ai{j}')
            self.task.timing.cfg_samp_clk_timing(self.rate, samps_per_chan=self.n_sample)
        answer = self.measured_array[i]
        answer = np.array(answer, dtype = str)
        self.measured_array[i] = None
        ans = ''
        for a in answer:
            ans += str(a)
            ans += ','
        try:
            answer = answer.replace(' ', '')
        except:
            pass
        ans = ans[:-1]
        return ans
    
    def n_statistics(self):
        ch0 = []
        ch1 = []
        
        for j in range(1):
        
            _ch0 = [float(i)/0.56075 for i in self.ch0_array().split(',')]
            _ch1 = [float(i)*500 for i in self.ch1_array().split(',')]
            ch0 = np.concatenate((ch0, _ch0))
            ch1 = np.concatenate((ch1, _ch1))
            
        Idc = ch1
        Vtg = ch0
        t = np.arange(Idc.shape[0])/5.12
        
        ###########
        
        fig, ax = plt.subplots()
        ax.plot(t[:2000], Vtg[:2000], '-', color = 'darkblue')
        # Axis labels

        ax.set_xlabel(r"Time, $t$ (ms)", fontsize=14)
        ax.set_ylabel(r"TG voltage, $V_{tg}$ (V)", fontsize=14)

        # Title (optional, often omitted in publications)
        # ax.set_title("Gate voltage vs Current", fontsize=14, fontweight='bold')

        # Ticks and tick labels
        ax.tick_params(axis='both', which='major', direction='out', length=8, width=1.2,
                       labelsize=12, top=False, right=False)   # major ticks

        #Add text
        #ax.text(0.5, 0.1, r"$T = 10\ \mathrm{K}$, THz on", 
        #        transform=ax.transAxes, fontsize=13, 
        #        verticalalignment='top', horizontalalignment='left')

        # Add minor ticks
        ax.minorticks_off()

        # Legend
        ax.legend(frameon=False, fontsize=12)

        # Grid (light, optional)
        ax.grid(False)

        ###

        fig2, ax2 = plt.subplots()
        ax2.plot(t[:2000], Idc[:2000], '-', color = 'darkblue')
        # Axis labels

        ax2.set_xlabel(r"Time, $t$ (ms)", fontsize=14)
        ax2.set_ylabel(r"SD current, $I_{sd}$ (µA)", fontsize=14)

        # Title (optional, often omitted in publications)
        # ax.set_title("Gate voltage vs Current", fontsize=14, fontweight='bold')

        # Ticks and tick labels
        ax2.tick_params(axis='both', which='major', direction='out', length=8, width=1.2,
                       labelsize=12, top=False, right=False)   # major ticks

        #Add text
        #ax.text(0.5, 0.1, r"$T = 10\ \mathrm{K}$, THz on", 
        #        transform=ax.transAxes, fontsize=13, 
        #        verticalalignment='top', horizontalalignment='left')

        # Add minor ticks
        ax2.minorticks_off()

        # Legend
        ax2.legend(frameon=False, fontsize=12)

        # Grid (light, optional)
        ax2.grid(False)

        # Adjust layout
        plt.tight_layout()
        ###########

        folder = r'D:\Unisweep\Data\250919'
        df = pd.DataFrame({'Time, t': t, 'Vtg': Vtg, 'I': Idc})
        #df.to_csv(os.path.join(folder, f'Loop_200Hz.csv'), index = False) 
        
        Idc_cutoff = -4
        bins = 1
        stat, bin_edges, bin_number = binned_statistic(t, Idc, bins = bins, statistic = lambda x: np.sum(x<Idc_cutoff)) #counts how many points are above the cutoff
        
        return stat[0] / 450000
    
    def raw_statistics(self):
        ch0 = []
        ch1 = []
        
        for j in range(5):
           
            _ch0 = [float(i)/0.56075 for i in self.ch0_array().split(',')]
            _ch1 = [float(i)*500 for i in self.ch1_array().split(',')]
            ch0 = np.concatenate((ch0, _ch0))
            ch1 = np.concatenate((ch1, _ch1))
            
        Idc = ch1
        Vtg = ch0
        
        folder = r'D:\Unisweep\Data\250914'
        files = os.listdir(folder)
        idx=[]
        for f in files:
            if '.csv' in f:
                idx.append(f[len(f)-f[::-1].index('-'):-4])
        print(idx)
        idx = np.array(list(map(int, idx)))
        df = pd.DataFrame({'I': Idc, 'Vtg': Vtg})
        df.to_csv(os.path.join(folder, f'file-{np.max(idx)+1}.csv'), index = False)
        
        
        return np.nan

    def close(self):
        self.task.close()
        
    def clear(self):
        self.measured_array = [None, None, None, None]
        self.measured_mean = [None, None, None, None]
    
def main():
    name = 'cDAQ1Mod1'
    device = NI_DAQ(name)
    
    print(device.n_statistics())

if __name__ == '__main__':
    main()
         