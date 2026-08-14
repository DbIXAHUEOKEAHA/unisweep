import serial
import time

class KSC101:
    '''
    Basic device adaptor for Thorlabs KSC101 K-Cube solenoid controller.
    - tested here with a SH05R/M optical beam shutter, Ø1/2" aperture.
    - 'manual' and 'trigger' modes are the typical modes.
    - 'single' and 'auto' modes are barely supported due to inherent race
    conditions that are created by passing the timing control to the KSC101...
    -> if running in 'single' or 'auto', use the Thorlabs GUI to change the
    timing parameters and add the required time delay to the script...
    - consider adding methods to adjust the trigger mode (active high vs low)
    and the timing parameters for 'single' and 'auto' modes.
    Test code runs and seems robust.
    '''
    def __init__(self,
                 adress,
                 name='KSC101',
                 mode='manual', # typically 'manual' or 'trigger'
                 verbose=False,
                 very_verbose=False):
        self.name = name
        self.verbose = verbose
        self.very_verbose = very_verbose
        if self.verbose: print("%s: opening..."%self.name, end='')
        try:
            self.port = serial.Serial(
                port=adress, baudrate=115200, timeout=1)
        except serial.serialutil.SerialException:
            raise IOError(
                '%s: no connection on port %s'%(self.name, adress))
        #if self.verbose: print(" done.")
        #self._get_info()
        #assert self.model_number == 'KSC101\x00\x00'
        #assert self.firmware_v == 65542
        #self._set_enable(True)
        self._pending_state = None
        #self.set_mode(mode)
        
        self.set_options = ['open', 'close']
        self.get_options = []

    def _send(self, cmd, response_bytes=None):
        if self.very_verbose: print('%s: sending cmd ='%self.name, cmd)
        self.port.write(cmd)
        if response_bytes is not None:
            response = self.port.read(response_bytes)
        else:
            response = None
        assert self.port.inWaiting() == 0
        if self.very_verbose: print('%s: -> response = '%self.name, response)
        return response

    def _get_info(self): # MGMSG_HW_REQ_INFO
        if self.verbose:
            print('%s: getting info'%self.name)
        cmd = b'\x05\x00\x00\x00\x50\x01'
        response = self._send(cmd, response_bytes=90)
        self.model_number = response[10:18].decode('ascii')
        self.type = int.from_bytes(response[18:20], byteorder='little')
        self.serial_number = int.from_bytes(response[6:10], byteorder='little')
        self.firmware_v = int.from_bytes(response[20:24], byteorder='little')
        self.hardware_v = int.from_bytes(response[84:86], byteorder='little')
        if self.verbose:
            print('%s: -> model number  = %s'%(self.name, self.model_number))
            print('%s: -> type          = %s'%(self.name, self.type))
            print('%s: -> serial number = %s'%(self.name, self.serial_number))
            print('%s: -> firmware version = %s'%(self.name, self.firmware_v))
            print('%s: -> hardware version = %s'%(self.name, self.hardware_v))
        return response

    def _get_enable(self): # MGMSG_MOD_REQ_CHANENABLESTATE
        if self.verbose:
            print('%s: getting enable'%self.name)
        cmd = b'\x11\x02\x00\x00\x50\x01'
        response = self._send(cmd, response_bytes=6)
        assert int(response[3]) in (1, 2)
        if int(response[3]) == 1: self.enable = True
        if int(response[3]) == 2: self.enable = False
        if self.verbose:
            print('%s: -> enable = %s'%(self.name, self.enable))
        return self.enable

    def _set_enable(self, enable): # MGMSG_MOD_SET_CHANENABLESTATE
        assert enable in (True, False)
        if enable:     cmd = b'\x10\x02\x00\x01\x50\x01'
        if not enable: cmd = b'\x10\x02\x00\x02\x50\x01'
        if self.verbose:
            print('%s: setting enable = %s'%(self.name, enable))
        self._send(cmd)
        assert self._get_enable() == enable
        if self.verbose:
            print('%s: done setting enable'%self.name)
        return None

    def identify(self): # MGMSG_MOD_IDENTIFY
        if self.verbose:
            print('%s: -> flashing front panel LEDs'%self.name)
        cmd = b'\x23\x02\x00\x00\x50\x01'
        response = self._send(cmd)
        return response

    def get_mode(self): # MGMSG_MOT_REQ_SOL_OPERATINGMODE
        if self.verbose:
            print('%s: getting mode'%self.name)
        cmd = b'\xC1\x04\x00\x00\x50\x01'
        response = self._send(cmd, response_bytes=6)
        assert int(response[3]) in (1, 2, 3, 4)
        number_to_mode = {1:"manual", 2:"single", 3:"auto", 4:"trigger"}
        self.mode = number_to_mode[int(response[3])]
        if self.verbose:
            print('%s: -> mode = %s'%(self.name, self.mode))
        return self.mode

    def set_mode(self, mode): # MGMSG_MOT_SET_SOL_OPERATINGMODE
        mode_to_number = {"manual":1, # use serial port to open/close
                          "single":2, # controller timed single open/close
                          "auto":3,   # controller timed sequence of open/close
                          "trigger":4}# external trigger: +5V TTL on I/O 1
        assert mode in mode_to_number
        if self.verbose:
            print('%s: setting mode = %s'%(self.name, mode))
        self.set_state('closed') # best to close the shutter first
        cmd_byte = mode_to_number[mode].to_bytes(1, byteorder='little')
        cmd = b'\xC0\x04\x00' + cmd_byte + b'\x50\x01'
        self._send(cmd)
        assert self.get_mode() == mode
        if self.verbose:
            print('%s: done setting mode'%self.name)
        return None

    def get_state(self): # MGMSG_MOT_REQ_SOL_STATE
        if self.verbose:
            print('%s: getting state'%self.name)
        cmd = b'\xCC\x04\x00\x00\x50\x01'
        response = self._send(cmd, response_bytes=6)
        assert int(response[3]) in (0, 1)
        if int(response[3]) == 0: self.state = 'closed' # error in docs?
        if int(response[3]) == 1: self.state = 'open'
        if self.verbose:
            print('%s: -> state = %s'%(self.name, self.state))
        return self.state

    def set_state(self, state, block=True): # MGMSG_MOT_SET_SOL_STATE
        if self._pending_state is not None: self._finish_set_state()
        assert state in ('open', 'closed')
        if state == 'open':     cmd = b'\xCB\x04\x00\x01\x50\x01'
        if state == 'closed':   cmd = b'\xCB\x04\x00\x02\x50\x01'
        if self.verbose:
            print('%s: setting state = %s'%(self.name, state))
        self._send(cmd)
        self._pending_state = state
        if block:
            self._finish_set_state()
        return None

    def _finish_set_state(self):
        if self._pending_state is None: return
        verbose = self.verbose
        self.verbose = False
        while self.get_state() != self._pending_state:
            self.get_state()
        self._pending_state = None
        self.verbose = verbose
        if self.verbose:
            print('%s: done setting state'%self.name)
        return None
    
    def set_open(self, value = True):
        self.set_state('open')
        
    def set_close(self, value = True):
        self.set_state('closed')

    def close(self):
        if self.verbose: print("%s: closing..."%self.name)
        self.port.close()
        if self.verbose: print("%s: done closing."%self.name)
        return None

if __name__ == '__main__':
    shutter = KSC101(
        'COM6', mode='manual', verbose=False, very_verbose=False)

    shutter.set_open()

    shutter.close()