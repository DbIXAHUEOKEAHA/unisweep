'''
Unisweep driver for a Bluefors LD-250 dilution refrigerator with Fast Sample
Exchange (FSE), talking to the Bluefors Control Software HTTP API.

Requirements:  pip install requests

How the API works
-----------------
The control software (the PC running Bluefors' GUI) exposes every quantity as
a dotted path, e.g.  mapper.bf.temperatures.tmixing.  It is read with
    GET  https://<ip>:49098/values/mapper/bf/temperatures/tmixing/?key=<API key>
and written with
    POST https://<ip>:49098/values/   {"data": {"<path>": {"content": {"value": v}}}}
Heater settings additionally need a  <heater>.write  "call" to be pushed to the
temperature controller.  Port 49098 is HTTPS, 49099 is plain HTTP.

API key
-------
Create one in the control software (Settings -> API keys) with read + write
permission.  Give it to the driver in one of three ways:
    1. bluefors(adress, key='...')
    2. a file  bluefors_api_key.txt  next to this module
    3. environment variable  BLUEFORS_API_KEY

Address (Unisweep 'Devices' menu):  '192.168.1.10:49098'  (or ':49099' for http)

Paths
-----
Verified (from the API docs / other LD-250 users):
    mapper.bf.temperatures.{t50k,t4k,tstill,tmixing,tmagnet,tfse}   [K]
    mapper.temperature_control.sensors.tN.{temperature,resistance}
    driver.bftc.data.heaters.heater_N.{setpoint,power,active,pid_mode}
    driver.maxigauge.pressures.pN                                    [mbar]
Anything else (flow meter, valves, pumps, FSE stage) can be found with
    bluefors('...').tree('mapper')      # prints every available path
and read with  .get_path('some.dotted.path').
'''

import os
import json
import time
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Bluefors temperature-controller channel numbers.  Edit to match the
# 'Temperature control' page of your control software.
MXC_HEATER = 4           # heater driving the mixing-chamber plate
STILL_HEATER = 3
FSE_HEATER = None        # heater on the sample puck, if fitted

TEMP = {   # get-option name -> path
    'T_50K':    'mapper.bf.temperatures.t50k',
    'T_4K':     'mapper.bf.temperatures.t4k',
    'T_still':  'mapper.bf.temperatures.tstill',
    'T_MXC':    'mapper.bf.temperatures.tmixing',
    'T_magnet': 'mapper.bf.temperatures.tmagnet',
    'T_FSE':    'mapper.bf.temperatures.tfse',      # fast-sample-exchange puck
}

PRESSURE = {f'P{i}': f'driver.maxigauge.pressures.p{i}' for i in range(1, 7)}
# LD-series Maxigauge convention: P1 OVC, P2 still/IVC, P3 condensing line,
# P4 mixture tank, P5 circulation/pumping line, P6 return/aux


class bluefors():

    def __init__(self, adress='192.168.1.10:49098', key=None, timeout=5):
        self.adress = adress
        self.timeout = timeout
        self.key = self._find_key(key)
        self.open()

        self.mxc_heater = f'driver.bftc.data.heaters.heater_{MXC_HEATER}'
        self.still_heater = f'driver.bftc.data.heaters.heater_{STILL_HEATER}'

        # ---------------- Unisweep interface ----------------
        self.set_options = ['T_MXC', 'MXC_setpoint', 'MXC_heater_power',
                            'MXC_heater_on', 'still_heater_power',
                            'still_heater_on']
        self.get_options = (list(TEMP) + list(PRESSURE) +
                            ['MXC_setpoint', 'MXC_heater_power', 'MXC_heater_on',
                             'still_heater_power', 'still_heater_on'])
        self.loggable = ['IDN'] + self.get_options

        # aligned with set_options.
        # T_MXC: the BFTC PID ramps the plate itself -> sweepable = True; the
        # sweeper waits until get('T_MXC') is within eps of the target.
        self.sweepable = [True, False, False, False, False, False]
        self.maxspeed = [None, None, None, None, None, None]
        self.eps = [0.002, None, 1e-6, None, 1e-6, None]     # K, -, W, -, W, -

    # ------------------------------------------------------------------ #
    # connection
    # ------------------------------------------------------------------ #
    @staticmethod
    def _find_key(key):
        if key:
            return key
        here = os.path.dirname(os.path.abspath(__file__))
        for p in (os.path.join(here, 'bluefors_api_key.txt'),
                  os.path.join(os.getcwd(), 'bluefors_api_key.txt')):
            if os.path.isfile(p):
                return open(p).read().strip()
        key = os.environ.get('BLUEFORS_API_KEY')
        if key:
            return key
        print('bluefors: no API key found - reads may work, writes will fail')
        return ''

    def open(self):
        a = str(self.adress).strip()
        if a.startswith('http'):
            self.base = a.rstrip('/')
        else:
            host, _, port = a.partition(':')
            port = int(port) if port else 49098
            scheme = 'https' if port == 49098 else 'http'
            self.base = f'{scheme}://{host}:{port}'
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers['Content-Type'] = 'application/json'

    def close(self):
        try:
            self.session.close()
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # generic access
    # ------------------------------------------------------------------ #
    def _url(self, path='', **params):
        p = path.replace('.', '/')
        if p and not p.endswith('/'):
            p += '/'
        params.setdefault('prettyprint', 0)
        if self.key:
            params['key'] = self.key
        q = '&'.join(f'{k}={v}' for k, v in params.items())
        return f'{self.base}/values/{p}?{q}'

    def get_path(self, path, typ=float):
        ''' read one dotted path; returns typ(value) or None if not valid '''
        r = self.session.get(self._url(path), timeout=self.timeout)
        r.raise_for_status()
        d = r.json()
        if 'error' in d:
            raise RuntimeError(f"bluefors: {d['error'].get('description', d['error'])}")
        content = d['data'][path]['content']
        v = content.get('latest_valid_value', content.get('latest_value', {}))
        s = v.get('value', '')
        if s == '' or s is None:
            return None
        if typ is bool:
            return s in ('1', 'true', 'True', True, 1)
        return typ(s)

    def set_path(self, path, value, apply_device=None):
        '''
        write one dotted path.  For temperature-controller settings pass
        apply_device=<heater path> so the change is pushed to the hardware.
        '''
        if isinstance(value, bool):
            value = int(value)
        body = {'data': {path: {'content': {'value': str(value)}}}}
        r = self.session.post(self._url(), data=json.dumps(body), timeout=self.timeout)
        r.raise_for_status()
        d = r.json()
        if 'error' in d:
            raise RuntimeError(f"bluefors: {d['error'].get('description', d['error'])}")
        if apply_device:
            body = {'data': {f'{apply_device}.write': {'content': {'call': 1}}}}
            r = self.session.post(self._url(), data=json.dumps(body), timeout=self.timeout)
            r.raise_for_status()
        return d

    def tree(self, root='mapper', show=True):
        ''' list every path below root (use to discover flow, valves, pumps, FSE) '''
        r = self.session.get(self._url(root, recursion=1), timeout=30)
        r.raise_for_status()
        d = r.json().get('data', {})
        paths = sorted(d)
        if show:
            for p in paths:
                c = d[p].get('content', {})
                v = c.get('latest_valid_value', c.get('latest_value', {})).get('value', '')
                print(f'{p:60s} {v}')
        return paths

    # ------------------------------------------------------------------ #
    # get options
    # ------------------------------------------------------------------ #
    def IDN(self):
        return f'Bluefors LD-250 @ {self.base}'

    def _temp(self, name):
        v = self.get_path(TEMP[name])
        return float('nan') if v is None else v

    def T_50K(self):     return self._temp('T_50K')
    def T_4K(self):      return self._temp('T_4K')
    def T_still(self):   return self._temp('T_still')
    def T_MXC(self):     return self._temp('T_MXC')
    def T_magnet(self):  return self._temp('T_magnet')
    def T_FSE(self):     return self._temp('T_FSE')

    def _pressure(self, name):
        v = self.get_path(PRESSURE[name])
        return float('nan') if v is None else v

    def P1(self): return self._pressure('P1')
    def P2(self): return self._pressure('P2')
    def P3(self): return self._pressure('P3')
    def P4(self): return self._pressure('P4')
    def P5(self): return self._pressure('P5')
    def P6(self): return self._pressure('P6')

    def sensor_temperature(self, channel):
        ''' temperature of controller channel N, K '''
        return self.get_path(f'mapper.temperature_control.sensors.t{channel}.temperature')

    def sensor_resistance(self, channel):
        ''' resistance of controller channel N, Ohm '''
        return self.get_path(f'mapper.temperature_control.sensors.t{channel}.resistance')

    def MXC_setpoint(self):
        ''' PID temperature setpoint of the MXC heater, K '''
        return self.get_path(f'{self.mxc_heater}.setpoint')

    def MXC_heater_power(self):
        ''' MXC heater power, W '''
        return self.get_path(f'{self.mxc_heater}.power')

    def MXC_heater_on(self):
        return int(bool(self.get_path(f'{self.mxc_heater}.active', bool)))

    def still_heater_power(self):
        return self.get_path(f'{self.still_heater}.power')

    def still_heater_on(self):
        return int(bool(self.get_path(f'{self.still_heater}.active', bool)))

    # ------------------------------------------------------------------ #
    # set options
    # ------------------------------------------------------------------ #
    def set_T_MXC(self, value, speed=None):
        '''
        Regulate the mixing chamber to `value` K: enables PID mode, sets the
        setpoint and switches the heater on.  Returns immediately; Unisweep
        waits for T_MXC to reach the target (sweepable = True).
        `speed` is ignored - the BFTC has no ramp rate.
        '''
        h = self.mxc_heater
        self.set_path(f'{h}.pid_mode', 1, apply_device=h)
        self.set_path(f'{h}.setpoint', float(value), apply_device=h)
        self.set_path(f'{h}.active', 1, apply_device=h)

    def set_MXC_setpoint(self, value, speed=None):
        ''' change the setpoint only (no mode / enable change), K '''
        self.set_path(f'{self.mxc_heater}.setpoint', float(value), apply_device=self.mxc_heater)

    def set_MXC_heater_power(self, value, speed=None):
        ''' manual heater power, W (switches PID off) '''
        h = self.mxc_heater
        self.set_path(f'{h}.pid_mode', 0, apply_device=h)
        self.set_path(f'{h}.power', float(value), apply_device=h)

    def set_MXC_heater_on(self, value, speed=None):
        self.set_path(f'{self.mxc_heater}.active', int(float(value)) != 0,
                      apply_device=self.mxc_heater)

    def set_still_heater_power(self, value, speed=None):
        ''' still heater power, W '''
        self.set_path(f'{self.still_heater}.power', float(value), apply_device=self.still_heater)

    def set_still_heater_on(self, value, speed=None):
        self.set_path(f'{self.still_heater}.active', int(float(value)) != 0,
                      apply_device=self.still_heater)

    # ------------------------------------------------------------------ #
    def wait_for_T_MXC(self, target, eps=None, timeout=3600, poll=2.0):
        ''' block until T_MXC is within eps of target (for scripts) '''
        eps = self.eps[0] if eps is None else eps
        t0 = time.time()
        while time.time() - t0 < timeout:
            if abs(self.T_MXC() - target) < eps:
                return True
            time.sleep(poll)
        return False


def main():
    device = bluefors(adress='192.168.1.10:49098')
    for param in device.loggable:
        try:
            print(f'{param} = {getattr(device, param)()}')
        except Exception as e:
            print(f'{param}: {e}')


if __name__ == '__main__':
    main()