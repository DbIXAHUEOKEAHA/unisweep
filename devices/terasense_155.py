'''
Unisweep driver for the TeraSense Tunable Sub-Terahertz Wave Source, 140-155 GHz
(User Manual Rev. 2026-08-20).

The system is two USB instruments:
    Oscillator          7.3 - 14.6 GHz synthesizer   (*IDN? -> TeraSense,SYF12P5V1,...)
    Amplifier/Multiplier x12, output WR6.5           (*IDN? -> TeraSense,AM24F12P10,...)

Output frequency = 12 x oscillator frequency.  Output power in dBm is set on the
amplifier, which runs its own ALC.

Port settings (both devices, FTDI virtual COM port):
    115200 baud, 8 data bits, no parity, 1 stop bit, no flow control,
    terminator '\\r' (0x0D).

Requirements:  pip install pyserial

Address (Unisweep 'Devices' menu), oscillator first:
    'COM5,COM6'          -> explicit ports; the driver checks *IDN? and swaps
                            them if they are the other way round
    'COM5'               -> one port only: whichever device answers is used,
                            the missing half is simply unavailable
    'auto'               -> scan all serial ports and find both devices

Important, from the manual
--------------------------
The amplifier's internal power detector is calibrated against the LO frequency it
has been told about.  set_frequency() therefore always writes the new frequency to
the amplifier as well; otherwise the power readings and the ALC would be wrong.

Setting power in dBm turns ALC on automatically; setting it in percent turns ALC
off.  The minimum settable power is -10 dBm and the maximum depends on frequency,
so a request that is too high leaves ALC reporting 'L' (output too low) rather
than failing - check ALC_status() after a large step.
'''

import time

import serial
import serial.tools.list_ports

MULTIPLIER = 12                     # x12 frequency multiplier
F_MIN_GHZ = 140.0                   # output frequency range of the system
F_MAX_GHZ = 155.0
P_MIN_DBM = -10.0                   # manual: minimum settable power
P_MAX_DBM = 20.0                    # ~100 mW; the real limit depends on frequency

OSC_ID = 'SYF12'                    # substring of the oscillator's *IDN?
AMP_ID = 'AM24F12'                  # substring of the amplifier's *IDN?


class terasense_155():

    def __init__(self, adress='auto', timeout=1.0):
        self.adress = adress
        self.timeout = timeout
        self.osc = None              # oscillator serial port
        self.amp = None              # amplifier/multiplier serial port
        self.open()

        # ---------------- Unisweep interface ----------------
        self.set_options = ['frequency', 'power', 'output', 'ALC',
                            'modulation', 'reference', 'power_percent']
        self.get_options = ['frequency', 'frequency_osc', 'power',
                            'power_measured', 'output', 'ALC', 'ALC_status',
                            'modulation', 'reference']
        self.loggable = ['IDN'] + self.get_options

        # aligned with set_options.  Nothing ramps by itself (frequency
        # switching takes 1 ms), so the sweeper steps through values.
        self.sweepable = [False] * len(self.set_options)
        self.maxspeed = [None] * len(self.set_options)
        self.eps = [1e-4, 0.05, None, None, None, None, 0.001]   # GHz, dBm, ...

    # ------------------------------------------------------------------ #
    # connection
    # ------------------------------------------------------------------ #
    def open(self):
        a = str(self.adress).strip()
        ports = [p.strip() for p in a.split(',') if p.strip()]
        if a.lower() == 'auto' or not ports:
            ports = [p.device for p in serial.tools.list_ports.comports()]

        for port in ports:
            try:
                s = serial.Serial(port, 115200, bytesize=serial.EIGHTBITS,
                                  parity=serial.PARITY_NONE,
                                  stopbits=serial.STOPBITS_ONE,
                                  timeout=self.timeout)
            except Exception:
                continue
            idn = self._ask(s, '*IDN?')
            if OSC_ID in idn and self.osc is None:
                self.osc = s
            elif AMP_ID in idn and self.amp is None:
                self.amp = s
            else:
                s.close()

        if self.osc is None:
            print('terasense: oscillator not found - frequency cannot be set')
        if self.amp is None:
            print('terasense: amplifier/multiplier not found - power cannot be set')

    def close(self):
        for s in (self.osc, self.amp):
            try:
                if s:
                    s.close()
            except Exception:
                pass
        self.osc = self.amp = None

    def __del__(self):
        self.close()

    # ------------------------------------------------------------------ #
    # low level: SCPI over the virtual COM port, '\r' terminated
    # ------------------------------------------------------------------ #
    def _ask(self, port, command):
        if port is None:
            raise RuntimeError('terasense: device not connected')
        port.reset_input_buffer()
        port.write((command + '\r').encode())
        reply = port.read_until(b'\r').decode(errors='ignore').strip('\r\n ')
        return reply

    def write_osc(self, command):
        ''' send a command to the oscillator, e.g. ":OUTPut:STATe ON" '''
        return self._ask(self.osc, command)

    def write_amp(self, command):
        ''' send a command to the amplifier/multiplier '''
        return self._ask(self.amp, command)

    # ------------------------------------------------------------------ #
    # get options
    # ------------------------------------------------------------------ #
    def IDN(self):
        parts = []
        for name, port in (('osc', self.osc), ('amp', self.amp)):
            try:
                parts.append(f'{name}: {self._ask(port, "*IDN?")}')
            except Exception:
                parts.append(f'{name}: -')
        return ' | '.join(parts)

    def frequency_osc(self):
        ''' oscillator frequency, GHz '''
        return float(self.write_osc(':SOURce:FREQuency?')) / 1e9

    def frequency(self):
        ''' output frequency, GHz (12 x oscillator) '''
        return self.frequency_osc() * MULTIPLIER

    def power(self):
        ''' power setpoint of the amplifier, dBm (nan if set in percent) '''
        reply = self.write_amp(':SOURce:POWer:LEVel?')
        try:
            return float(reply.replace('dB', '').replace('m', '').strip())
        except ValueError:
            return float('nan')          # the setpoint is in %, see power_percent

    def power_measured(self):
        ''' output power measured by the internal detector, dBm '''
        return float(self.write_amp(':SOURce:POWer:SENSe:DATA?'))

    def output(self):
        ''' 1 if the oscillator output is on '''
        return int(self.write_osc(':OUTPut:STATe?').upper().startswith('ON'))

    def ALC(self):
        ''' 1 if automatic level control is on '''
        return int(self.write_amp(':SOURce:POWer:ALC:STATe?').strip() == '1')

    def ALC_status(self):
        '''
        ALC status as a string:
          '~' ALC off,  'S' power matches the request,
          'L' output too low (request above what this frequency can give),
          'H' output too high
        '''
        return self.write_amp(':SOURce:POWer:ALC:STATUS?')

    def modulation(self):
        ''' 1 if external modulation mode is on '''
        return int(self.write_amp(':SOURce:AM:STATe?').strip() == '1')

    def reference(self):
        ''' 10 MHz reference source: 0 = internal, 1 = external '''
        return int(self.write_osc(':SOURce:ROSCillator:SOURce?').upper().startswith('EXT'))

    # ------------------------------------------------------------------ #
    # set options
    # ------------------------------------------------------------------ #
    def set_frequency(self, value=147.0, speed=None):
        '''
        Output frequency, GHz.  Sets the oscillator to value/12 and tells the
        amplifier the new LO frequency so that its detector and ALC stay
        calibrated.  Switching takes about 1 ms.
        '''
        value = float(value)
        if not (F_MIN_GHZ <= value <= F_MAX_GHZ):
            print(f'terasense: frequency must be {F_MIN_GHZ}-{F_MAX_GHZ} GHz, clipping')
            value = min(max(value, F_MIN_GHZ), F_MAX_GHZ)
        f_osc_hz = value * 1e9 / MULTIPLIER
        self.write_osc(f':SOURce:FREQuency {f_osc_hz:.0f}')
        if self.amp is not None:
            self.write_amp(f':SOURce:ROSCillator:EXTernal:FREQuency {f_osc_hz / 1e6:.3f}')
        time.sleep(0.01)

    def set_power(self, value=10.0, speed=None):
        '''
        Output power, dBm.  This switches ALC on automatically.  The maximum
        depends on frequency, so set the frequency first and check ALC_status()
        - 'L' means the request is above what the multiplier can deliver there.
        '''
        value = float(value)
        if not (P_MIN_DBM <= value <= P_MAX_DBM):
            print(f'terasense: power must be {P_MIN_DBM}-{P_MAX_DBM} dBm, clipping')
            value = min(max(value, P_MIN_DBM), P_MAX_DBM)
        self.write_amp(f':SOURce:POWer:LEVel {value} dB')

    def set_power_percent(self, value=0.5, speed=None):
        '''
        Output power as a fraction 0-1 of the raw drive level (ALC turns off).
        The scale is non-linear and 0 does not mean zero output.
        '''
        value = float(value)
        if not (0.0 <= value <= 1.0):
            print('terasense: power_percent must be 0-1, clipping')
            value = min(max(value, 0.0), 1.0)
        self.write_amp(f':SOURce:POWer:LEVel {value}')

    def set_output(self, value=1, speed=None):
        ''' 1 -> oscillator output on, 0 -> off (the whole chain goes dark) '''
        state = 'ON' if int(float(value)) != 0 else 'OFF'
        self.write_osc(f':OUTPut:STATe {state}')

    def set_ALC(self, value=1, speed=None):
        ''' 1 -> automatic level control on, 0 -> off '''
        self.write_amp(f':SOURce:POWer:ALC:STATe {int(float(value)) != 0:d}')

    def set_modulation(self, value=0, speed=None):
        '''
        1 -> external modulation mode (ALC off; feed a 2.5-4 V square wave to
             the amplifier's modulation input, up to 100 kHz).
             Note the inverse logic: a high input level gives low output.
        0 -> back to normal operation
        '''
        self.write_amp(f':SOURce:AM:STATe {int(float(value)) != 0:d}')

    def set_reference(self, value=0, speed=None):
        ''' 10 MHz reference: 0 = internal, 1 = external (phase-locked) '''
        state = 'EXTernal' if int(float(value)) != 0 else 'INTernal'
        self.write_osc(f':SOURce:ROSCillator:SOURce {state}')


def main():
    device = terasense_155(adress='auto')
    for param in device.loggable:
        try:
            print(f'{param} = {getattr(device, param)()}')
        except Exception as e:
            print(f'{param}: {e}')
    device.close()


if __name__ == '__main__':
    main()