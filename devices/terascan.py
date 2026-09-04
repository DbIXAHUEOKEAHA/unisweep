'''
Unisweep driver for the TOPTICA TeraScan / TeraBeam cw-THz system (DLC smart THz).

Parameter names taken from "TeraScan / TeraBeam Remote Command Reference,
Firmware 3.1.1" (DLC_smart_THz-CommandReference-3_1_1.pdf).

Controls the photomixer: THz difference frequency (Precise Scan mode),
transmitter bias amplitude / offset ("Bias Out" SMB, lockin:mod-out-*) and
bias modulation frequency (lockin:frequency).  Also reads the receiver
photocurrent from the built-in lock-in.

Requirements:  pip install toptica-lasersdk

Address (Unisweep 'Devices' menu):
    'COM4' or 'ASRL4::INSTR'   -> serial, 115200 8N1 (your setup)
    '192.168.1.50[:1998]'      -> Ethernet command line (port 1998)

The connection is raised to user level 2 (maintenance) with the superuser
password so that read-write parameters can be set.
'''

import time
import re

from toptica.lasersdk.client import Client, NetworkConnection, SerialConnection
from toptica.lasersdk.client import UserLevel
from toptica.lasersdk.client import DecopError

P = {
    # identity
    'system_type':    'general:system-type',          # "DLCsmartTHz"
    'serial':         'general:serial-number',
    'fw':             'general:fw-ver',
    'profile':        'general:profiles:profile-caption',   # e.g. "THz: -50 .. 1300 GHz"
    # laser emission
    'emission_en':    'laser-operation:emission-global-enable',   # bool, rw
    'emission':       'laser-operation:emission',                 # bool, ro
    'interlock_open': 'laser-operation:interlock-open',
    # THz frequency (Precise Scan mode)
    'scan_mode_fast': 'frequency:scan-mode-fast',     # bool, must be #f for frequency-set
    'frequency':      'frequency:frequency-set',      # GHz, rw
    'frequency_act':  'frequency:frequency-act',      # GHz, ro
    # transmitter bias ("Bias Out")
    'bias_amplitude': 'lockin:mod-out-amplitude',     # V, rw
    'bias_offset':    'lockin:mod-out-offset',        # V, rw
    'bias_frequency': 'lockin:frequency',             # Hz, rw
    'bias_amp_def':   'lockin:mod-out-amplitude-default',
    'bias_off_def':   'lockin:mod-out-offset-default',
    # lock-in / photocurrent
    'lockin_phase':   'lockin:phase',                 # deg, rw
    'int_time':       'lockin:integration-time',      # ms, rw
    'amp_gain':       'lockin:amplifier-gain',        # V/A, rw
    'lockin_nA':      'lockin:lock-in-value-nanoamp', # (real bool), ro
    'lockin_V':       'lockin:lock-in-value',         # (real bool), ro
    'fpm_enabled':    'lockin:fast-phase-modulation:enabled',
}

CMD = {
    'lockin_reset':   'lockin:lock-in-reset',
    'bias_default':   'lockin:mod-out-set-to-default',
    'bias_zero':      'lockin:mod-out-set-to-zero',
}


class terascan():

    def __init__(self, adress='COM4', password='Toptica'):
        '''
        adress:   'COM4' / 'ASRL4::INSTR' or IP address
        password: superuser password -> user level 2 (maintenance)
        '''
        self.adress = adress
        self.open()

        try:
            ul = self.client.change_ul(UserLevel.MAINTENANCE, password)
            if ul != UserLevel.MAINTENANCE:
                print(f'terascan: user level is {ul.name}, expected MAINTENANCE; '
                      'set-commands may be rejected')
        except Exception as e:
            print(f'terascan: change_ul failed: {e}')

        # frequency-set only works in Precise Scan mode
        try:
            if self._get('scan_mode_fast', bool):
                self._set('scan_mode_fast', False)
        except DecopError as e:
            print(f'terascan: could not switch to Precise Scan mode: {e}')

        # ---------------- Unisweep interface ----------------
        self.set_options = ['frequency', 'bias_amplitude', 'bias_offset',
                            'bias_frequency']
        self.get_options = ['frequency', 'bias_amplitude',
                            'bias_offset', 'bias_frequency']
        self.loggable = ['IDN', 'profile', 'frequency', 'frequency_act',
                         'bias_amplitude', 'bias_offset', 'bias_frequency',
                         'emission', 'lockin_phase', 'integration_time',
                         'amplifier_gain']

        # aligned with set_options.  Nothing ramps on its own -> the sweeper
        # steps through values itself (sweepable = False).
        self.sweepable = [False] * len(self.set_options)
        self.maxspeed = [None] * len(self.set_options)
        self.eps = [0.01, 1e-3, 1e-3, 0.1, None, 0.1, 0.1, None]

        # extra wait after a frequency step (laser temperature settling)
        self.settle_time = 0.0

    # ------------------------------------------------------------------ #
    def open(self):
        a = str(self.adress).strip()
        m = re.match(r'ASRL(\d+)::INSTR', a, re.IGNORECASE)
        if m:
            a = f'COM{m.group(1)}'
        if a.upper().startswith('COM') or a.startswith('/dev/'):
            conn = SerialConnection(a, baudrate=115200)      # 8N1 by default
        elif ':' in a:
            host, port = a.split(':')
            conn = NetworkConnection(host, command_line_port=int(port))
        else:
            conn = NetworkConnection(a)
        self.client = Client(conn)
        self.client.open()

    def close(self):
        try:
            self.client.close()
        except Exception:
            pass

    def __del__(self):
        self.close()

    def _get(self, key, *types):
        ''' types: one type (float/int/str/bool) or several for tuple params '''
        if not types:
            types = (float,)
        return self.client.get(P[key], *types)

    def _set(self, key, value):
        rc = self.client.set(P[key], value)
        if rc == 2:
            print(f'terascan: {key} value {value} was clipped by the device '
                  f'-> now {self.client.get(P[key])}')
        return rc

    def _exec(self, key):
        return self.client.exec(CMD[key], return_type=int)

    # ------------------------------------------------------------------ #
    # get options
    # ------------------------------------------------------------------ #
    def IDN(self):
        return f"{self._get('system_type', str)} {self._get('serial', str)} fw {self._get('fw', str)}"

    def profile(self):
        return self._get('profile', str)

    def frequency(self):
        ''' actual THz frequency from measured laser temperatures, GHz '''
        return float(self._get('frequency_act'))

    def bias_amplitude(self):
        ''' Tx bias AC modulation amplitude, V '''
        return float(self._get('bias_amplitude'))

    def bias_offset(self):
        ''' Tx bias DC offset, V '''
        return float(self._get('bias_offset'))

    def bias_frequency(self):
        ''' Tx bias modulation frequency (= lock-in reference), Hz '''
        return float(self._get('bias_frequency'))

    def emission(self):
        ''' 1 if laser emission is on '''
        return int(bool(self._get('emission', bool)))

    def interlock_open(self):
        return int(bool(self._get('interlock_open', bool)))

    def lockin_phase(self):
        ''' lock-in reference phase, deg '''
        return float(self._get('lockin_phase'))

    def integration_time(self):
        ''' lock-in integration time, ms '''
        return float(self._get('int_time'))

    def amplifier_gain(self):
        ''' transimpedance amplifier gain used for nA conversion, V/A '''
        return float(self._get('amp_gain'))

    def _lockin_read(self, key):
        '''
        Reference manual sequence: reset lock-in, wait one integration time,
        read (value, valid) tuple.  Polls until valid.
        '''
        self._exec('lockin_reset')
        t_int = self.integration_time() * 1e-3
        time.sleep(t_int)
        for _ in range(50):
            value, valid = self._get(key, float, bool)
            if valid:
                return float(value)
            time.sleep(max(t_int / 10, 0.005))
        print('terascan: lock-in value never became valid')
        return float('nan')

    def photocurrent(self):
        ''' receiver THz photocurrent from the built-in lock-in, nA '''
        return self._lockin_read('lockin_nA')

    def photocurrent_V(self):
        ''' same, but as voltage at the DLC smart input, V '''
        return self._lockin_read('lockin_V')

    # ------------------------------------------------------------------ #
    # set options   (Unisweep calls set_x(value=..., speed=...))
    # ------------------------------------------------------------------ #
    def set_frequency(self, value=100.0, speed=None):
        ''' THz frequency, GHz '''
        self._set('frequency', float(value))
        if self.settle_time:
            time.sleep(self.settle_time)

    def set_bias_amplitude(self, value=0.0, speed=None):
        ''' Tx bias AC amplitude, V '''
        self._set('bias_amplitude', float(value))

    def set_bias_offset(self, value=0.0, speed=None):
        ''' Tx bias DC offset, V '''
        self._set('bias_offset', float(value))

    def set_bias_frequency(self, value=10e3, speed=None):
        ''' Tx bias modulation frequency, Hz '''
        self._set('bias_frequency', float(value))

    def set_emission(self, value=0, speed=None):
        ''' 1 -> enable laser emission, 0 -> disable '''
        self._set('emission_en', bool(int(float(value))))

    def set_lockin_phase(self, value=0.0, speed=None):
        self._set('lockin_phase', float(value))

    def set_integration_time(self, value=100.0, speed=None):
        ''' ms '''
        self._set('int_time', float(value))

    def set_amplifier_gain(self, value=1e6, speed=None):
        ''' V/A '''
        self._set('amp_gain', float(value))

    # convenience (not exposed as sweep options)
    def bias_to_default(self):
        ''' restore factory bias amplitude/offset '''
        self._exec('bias_default')

    def bias_to_zero(self):
        self._exec('bias_zero')

    def raw(self, command):
        ''' send a raw Scheme command, e.g. "(param-disp 'lockin)" '''
        conn = self.client.connection

        async def _q():
            await conn.write_command_line(command.rstrip() + '\n')
            return await conn.read_command_line()

        return self.client._async_run(_q())


def main():
    device = terascan(adress='COM4')
    for param in device.loggable:
        try:
            print(f'{param} = {getattr(device, param)()}')
        except Exception as e:
            print(f'{param}: {e}')
    print(f'photocurrent = {device.photocurrent()} nA')


if __name__ == '__main__':
    main()