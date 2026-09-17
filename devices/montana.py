'''
Unisweep driver for a Montana Instruments Cryostation - temperature only.
Vacuum, cooldown and sample exchange are left to the front panel / touchscreen.

Two generations of Cryostation are supported; the driver picks one from the port:

  s-series (Cryostation s50/s100/s200, Galaxy software)   port 47101, REST/JSON
      'Instrument scripting' must be enabled on the touchscreen:
      Settings -> Remote access -> Instrument Scripting.
      Requires:  pip install requests

  legacy (Cryostation C2 / 200 PT / HILA)                 port 7773, text protocol
      As described in "Cryostation Communication Specification v1.21".
      Enable the remote-control button in the Cryostation software first.
      No extra packages needed.

Address (Unisweep 'Devices' menu):
    '192.168.1.20'          -> s-series, port 47101 (default)
    '192.168.1.20:47101'    -> s-series
    '192.168.1.20:7773'     -> legacy text protocol

Temperature control
-------------------
set_T(value) writes the platform target temperature; the system's own PID drives
the platform there.  There is no ramp-rate setting, so T is declared sweepable:
Unisweep sets the end value once and records continuously while the platform
travels.  For point-by-point measurement with settling, use the 2D/1D sweeper
with T as a non-master (stepwise) axis and a delay long enough to stabilise, or
call wait_for_T() from a script.
'''

import time
import socket

DEFAULT_PORT = 47101          # s-series; use 7773 for the legacy protocol
PLATFORM = '/sampleChamber/temperatureControllers/platform'
USER1 = '/sampleChamber/temperatureControllers/user1'


class montana():

    def __init__(self, adress='192.168.1.20:47101', timeout=5):
        self.timeout = timeout
        self.adress = adress
        host, _, port = str(adress).strip().partition(':')
        self.host = host
        self.port = int(port) if port else DEFAULT_PORT
        self.legacy = (self.port == 7773)
        self.open()

        # ---------------- Unisweep interface ----------------
        self.set_options = ['T', 'stability_target', 'T_user1']
        self.get_options = ['T', 'T_setpoint', 'T_stability', 'T_stable',
                            'heater_power', 'T_user1', 'T_stage1', 'T_stage2',
                            'pressure']
        self.loggable = ['IDN'] + self.get_options

        # aligned with set_options
        self.sweepable = [True, False, False]
        self.maxspeed = [None, None, None]
        self.eps = [0.05, None, 0.05]        # K

        # used by wait_for_T() and T_stable()
        self.stability = 0.02                # K

    # ------------------------------------------------------------------ #
    # connection
    # ------------------------------------------------------------------ #
    def open(self):
        if self.legacy:
            self.socket = None
            self._connect_legacy()
        else:
            import requests
            self.session = requests.Session()
            self.base = f'http://{self.host}:{self.port}/v1'

    def _connect_legacy(self):
        self.close()
        self.socket = socket.create_connection((self.host, self.port), timeout=10)
        self.socket.settimeout(self.timeout)

    def close(self):
        try:
            if self.legacy:
                if self.socket:
                    self.socket.close()
                self.socket = None
            else:
                self.session.close()
        except Exception:
            pass

    def __del__(self):
        self.close()

    # ------------------------------------------------------------------ #
    # low level: legacy text protocol (2-byte length prefix)
    # ------------------------------------------------------------------ #
    def command(self, message):
        ''' send one legacy command (e.g. "GPT") and return the reply string '''
        for attempt in (0, 1):
            try:
                msg = str(len(message)).zfill(2) + message
                self.socket.sendall(msg.encode())
                n = int(self.socket.recv(2).decode())
                chunks, got = [], 0
                while got < n:
                    c = self.socket.recv(n - got)
                    if not c:
                        raise RuntimeError('connection lost')
                    chunks.append(c)
                    got += len(c)
                return b''.join(chunks).decode()
            except Exception:
                if attempt:
                    raise
                self._connect_legacy()      # the Cryostation drops idle clients

    @staticmethod
    def _legacy_float(reply):
        ''' the legacy protocol returns -0.1 / -0.100 for "not available" '''
        try:
            v = float(reply)
        except (TypeError, ValueError):
            return float('nan')
        return float('nan') if abs(v + 0.1) < 1e-9 else v

    # ------------------------------------------------------------------ #
    # low level: s-series REST
    # ------------------------------------------------------------------ #
    def get_prop(self, path):
        ''' GET one REST property, e.g. "/controller/properties/systemState" '''
        r = self.session.get(f"{self.base}/{path.strip('/')}", timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def set_prop(self, path, value):
        ''' PUT one REST property '''
        name = path.strip('/').split('/')[-1]
        url = f"{self.base}/{path.strip('/')}"
        r = self.session.put(url, json={name: value}, timeout=self.timeout)
        if not r.ok:                       # some firmware wants the bare value
            r = self.session.put(url, json=value, timeout=self.timeout)
        r.raise_for_status()
        return r

    def call_method(self, path):
        ''' POST a REST method, e.g. "/controller/methods/cooldown()" '''
        r = self.session.post(f"{self.base}/{path.strip('/')}", timeout=self.timeout)
        r.raise_for_status()
        return r

    def _sample(self, controller):
        ''' thermometer sample dict of a temperature controller '''
        return self.get_prop(f'{controller}/thermometer/properties/sample')['sample']

    # ------------------------------------------------------------------ #
    # get options
    # ------------------------------------------------------------------ #
    def IDN(self):
        if self.legacy:
            return f'Montana Cryostation (legacy) @ {self.host}:{self.port}'
        try:
            state = self.get_prop('/controller/properties/systemState')['systemState']
        except Exception:
            state = '?'
        return f'Montana Cryostation s-series @ {self.host} [{state}]'

    def T(self):
        ''' platform temperature, K '''
        if self.legacy:
            return self._legacy_float(self.command('GPT'))
        s = self._sample(PLATFORM)
        return float(s['temperatureAvg1Sec']) if s.get('temperatureOK', True) else float('nan')

    def T_setpoint(self):
        ''' platform target temperature, K '''
        if self.legacy:
            return self._legacy_float(self.command('GTSP'))
        return float(self.get_prop('/controller/properties/platformTargetTemperature')
                     ['platformTargetTemperature'])

    def T_stability(self):
        ''' platform temperature stability, K '''
        if self.legacy:
            return self._legacy_float(self.command('GPS'))
        return float(self._sample(PLATFORM)['temperatureStability'])

    def T_stable(self):
        ''' 1 when the platform is stable at the setpoint, else 0 '''
        if self.legacy:
            s = self.T_stability()
            return int(s == s and s <= self.stability)
        s = self._sample(PLATFORM)
        return int(bool(s.get('temperatureStable', False)))

    def heater_power(self):
        ''' platform heater power, W '''
        if self.legacy:
            return self._legacy_float(self.command('GPHP'))
        return float(self.get_prop(f'{PLATFORM}/heater/properties/sample')['sample']['powerAvg1Sec'])

    def T_user1(self):
        ''' user/sample thermometer, K (needs the user module fitted) '''
        if self.legacy:
            return self._legacy_float(self.command('GUT'))
        try:
            return float(self._sample(USER1)['temperatureAvg1Sec'])
        except Exception:
            return float('nan')

    def T_sample(self):
        ''' sample thermometer of the legacy systems, K '''
        if self.legacy:
            return self._legacy_float(self.command('GST'))
        return self.T_user1()

    def T_stage1(self):
        if self.legacy:
            return self._legacy_float(self.command('GS1T'))
        return float(self._sample('/cooler/temperatureControllers/stage1')['temperatureAvg1Sec'])

    def T_stage2(self):
        if self.legacy:
            return self._legacy_float(self.command('GS2T'))
        return float(self._sample('/cooler/temperatureControllers/stage2')['temperatureAvg1Sec'])

    def pressure(self):
        ''' sample chamber pressure: mTorr (legacy) / mbar (s-series) '''
        if self.legacy:
            return self._legacy_float(self.command('GCP'))
        try:
            p = self.get_prop('/vacuumSystem/vacuumGauges/sampleChamberPressure/'
                              'properties/pressureSample')['pressureSample']
            return float(p['pressure'])
        except Exception:
            return float('nan')

    # ------------------------------------------------------------------ #
    # set options
    # ------------------------------------------------------------------ #
    def set_T(self, value, speed=None):
        '''
        Platform target temperature, K.  The Cryostation PID drives the platform
        there at its own rate, so `speed` is ignored.
        '''
        value = float(value)
        if self.legacy:
            if not self.command(f'STSP{value}').startswith('OK'):
                print(f'cryostation: set point {value} rejected')
                return
            self.command('SPPT')                     # platform PID on
        else:
            self.set_prop('/controller/properties/platformTargetTemperature', value)

    def set_stability_target(self, value, speed=None):
        ''' stability window used by the system's "stable" flag, K '''
        self.stability = float(value)
        if not self.legacy:
            self.set_prop(f'{PLATFORM}/thermometer/properties/stabilityTarget', float(value))

    def set_T_user1(self, value, speed=None):
        ''' target temperature of the user/sample heater, K '''
        value = float(value)
        if self.legacy:
            self.command(f'SUTSP{value}')
            self.command('SUPT')                     # user PID on
        else:
            self.set_prop(f'{USER1}/properties/controllerEnabled', True)
            self.set_prop(f'{USER1}/properties/targetTemperature', value)

    # ------------------------------------------------------------------ #
    # convenience (not sweep options - normally done by hand)
    # ------------------------------------------------------------------ #
    def cooldown(self):
        self.call_method('/controller/methods/cooldown()') if not self.legacy \
            else self.command('SCD')

    def warmup(self):
        self.call_method('/controller/methods/warmup()') if not self.legacy \
            else self.command('SWU')

    def stop(self):
        self.call_method('/controller/methods/abortGoal()') if not self.legacy \
            else self.command('STP')

    def wait_for_T(self, target=None, stability=None, timeout=3600, poll=2.0):
        '''
        Block until the platform is at `target` (default: current setpoint) and
        stable to within `stability` K.  For use in scripts, not in the GUI.
        '''
        target = self.T_setpoint() if target is None else float(target)
        stability = self.stability if stability is None else float(stability)
        eps = float(self.eps[0])
        t0 = time.time()
        while time.time() - t0 < timeout:
            T, s = self.T(), self.T_stability()
            if abs(T - target) < eps and s == s and 0 < s <= stability:
                return True
            time.sleep(poll)
        print('cryostation: timed out waiting for temperature')
        return False


def main():
    device = montana(adress='192.168.1.20:47101')
    for param in device.loggable:
        try:
            print(f'{param} = {getattr(device, param)()}')
        except Exception as e:
            print(f'{param}: {e}')


if __name__ == '__main__':
    main()