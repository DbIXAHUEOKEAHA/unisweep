'''
Unisweep driver for the TeraSense Oscillator (frequency synthesizer, 7.3-14.6 GHz)
of the tunable 140-155 GHz sub-THz source.
User Manual Rev. 2026-08-20, *IDN? -> TeraSense,SYF12P5Vx,<serial>,<fw>

This driver owns the FREQUENCY of the system.  The output power lives on the
amplifier/multiplier, which is a separate USB device with its own COM port -
see terasense_amp.py.

The final radiated frequency is 12 x the oscillator frequency, so this driver
reports and sets GHz at the WR6.5 output (140-155 GHz) by default.  Use
frequency_osc if you would rather work in synthesizer GHz (7.3-14.6).

Port: 115200 baud, 8N1, no flow control, commands terminated with '\\r'.
Requirements:  pip install pyserial

Address (Unisweep 'Devices' menu):   'COM19'

NOTE: the amplifier's power detector is calibrated against the frequency it has
been told.  If the LEMO multiplier-control cable between the two boxes is
connected, the oscillator passes the new frequency over automatically.  If it is
not, set the same frequency on terasense_amp as well, or its power readings and
ALC will be wrong.
'''

import time

import serial

MULTIPLIER = 12                 # x12 frequency multiplier downstream
F_MIN_GHZ = 140.0               # output frequency range of the full system
F_MAX_GHZ = 155.0
F_OSC_MIN_GHZ = 7.3             # range of the synthesizer itself
F_OSC_MAX_GHZ = 14.6


class terasense_osc():

    def __init__(self, adress='COM19', timeout=1.0):
        self.adress = adress
        self.timeout = timeout
        self.open()

        # ---------------- Unisweep interface ----------------
        self.set_options = ['frequency', 'output']
        self.get_options = ['frequency', 'output']
        self.loggable = ['IDN'] + self.get_options

        # frequency switching takes about 1 ms, nothing ramps by itself
        self.sweepable = [False, False, False, False]
        self.maxspeed = [None, None, None, None]
        self.eps = [1e-4, 1e-5, None, None]          # GHz, GHz, -, -

    # ------------------------------------------------------------------ #
    # connection
    # ------------------------------------------------------------------ #
    def open(self):
        port = str(self.adress).strip()
        self.serial = serial.Serial(port, 115200, bytesize=serial.EIGHTBITS,
                                    parity=serial.PARITY_NONE,
                                    stopbits=serial.STOPBITS_ONE,
                                    timeout=self.timeout, write_timeout=1)
        time.sleep(0.3)                 # the FTDI chip resets when the port opens
        self.serial.reset_input_buffer()
        self.serial.reset_output_buffer()
        idn = self.IDN()
        if 'SYF12' not in idn:
            print(f'terasense_osc: {port} does not look like the oscillator '
                  f'(*IDN? -> {idn or "no reply"})')

    def close(self):
        try:
            self.serial.close()
        except Exception:
            pass

    def __del__(self):
        self.close()

    # ------------------------------------------------------------------ #
    # low level
    # ------------------------------------------------------------------ #
    def ask(self, command, tries=3):
        ''' send a SCPI command and return the reply, e.g. ask(":OUTPut:STATe?") '''
        for _ in range(tries):
            self.serial.reset_input_buffer()
            self.serial.write((command + '\r').encode())
            reply = self.serial.read_until(b'\r').decode(errors='ignore').strip('\r\n ')
            if reply or not command.endswith('?'):
                return reply
            time.sleep(0.1)
        return ''

    # ------------------------------------------------------------------ #
    # get options
    # ------------------------------------------------------------------ #
    def IDN(self):
        return self.ask('*IDN?')

    def frequency_osc(self):
        ''' synthesizer frequency, GHz '''
        return float(self.ask(':SOURce:FREQuency?')) / 1e9

    def frequency(self):
        ''' radiated frequency at the WR6.5 output, GHz (12 x synthesizer) '''
        return self.frequency_osc() * MULTIPLIER

    def output(self):
        ''' 1 if the synthesizer output is on '''
        return int(self.ask(':OUTPut:STATe?').upper().startswith('ON'))

    def reference(self):
        ''' 10 MHz reference: 0 = internal, 1 = external '''
        return int(self.ask(':SOURce:ROSCillator:SOURce?').upper().startswith('EXT'))

    # ------------------------------------------------------------------ #
    # set options
    # ------------------------------------------------------------------ #
    def set_frequency(self, value=147.0, speed=None):
        ''' radiated frequency, GHz (the synthesizer goes to value/12) '''
        value = float(value)
        if not (F_MIN_GHZ <= value <= F_MAX_GHZ):
            print(f'terasense_osc: frequency must be {F_MIN_GHZ}-{F_MAX_GHZ} GHz, clipping')
            value = min(max(value, F_MIN_GHZ), F_MAX_GHZ)
        self.set_frequency_osc(value / MULTIPLIER)

    def set_frequency_osc(self, value=12.25, speed=None):
        ''' synthesizer frequency, GHz '''
        value = float(value)
        if not (F_OSC_MIN_GHZ <= value <= F_OSC_MAX_GHZ):
            print(f'terasense_osc: synthesizer frequency must be '
                  f'{F_OSC_MIN_GHZ}-{F_OSC_MAX_GHZ} GHz, clipping')
            value = min(max(value, F_OSC_MIN_GHZ), F_OSC_MAX_GHZ)
        self.ask(f':SOURce:FREQuency {value * 1e9:.0f}')
        time.sleep(0.01)                # 1 ms switching time

    def set_output(self, value=1, speed=None):
        ''' 1 -> output on, 0 -> off (the whole chain goes dark) '''
        self.ask(f':OUTPut:STATe {"ON" if int(float(value)) != 0 else "OFF"}')

    def set_reference(self, value=0, speed=None):
        ''' 10 MHz reference: 0 = internal, 1 = external (phase-locked) '''
        state = 'EXTernal' if int(float(value)) != 0 else 'INTernal'
        self.ask(f':SOURce:ROSCillator:SOURce {state}')


def main():
    device = terasense_osc(adress='COM19')
    device.set_frequency(150)
    device.set_output(1)
    for param in device.loggable:
        try:
            print(f'{param} = {getattr(device, param)()}')
        except Exception as e:
            print(f'{param}: {e}')
    device.close()


if __name__ == '__main__':
    main()