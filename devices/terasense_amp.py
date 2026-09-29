'''
Unisweep driver for the TeraSense Amplifier/Multiplier x12 of the tunable
140-155 GHz sub-THz source.
User Manual Rev. 2026-08-20, *IDN? -> TeraSense,AM24F12P10,<serial>,<fw>

This driver owns the OUTPUT POWER, in dBm - the value on the front screen.
The frequency lives on the oscillator, a separate USB device with its own COM
port; see terasense_osc.py.

Port: 115200 baud, 8N1, no flow control, commands terminated with '\\r'.
Requirements:  pip install pyserial

Address (Unisweep 'Devices' menu):   'COM18'

`frequency` here is not the radiated frequency - it only tells the multiplier
which LO to assume so its power reading is calibrated.  Set the real frequency
on terasense_osc and keep this one equal to it (the LEMO multiplier-control
cable does that automatically if it is connected).
'''

import re
import time

import serial

MULTIPLIER = 12
F_MIN_GHZ = 140.0               # output frequency range of the full system
F_MAX_GHZ = 155.0
P_MIN_DBM = -10.0               # manual: minimum settable power
P_MAX_DBM = 20.0                # ~100 mW; the real limit depends on frequency


class terasense_amp():

    def __init__(self, adress='COM18', timeout=1.0):
        self.adress = adress
        self.timeout = timeout
        self.open()

        # ---------------- Unisweep interface ----------------
        self.set_options = ['power']
        self.get_options = ['power', 'frequency']
        self.loggable = ['IDN'] + self.get_options

        self.sweepable = [False, False, False]
        self.maxspeed = [None, None, None]
        self.eps = [0.05, 1e-4, None]          # dBm, GHz, -

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
        if 'AM12' not in idn.upper():
            print(f'terasense_amp: {port} does not look like the multiplier '
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
        ''' send a SCPI command and return the reply '''
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

    @staticmethod
    def _number(reply):
        ''' first number in a reply like "12.50 dBm", nan if there is none '''
        match = re.search(r'[-+]?\d*\.?\d+', reply)
        return float(match.group()) if match else float('nan')

    def power(self):
        ''' output power, dBm - the value shown on the screen '''
        return self._number(self.ask(':SOURce:POWer:SENSe:DATA?'))

    def frequency(self):
        ''' LO frequency the multiplier assumes, expressed as output GHz '''
        mhz = self._number(self.ask(':SOURce:ROSCillator:EXTernal:FREQuency?'))
        return mhz * MULTIPLIER / 1000.0

    def modulation(self):
        ''' 1 if external modulation mode is on '''
        return int(self.ask(':SOURce:AM:STATe?').strip() == '1')

    # ------------------------------------------------------------------ #
    # set options
    # ------------------------------------------------------------------ #
    def set_power(self, value=10.0, speed=None):
        '''
        Output power, dBm.  Levelling (ALC) is switched on automatically.
        The maximum depends on frequency, so set the frequency first; if the
        request is higher than the multiplier can give there, the device holds
        what it can and shows 'L' on its screen.
        '''
        value = float(value)
        if not (P_MIN_DBM <= value <= P_MAX_DBM):
            print(f'terasense_amp: power must be {P_MIN_DBM}-{P_MAX_DBM} dBm, clipping')
            value = min(max(value, P_MIN_DBM), P_MAX_DBM)
        self.ask(f':SOURce:POWer:LEVel {value} dB')

    def set_frequency(self, value=147.0, speed=None):
        '''
        Tell the multiplier which output frequency to assume, GHz, so its power
        reading is calibrated.  This does NOT change the radiated frequency.
        '''
        value = float(value)
        if not (F_MIN_GHZ <= value <= F_MAX_GHZ):
            print(f'terasense_amp: frequency must be {F_MIN_GHZ}-{F_MAX_GHZ} GHz, clipping')
            value = min(max(value, F_MIN_GHZ), F_MAX_GHZ)
        mhz = value * 1000.0 / MULTIPLIER
        self.ask(f':SOURce:ROSCillator:EXTernal:FREQuency {mhz:.3f}')

    def set_modulation(self, value=0, speed=None):
        '''
        1 -> external modulation mode.  Feed a 2.5-4 V square wave to the
             modulation input, up to 100 kHz.  Inverse logic: high in, low out.
        0 -> normal operation
        '''
        self.ask(f':SOURce:AM:STATe {int(float(value)) != 0:d}')


def main():
    device = terasense_amp(adress='COM18')
    device.set_power(10)
    for param in device.loggable:
        try:
            print(f'{param} = {getattr(device, param)()}')
        except Exception as e:
            print(f'{param}: {e}')
    device.close()


if __name__ == '__main__':
    main()
