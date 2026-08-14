from pathlib import Path, PureWindowsPath
from enum    import Enum
from rohdeschwarz.general                       import SiPrefix
from rohdeschwarz.general                       import unique_alphanumeric_string
from rohdeschwarz.instruments.genericinstrument import GenericInstrument
from rohdeschwarz.instruments.vna.calunit       import CalUnit
from rohdeschwarz.instruments.vna.channel       import Channel
from rohdeschwarz.instruments.vna.diagram       import Diagram
from rohdeschwarz.instruments.vna.trace         import Trace
from rohdeschwarz.instruments.vna.properties    import Properties
from rohdeschwarz.instruments.vna.settings      import Settings
from rohdeschwarz.instruments.vna.filesystem    import FileSystem, Directory

import numpy as np
np.set_printoptions(threshold=1e9)
import time

class myTrace(Trace):
    
    def measure_complex_data(self):
        channel = self._vna.channel(self.channel)
        is_manual = channel.manual_sweep
        channel.manual_sweep = True
        channel.start_sweep()
        y = self.y_complex
        channel.manual_sweep = is_manual
        return y

class ImageFormat(Enum):
    bmp = 'BMP'
    png = 'PNG'
    jpg = 'JPG'
    pdf = 'PDF'
    svg = 'SVG'
    def __str__(self):
        return self.value

class Vna(GenericInstrument):
    def __init__(self, adress):
        super(Vna, self).__init__()
        self.properties = Properties(self)
        self.settings = Settings(self)
        self.file = FileSystem(self)
        if ':' in adress and '::' not in adress:
            ip_address, socket = adress.split(':')
            socket = int(socket)
            self._open(ip_address, socket)
        else:
            self._open(adress)
        #self.display_screen()
        
        self.complex_number = [None, None]
        self.complex_linmag = [None, None]
        self.complex_linmag_peak = [None, None]
        self.complex_peak = [None, None]
        self.complex_dip = [None, None]
        self.complex_average = [None, None]
        
        self.cur_average = 1 #Default number of measurements to AVERAGE
        
        self.get_options = ['start_freq', 'stop_freq', 'cent_freq', 'span_freq', 'sweep_time', 'num_points', 'bandwidth', 'average', 'power', 
                            'freqs', 'average_real', 'average_im', 'trace_real', 'trace_im', 'trace_linmag', 'trace_logmag', 'trace_phase', 
                            'real_peak_freq', 'real_dip_freq', 'im_peak_freq', 'im_dip_freq', 'linmag_peak_freq', 'max_linmag_freq']
        self.set_options = ['start_freq', 'stop_freq', 'cent_freq', 'span_freq', 'num_points', 'bandwidth', 'average', 'power']

    def _open(self, ip_address: str, socket:int):
        self.open_tcp(ip_address, socket)

    def __del__(self):
        if self.connected():
            self.local()
            self.close()
            
    def display_screen(self):
        scpi = 'SYST:DISP:UPD 1'
        self.write(scpi)
        
    def autoscale(self):
        scpi = 'DISP:WIND:TRAC:Y:AUTO ONCE'
        self.write(scpi)

    def array_to_string(self, array):
        return ','.join(map(str, array))

    def print_info(self):
        _log = self.log
        self.log = None
        _log.write('VNA INSTRUMENT INFO\n')
        if self.connected() and self.properties.is_known_model():
            _log.write('Connection:       {0}\n'.format(self.connection_method))
            _log.write('Address:          {0}\n'.format(self.address))
            _log.write('Make:             Rohde & Schwarz\n')
            _log.write('Model:            {0}\n'.format(self.properties.model))
            _log.write('Serial No:        {0}\n'.format(self.properties.serial_number))
            _log.write('Firmware Version: {0}\n'.format(self.properties.firmware_version))
            value, prefix = SiPrefix.convert(self.properties.minimum_frequency_Hz)
            _log.write('Min Frequency:    {0} {1}Hz\n'.format(value, prefix))
            value, prefix = SiPrefix.convert(self.properties.maximum_frequency_Hz)
            _log.write('Max Frequency:    {0} {1}Hz\n'.format(value, prefix))
            _log.write('Number of Ports:  {0}\n'.format(self.properties.physical_ports))
            options = self.properties.options_list
            if options:
                _log.write('Options:          ')
                _log.write('\n                  '.join(options))
                _log.write('\n')
        elif self.connected():
            _log.write('Make: Unknown\n')
            _log.write('*IDN?\n  {0}\n'.format(self.id_string()))
        else:
            _log.write('Instrument not found!\n')
            _log.write('Connection:       {0}\n'.format(self.connection_method))
            _log.write('Address:          {0}\n'.format(self.address))
        _log.write('\n\n')
        self.log = _log

    ### Channels
    def is_channel(self, index):
        return index in self._channels()

    def _channels(self):
        result = self.query(':CONF:CHAN:CAT?')
        result = result.strip().strip("'")
        if len(result) == 0:
            return []
        result = result.split(",")
        result = result[::2]
        return list(map(int, result))
    def _set_channels(self, channels):
        _allChannels = self._channels()
        for c in channels:
            if c not in _allChannels:
                self.create_channel(c)
        for c in _allChannels:
            if c not in channels:
                self.delete_channel(c)
    channels = property(_channels, _set_channels)

    def create_channel(self, index=None):
        if not index:
            _channels = self._channels()
            if len(_channels) == 0:
                index = 1
            else:
                index = _channels[-1] + 1
        self.write(':CONF:CHAN{0} 1'.format(index))
        return index

    def copy_channel(self, original_index, new_index=None):
        self.channel(original_index).select()
        if not new_index:
            return self.create_channel()
        else:
            self.create_channel(new_index)

    def delete_channel(self, index):
        self.write(':CONF:CHAN{0} 0'.format(index))

    def delete_channels(self, indexes):
        for i in indexes:
            self.delete_channel(i)

    def channel(self, index=1):
        return Channel(self, index)


    ### Traces
    def is_trace(self, name):
        return name in self._traces()

    def _traces(self):
        result = self.query(':CONF:TRAC:CAT?').strip().strip("'")
        if len(result) == 0:
            return []
        result = result.split(",")
        return result[1::2]
    def _set_traces(self, traces):
        _allTraces = self._traces()
        for t in traces:
            if t not in _allTraces:
                self.create_trace(name=t)
        for t in _allTraces:
            if t not in traces:
                self.delete_trace(name=t)
    traces = property(_traces, _set_traces)

    def create_trace(self, name=None, channel=1, parameter = 'S11'):
        if not name:
            traces = self.traces
            name = 'Trc1'
            i = 2
            while name in traces:
                name = 'Trc{0}'.format(i)
                i += 1
            scpi = ":CALC{0}:PAR:SDEF '{1}', '{2}'"
            scpi = scpi.format(channel, name, parameter) # Fix
            self.write(scpi)
            return name
        else:
            scpi = ":CALC{0}:PAR:SDEF '{1}', '{2}'"
            scpi = scpi.format(channel, name, parameter) # Fix
            self.write(scpi)

    def delete_trace(self, name):
        _channel = self.trace(name).channel
        scpi = ":CALC{0}:PAR:DEL '{1}'"
        scpi = scpi.format(_channel, name)
        self.write(scpi)

    def delete_traces(self):
        for t in self._traces():
            self.delete_trace(t)

    def trace(self, name='Trc1'):
        return Trace(self, name)

    ### Diagrams
    def is_diagram(self, index):
        return index in self._diagrams()

    def _diagrams(self):
        result = self.query(':DISP:CAT?').strip().strip("'")
        if len(result) == 0:
            return []
        result = result.split(',')
        result = result[::2]
        return list(map(int, result))

    def _set_diagrams(self, diagrams):
        _allDiagrams = self._diagrams()
        while len(diagrams) > len(_allDiagrams):
            _allDiagrams.append(self.create_diagram())
        while len(diagrams) < len(_allDiagrams):
            self.delete_diagram(_allDiagrams[-1])
            _allDiagrams.pop(-1)

    diagrams = property(_diagrams, _set_diagrams)

    def create_diagram(self, index=None):
        if not index:
            _diagrams = self._diagrams()
            if len(_diagrams) == 0:
                index = 1
            else:
                index = _diagrams[-1] + 1
        self.write(':DISP:WIND{0}:STAT 1'.format(index))
        return index

    def delete_diagram(self, index):
        self.write(':DISP:WIND{0}:STAT 0'.format(index))

    def delete_diagrams(self):
        _diagrams = self._diagrams()
        while len(_diagrams) > 1:
            self.delete_diagram(_diagrams[-1])
            _diagrams = self._diagrams()

    def diagram(self, index=1):
        return Diagram(self, index)


    ### Sets
    def __add_set_suffix(self, name):
        path = PureWindowsPath(name.lower())
        if self.properties.is_zvx():
            suffix    = '.zvx'
            is_suffix = path.suffix == suffix
            if not is_suffix:
                name += suffix
            return name
        if self.properties.is_znx():
            suffixes  = ['.znx', '.znxml']
            is_suffix = path.suffix in suffixes
            if not is_suffix:
                name += suffixes[0]
            return name
        # else unknown model, do nothing to name
        return name

    def create_set(self, name=None):
        if name:
            scpi = ":MEM:DEF '{0}'".format(name)
            self.write(scpi)
        else:
            sets = self.sets
            name = 'Set1'
            i = 2
            while name in sets:
                name = "Set{0}".format(i)
                i += 1
            scpi = ":MEM:DEF '{0}'"
            scpi = scpi.format(name)
            self.write(scpi)
            return name

    def open_set(self, name):
        # filename must include suffix
        name = self.__add_set_suffix(name)

        # file exists?
        restore_dir = None
        if not self.file.is_file(name):
            # try recallsets folder
            restore_dir = self.file.directory()
            self.file.cd(Directory.recall_sets)

        scpi = ":MMEM:LOAD:STAT 1,'{0}'".format(name)
        self.write(scpi)

        # restore directory?
        if restore_dir:
            self.file.cd(restore_dir)

    def open_set_locally(self, name):
        # name must include suffix
        name = self.__add_set_suffix(name)

        # cd into RecallSets
        restore_dir = self.file.directory()
        self.file.cd(Directory.recall_sets)

        # upload set file
        filename = Path(name).name
        self.file.upload_file(name, filename)
        self.pause(10000)

        # open set
        self.open_set(filename)

        # restore dir
        self.file.cd(restore_dir)

    def _sets(self):
        result = self.query(":MEM:CAT?")
        result = result.strip().replace("'","")
        if not result:
            return []
        result = result.split(',')
        return result
    sets = property(_sets)

    def _set_active_set(self, name):
        scpi = ":MEM:SEL '{0}'"
        scpi = scpi.format(name)
        self.write(scpi)
    def _active_set(self):
        sets = self.sets
        if len(sets) == 0:
            return None
        if len(sets) == 1:
            return sets[0]

        # create unique trace name
        unique_trace_name = 'Trc' + unique_alphanumeric_string()
        self.create_trace(unique_trace_name, self.channels[0])
        for set in sets:
            self.active_set = set
            if unique_trace_name in self.traces:
                self.delete_trace(unique_trace_name)
                return set
        return None
    active_set = property(_active_set, _set_active_set)

    def save_active_set(self, path):
        # must include suffix
        path = self.__add_set_suffix(path)

        # directory
        dir    = PureWindowsPath(path).parent
        is_dir = str(dir) != '.'

        # change directory
        restore_dir = None
        if not is_dir:
            restore_dir = self.file.directory()
            self.file.cd(Directory.recall_sets)

        scpi = ":MMEM:STOR:STAT 1,'{0}'"
        scpi = scpi.format(path)
        self.write(scpi)
        self.pause()

        if restore_dir:
            self.file.cd(restore_dir)

    def save_active_set_locally(self, filename):
        # must include suffix
        filename  = self.__add_set_suffix(filename)
        suffix    = Path(filename).suffix

        # save on VNA in RecallSets
        temp_file = unique_alphanumeric_string() + suffix
        self.save_active_set(temp_file)

        # cd into RecallSets
        restore_dir = self.file.directory()
        self.file.cd(Directory.recall_sets)

        # download set file
        self.file.download_file(temp_file, filename)

        # delete temp file from VNA
        self.file.delete(temp_file)

        # restore dir
        self.file.cd(restore_dir)

    def close_set(self, name):
        scpi = ":MEM:DEL '{0}'".format(name)
        self.write(scpi)

    def close_sets(self):
        sets = self.sets
        for set in sets:
            self.close_set(set)

    def delete_set(self, name):
        # must have suffix
        name   = self.__add_set_suffix(name)

        # directory
        dir    = PureWindowsPath(name).parent
        is_dir = dir != '.'

        # cd into RecallSets?
        restore_dir = None
        if not is_dir:
            restore_dir = self.file.directory()
            self.file.cd(Directory.recall_sets)

        # delete file
        self.file.delete(name)

        # restore directory?
        if restore_dir:
            self.file.cd(restore_dir)

    ### Cal groups
    def is_cal_group(self, name):
        name = name.lower()
        if name.endswith('.cal'):
            name = name[:-4]
        cal_groups = [i.lower() for i in self.cal_groups]
        return name in cal_groups

    def _cal_groups(self):
        current_dir = self.file.directory()
        self.file.cd(Directory.cal_groups)
        cal_groups = self.file.files()
        def is_cal(filename):
            return filename.lower().endswith('.cal')
        cal_groups = list(filter(is_cal, cal_groups))
        cal_groups = [name[:-4] for name in cal_groups]
        self.file.cd(current_dir)
        return cal_groups
    cal_groups = property(_cal_groups)

    # cal units
    def _cal_units(self):
        results = self.query(':SYST:COMM:RDEV:AKAL:ADDR:ALL?')
        results = results.strip().strip("'")
        if not results:
            return []
        else:
            return [unit.strip("'") for unit in results.split(',')]
    cal_units = property(_cal_units)
    def cal_unit(self, id=None):
        return CalUnit(self, id)

    # power sensors
    def _power_sensors(self):
        scpi = 'SYST:COMM:RDEV:PMET:CAT?'
        sensors = self.query(scpi)
        sensors = sensors.strip().split(',')
        return [int(i) for i in sensors if i]
    power_sensors = property(_power_sensors)

    ### General
    def _sweep_time_ms(self):
        sweep_time_ms = 0
        channels = self.channels
        for i in channels:
            sweep_time_ms += self.channel(i).total_sweep_time_ms
        return sweep_time_ms
    sweep_time_ms = property(_sweep_time_ms)

    def _is_manual_sweep(self):
        for c in self.channels:
            if not self.channel(c).manual_sweep:
                return False
        return True
    def _set_manual_sweep(self, value):
        for c in self.channels:
            self.channel(c).manual_sweep = value
    manual_sweep = property(_is_manual_sweep, _set_manual_sweep)

    def _is_continuous_sweep(self):
        for c in self.channels:
            if not self.channel(c).continuous_sweep:
                return False
        return True
    def _set_continuous_sweep(self, value):
        for c in self.channels:
            self.channel(c).continuous_sweep = value
    continuous_sweep = property(_is_continuous_sweep, _set_continuous_sweep)


    def start_sweeps(self):
        if self.properties.is_zvx():
            self.write(':INIT:CONT 0')
            self.write(':INIT:SCOP ALL')
            self.write(":INIT")
            return
        # else
        self.write(':INIT:CONT:ALL 0')
        self.write(":INIT:ALL")

    def sweep(self):
        self.manual_sweep = True
        timeout_ms = 2 * self.sweep_time_ms + 5000
        self.start_sweeps()
        self.pause(timeout_ms)

    def _sweep_count(self):
        indexes = self.channels
        sweep_count = self.channel(indexes.pop(0)).sweep_count
        for i in indexes:
            if self.channel(i).sweep_count != sweep_count:
                raise ValueError('channel sweep counts are not equal')
        return sweep_count
    def _set_sweep_count(self, sweep_count):
        for index in self.channels:
            self.channel(index).sweep_count = sweep_count
    sweep_count = property(_sweep_count, _set_sweep_count)


    def _test_ports(self):
        if self.properties.is_zvx():
            return self.properties.physical_ports
        else:
            scpi = ':INST:TPORT:COUN?'
            result = self.query(scpi)
            return int(result.strip())
    test_ports = property(_test_ports)

    def is_limits(self):
        for i in self.traces:
            t = self.trace(i)
            if t.limits.on:
                return True
        # else
        return False

    def _passed(self):
        scpi = ":CALC:CLIM:FAIL?"
        return self.query(scpi).strip() == "0"
    passed = property(_passed)
    def _failed(self):
        return not self.passed
    failed = property(_failed)

    def save_screenshot(self, filename, image_format='JPG'):
        extension = ".{0}".format(image_format).lower()
        if not filename.lower().endswith(extension):
            filename += extension
        scpi = ":MMEM:NAME '{0}'"
        scpi = scpi.format(filename)
        self.write(scpi)
        scpi = ":HCOP:DEV:LANG {0}"
        scpi = scpi.format(image_format)
        self.write(scpi)
        self.write(":HCOP:PAGE:WIND ALL")
        self.write("HCOP:DEST 'MMEM'")
        self.write(":HCOP")
        self.pause(5000)
        return self.file.is_file(filename)
    def save_screenshot_locally(self, filename, image_format='JPG'):
        extension = "." + str(image_format).lower()
        unique_filename = unique_alphanumeric_string() + extension
        if not filename.lower().endswith(extension):
            filename += extension
        if self.save_screenshot(unique_filename, image_format):
            self.file.download_file(unique_filename, filename)
            self.file.delete(unique_filename)
            return True
        else:
            return False
    
    def start_freq(self):
        scpi = 'FREQ:START?'
        return self.query(scpi)
    
    def stop_freq(self):
        scpi = 'FREQ:STOP?'
        return self.query(scpi)
    
    def cent_freq(self):
        scpi = 'FREQ:CENT?'
        return self.query(scpi)
    
    def span_freq(self):
        scpi = 'FREQ:SPAN?'
        return self.query(scpi)
    
    def set_start_freq(self, value):
        scpi = f'FREQ:START {value}'
        self.write(scpi)
        
    def set_stop_freq(self, value):
        scpi = f'FREQ:STOP {value}'
        self.write(scpi)
        
    def set_span_freq(self, value):
        scpi = f'FREQ:SPAN {value}'
        self.write(scpi)
        
    def set_cent_freq(self, value):
        scpi = f'FREQ:CENT {value}'
        self.write(scpi)
        
    def power(self):
        scpi = 'SOUR:POW?'
        return self.query(scpi)
    
    def average(self):
        return self.cur_average
    
    def set_average(self, value):
        try:
            self.cur_average = int(value)
        except ValueError:
            self.cur_average = 3
    
    def set_power(self, value):
        scpi = f'SOUR:POW {value}'
        self.write(scpi)
        
    def set_directory(self, value):
        scpi = f'MMEM:CDIR {value}'
        self.write(scpi)

    def create_file(self, value):
        scpi = f"MMEM:NAME '{value}'"
        self.write(scpi)

    def get_data(self, value):
        scpi = f'MMEM:DATA \'{value}\',#220'
        self.write(scpi)
        
    def start_sweep(self):
        scpi = 'INIT1:IMM'
        self.write(scpi)
        
    def trace_data(self):
        scpi = 'CALC1:DATA? FDAT'
        return self.query(scpi)
    
    def sweep_time(self):
        scpi = 'SENSE1:SWEEP:TIME?'
        return float(self.query(scpi))
    
    def trac(self):
        data = myTrace(self, 'Trc1')
        complex_trace = data.measure_complex_data()
        num = [complex_trace.real, complex_trace.imag]
        self.complex_number = num
        self.complex_linmag = num
        self.complex_linmag_peak = num
        self.complex_peak = num
        self.complex_dip = num
        
    def average_trac(self):
        """

        Parameters
        ----------
        n : int
            Average count.

        Returns
        -------
        Complex trace after averaging

        """
        n = self.cur_average
        num = [0, 0]
        for i in range(n):
            data = myTrace(self, 'Trc1')
            complex_trace = data.measure_complex_data()
            num = [num[0] + complex_trace.real, num[1] + complex_trace.imag]
        num = [num[0] / n, num[1] / n]
        self.complex_average = num
    
    def average_real(self):
        if self.complex_average[0] is None:
            self.average_trac()
        answer = self.complex_average[0]
        self.complex_average[0] = None
        return self.array_to_string(answer)
    
    def average_im(self):
        if self.complex_average[1] is None:
            self.average_trac()
        answer = self.complex_average[1]
        self.complex_average[1] = None
        return self.array_to_string(answer)
    
    def trace_real(self):
        if self.complex_number[0] is None:
            self.trac()
        answer = self.complex_number[0]
        self.complex_number[0] = None
        return self.array_to_string(answer)
    
    def trace_im(self):
        if self.complex_number[1] is None:
            self.trac()
        answer = self.complex_number[1]
        self.complex_number[1] = None
        return self.array_to_string(answer)
    
    def trace_linmag(self):
        if self.complex_linmag[0] is None:
            self.trac()
        answer = np.sqrt(self.complex_linmag[0] ** 2 + self.complex_linmag[0] ** 2)
        self.complex_linmag[0] = None
        return self.array_to_string(answer)
    
    def trace_logmag(self):
        self.autoscale()
        scpi = 'INIT1:IMM:ALL'
        self.write(scpi)
        t = self.sweep_time()
        time.sleep(t)
        scpi = 'CALC1:FORM MLOG'
        self.write(scpi)
        scpi = 'CALC1:DATA? FDAT'
        answer = self.query(scpi)
        answer = answer.replace('\r', '')
        answer = answer.replace('\n', '')
        answer = answer.replace(' ', '')
        return answer
    
    def trace_phase(self):
        self.autoscale()
        scpi = 'INIT1:IMM:ALL'
        self.write(scpi)
        t = self.sweep_time()
        time.sleep(t)
        scpi = 'CALC1:FORM PHAS'
        self.write(scpi)
        scpi = 'CALC1:DATA? FDAT'
        answer = self.query(scpi)
        answer = answer.replace('\r', '')
        answer = answer.replace('\n', '')
        answer = answer.replace(' ', '')
        return answer
    
    def num_points(self):
        scpi = 'SWE:POIN?'
        return self.query(scpi)

    def set_num_points(self, value):
        scpi = f'SWE:POIN {value}'
        self.write(scpi)
        
    def bandwidth(self):
        scpi = 'BAND?'
        return self.query(scpi)
    
    def set_bandwidth(self, value):
        scpi = f'BAND {value}'
        self.write(scpi)
        
    def trig(self):
        scpi = '*TRG'
        self.write(scpi)
        
    def freqs(self):
        start = self.start_freq()
        stop = self.stop_freq()
        num = self.num_points()
        
        f = np.linspace(float(start), float(stop), int(num))
        f = np.array2string(f, separator = ',')[1:-1]
        f = f.replace('\r', '')
        f = f.replace('\n', '')
        f = f.replace(' ', '')
        
        return f
        
    '''
    def reverse_sweep(self, start, stop, num_points):
        "returns tuple ([freq], [real], [imag])"
        points = np.linspace(start, stop, num_points)
        delta = (stop - start) / num_points
        freq = []
        trace_real = []
        trace_im = []
        for ind, point in enumerate(points[::-1]):
            self.set_start_freq(point + delta)
            self.set_stop_freq(points[::-1][ind])
            self.set_num_points(1)
            self.start_sweep()
            freq.append(point)
            trace_real.append(self.trace_real())
            trace_im.append(self.trace_im())
        
        return freq, trace_real, trace_im
    '''
    
    def fit(self, x, y):
        
        from scipy.signal import find_peaks
        
        peaks_pos = find_peaks(y)[0]
        
        try:
            max_peak_pos = peaks_pos[0]
        except IndexError:
            return x[x.shape[0] // 2], x[x.shape[0] // 2], np.max(y), np.max(y)
        

        for pos in peaks_pos:
            if y[pos] > y[max_peak_pos]:
                max_peak_pos = pos
            
        dips_pos = find_peaks([-i for i in y])[0]
        
        try:
            min_dip_pos = dips_pos[0]
        except IndexError:
            return x[x.shape[0] // 2], x[x.shape[0] // 2], np.max(y), np.max(y)
            
        
        for pos in dips_pos:
            if y[pos] < y[min_dip_pos]:
                min_dip_pos = pos
        
        return x[max_peak_pos], x[min_dip_pos], y[max_peak_pos], y[min_dip_pos]
    
    def calculate_span_peak(self, x, y):
        from scipy.signal import find_peaks, peak_widths
        
        y = [float(i) for i in y]
        
        peaks_pos = find_peaks(y)[0]
        
        try:
            max_peak_pos = peaks_pos[0]
        except IndexError:
            return self.span_freq() // 10
        
        for pos in peaks_pos:
            if y[pos] > y[max_peak_pos]:
                max_peak_pos = pos
        
        n = peak_widths(y, [max_peak_pos])[0][0]
        
        span = float(self.span_freq())
        
        npoints = float(self.num_points())
        
        n = float(n)
        
        n = span * n / npoints
        
        return n
    
    def max_linmag_freq(self):
        x = self.freqs().split(',')
        
        if self.complex_linmag_peak[0] is None:
            self.trac()
        answer = np.sqrt(self.complex_linmag[0] ** 2 + self.complex_linmag[0] ** 2)
        self.complex_linmag_peak[0] = None
        
        idx = np.argmax(answer)
        return x[idx]
    
    def real_peak_freq(self):
        f = self.freqs().split(',')
        f = np.array([float(i) for i in f])
        
        if self.complex_peak[0] is None:
            self.trac()
        answer = self.complex_peak[0]
        self.complex_peak[0] = None
        
        return self.fit(f, answer)[0]
    
    def im_peak_freq(self):
        f = self.freqs().split(',')
        f = np.array([float(i) for i in f])
        
        if self.complex_peak[1] is None:
            self.trac()
        answer = self.complex_peak[1]
        self.complex_peak[1] = None
        
        return self.fit(f, answer)[0]
    
    def real_dip_freq(self):
        f = self.freqs().split(',')
        f = np.array([float(i) for i in f])
        
        if self.complex_dip[0]is None:
            self.trac()
        answer = self.complex_dip[0]
        self.complex_dip[0] = None
        
        return self.fit(f, answer)[1]
    
    def im_dip_freq(self):
        f = self.freqs().split(',')
        f = np.array([float(i) for i in f])
        
        if self.complex_dip[1] is None:
            self.trac()
        answer = self.complex_dip[1]
        self.complex_dip[1] = None
        
        return self.fit(f, answer)[1]
    
    def linmag_peak(self):
        f = self.freqs().split(',')
        f = np.array([float(i) for i in f])
        ans = self.fit(f, self.trace_linmag().split(','))
        return (ans[0], ans[2])
    
    def linmag_span(self):
        f = self.freqs().split(',')
        f = np.array([float(i) for i in f])
        ans = self.calculate_span_peak(f, self.trace_linmag().split(','))
        return ans
    
    def linmag_dip(self):
        f = self.freqs().split(',')
        f = np.array([float(i) for i in f])
        ans = self.fit(f, self.trace_linmag().split(','))
        return (ans[1], ans[3])
    
    def linmag_peak_freq(self):
        f = self.freqs().split(',')
        f = np.array([float(i) for i in f])
        return self.fit(f, self.trace_linmag().split(','))[0]
    
    def linmag_dip_freq(self):
        f = self.freqs().split(',')
        f = np.array([float(i) for i in f])
        return self.fit(f, self.trace_linmag().split(','))[0]
     
def main():
    vna = Vna('169.254.169.168:5025')
    try:
        print(vna.im_peak_freq())
    except Exception as ex:
        print(ex)
    finally:
        vna.close()
    
if __name__ == '__main__':       
    main()