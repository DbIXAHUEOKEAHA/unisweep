import ctypes
import os
import warnings
import platform
import time

if __name__ == '__main__':
    from ANC350_drivers.ANC350.PylibANC350 import Positioner_ANC350
else:
    from devices.ANC350_drivers.ANC350.PylibANC350 import Positioner_ANC350

def ANC_errcheck(ret_code, func, args):
    '''
    Translates the errors returned from the dll functions.

    Parameters
    ----------
    ret_code : int
        Return value from the function
    func : function
        Function that is called
    args : list
        Parameters passed to the function

    Returns
    -------
    str
        String of the return code
    '''
    # List of error types, manually imported from the header file anc350.h
    ANC_RC = {
        0 : "No error",
        -1 : "Unknown / other error",
        1 : "Timeout during data retrieval",
        2 : "No contact with the positioner via USB",
        3 : "Error in the driver response",
        7 : "A connection attempt failed because the device is already in use",
        8 : "Unknown error",
        9 : "Invalid device number used in call",
        10 : "Invalid axis number in function call",
        11 : "Parameter in call is out of range",
        12 : "Function not available for device type",
        13 : "Error opening or interpreting a file"}

    assert str(type(func)) == "<class 'ctypes.CDLL.__init__.<locals>._FuncPtr'>"

    if ret_code != 0:
        raise RuntimeError('Error: {:} '.format(ANC_RC[ret_code]) +
                           str(func.__name__) +
                           ' with parameters: ' + str(args))
    return ANC_RC[ret_code]

def load_ANC350dll():
    '''
    Import .dll/.so to communicate with ANC350. Pay attention to have libusb0
    available too for Windows systems.

    Returns
    -------
    anc : ctypes
        Instance of the LoadLibrary method
    '''

    cur_dir = os.getcwd()

    if __name__ == '__main__':
        filename = os.path.join(cur_dir, 'ANC350_drivers', 'ANC350', 'win64', 'anc350v4.dll')
    else:
        filename = os.path.join(cur_dir, 'devices', 'ANC350_drivers', 'ANC350', 'win64', 'anc350v4.dll')

    anc = ctypes.cdll.LoadLibrary(filename)

    return anc

def discover_ANC350(ifaces=3):
    '''
    The function searches for connected ANC350RES devices on USB and LAN
    and initialises internal data structures per device. Devices that are
    in use by another application or PC are not found. The function must
    be called *before* connecting to a device and must not be called as
    long as any devices are connected.

    The number of devices found is returned. In subsequent functions,
    devices are identified by a sequence number that must be less than the
    number returned.

    Parameters
    ----------
    ifaces : int
        Interfaces where devices are to be searched.
        {None: 0, USB: 1, ethernet: 2, all: 3} Default: 3

    Returns
    -------
    devCount : int
        Number of devices found
    '''
    anc = load_ANC350dll()

    discover_dll = anc.ANC_discover
    discover_dll.errcheck = ANC_errcheck

    devCount = ctypes.c_int()
    discover_dll(ctypes.c_int(ifaces),
                 ctypes.byref(devCount))
    print('{:} ANC350 devices found.'.format(devCount.value))
    return devCount.value

def registerExternalIp(hostname):
    '''
    discover is able to find devices connected via TCP/IP
    in the same network segment, but it can't "look through" routers.
    To connect devices in external networks, reachable by routing,
    the IP addresses of those devices have to be registered prior to
    calling discover. The function registers one device and can
    be called several times.

    The function will return ANC_Ok if the name resolution succeeds
    (ANC_NoDevice otherwise); it *doesn't test* if the device is reachable.
    Registered and reachable devices will be found by discover.

    Parameters
    ----------
    hostname : str
        hostname or IP Address in dotted decimal notation of the device to
        register.
    '''
    anc = load_ANC350dll()

    registerExternalIp_dll = anc.ANC_registerExternalIp
    registerExternalIp_dll.errcheck = ANC_errcheck

    registerExternalIp_dll(ctypes.c_char_p(hostname)) # @todo To check

class ANC350():
    def __init__(self, adress = 'ASRL3::INSTR'):
        
        ANC350_devcount = discover_ANC350()
        if ANC350_devcount != 2:
            print(f'{ANC350_devcount} devices found, please check Daisy')
        self.device = Positioner_ANC350(0)
        
        #time.sleep(1)
        
        cx = self.cap_x()
        print(f'X-capasitance = {cx}')
        cy = self.cap_y()
        print(f'Y-capasitance = {cy}')
        cz = self.cap_z()
        print(f'Z-capasitance = {cz}')
        
        gnd_val = 0
        
        self.set_gnd_all(gnd_val)
        
        self.get_options = ['gnd_x', 'gnd_y', 'gnd_z', 'pos_x', 'pos_y', 'pos_z', 'volt_x', 'volt_y', 'volt_z', 
                            'freq_x', 'freq_y', 'freq_z', 'cap_x', 'cap_y', 'cap_z']
        self.set_options = ['gnd_x', 'gnd_y', 'gnd_z', 'step_up_x', 'step_up_y', 'step_up_z', 'step_down_x', 
                            'step_down_y', 'step_down_z', 'volt_x', 'volt_y', 'volt_z', 'freq_x', 'freq_y', 'freq_z']
    
    def set_gnd_all(self, value):
        """
        If value == 1 or True: set all axis grounded
        If value == 0 or False: set all axis ungrounded
        
        Returns
        -------
        None.
        """
        
        for i in [0, 1, 2]:
            self.device.setAxisOutput(i, value, 0)
    
    def set_gnd_x(self, value):
        """
        If value == 1 or True: set x-axis grounded
        If value == 0 or False: set x-axis ungrounded
        
        Returns
        -------
        None.
        """
        axis = 0
        value = int(value)
        self.device.setAxisOutput(axis, value, 0)
        
    def set_gnd_y(self, value):
        """
        If value == 1 or True: set y-axis grounded
        If value == 0 or False: set y-axis ungrounded
        
        Returns
        -------
        None.
        """
        axis = 1
        value = int(value)
        self.device.setAxisOutput(axis, value, 0)
        
    def set_gnd_z(self, value):
        """
        If value == 1 or True: set z-axis grounded
        If value == 0 or False: set z-axis ungrounded
        
        Returns
        -------
        None.
        """
        axis = 2
        value = int(value)
        self.device.setAxisOutput(axis, value, 0)
    
    def pos_x(self):
        axis = 0
        
        ans = self.device.getPosition(axis)
        return ans
    
    def pos_y(self):
        axis = 1
        
        ans = self.device.getPosition(axis)
        return ans
    
    def pos_z(self):
        axis = 2
        
        ans = self.device.getPosition(axis)
        return ans
    
    def set_step_up_x(self, value: int = 1):
        """
        Makes 'value' number of steps up along x-axis
        
        Returns
        -------
        None.
        """
        
        try:
            value = int(value)
        except ValueError:
            value = 1
        
        axis = 0
        for i in range(value):
            time.sleep(0.05)
            self.device.startSingleStep(axis, 0)
        
    def set_step_down_x(self, value: int = 1):
        """
        Makes 'value' number of steps up along x-axis
        
        Returns
        -------
        None.
        """
        
        try:
            value = int(value)
        except ValueError:
            value = 1
        
        axis = 0
        for i in range(value):
            time.sleep(0.05)
            self.device.startSingleStep(axis, 1)
        
    def set_step_up_y(self, value: int = 1):
        """
        Makes 'value' number of steps up along y-axis
        
        Returns
        -------
        None.
        """
        
        try:
            value = int(value)
        except ValueError:
            value = 1
        
        axis = 1
        for i in range(value):
            time.sleep(0.05)
            self.device.startSingleStep(axis, 0)
        
    def set_step_down_y(self, value: int = 1):
        """
        Makes 'value' number of steps up along y-axis
        
        Returns
        -------
        None.
        """
        
        try:
            value = int(value)
        except ValueError:
            value = 1
        
        axis = 1
        for i in range(value):
            time.sleep(0.05)
            self.device.startSingleStep(axis, 1)
        
    def set_step_up_z(self, value: int = 1):
        """
        Makes 'value' number of steps up along z-axis
        
        Returns
        -------
        None.
        """
        
        try:
            value = int(value)
        except ValueError:
            value = 1
        
        axis = 2
        for i in range(value):
            time.sleep(0.05)
            self.device.startSingleStep(axis, 0)
        
    def set_step_down_z(self, value: int = 1):
        """
        Makes 'value' number of steps up along z-axis
        
        Returns
        -------
        None.
        """
        
        try:
            value = int(value)
        except ValueError:
            value = 1
        
        axis = 2
        for i in range(value):
            time.sleep(0.05)
            self.device.startSingleStep(axis, 1)
        
    def volt_x(self):
        """
        Returns
        -------
        float: Voltage on x-axis

        """
        axis = 0
        ans = self.device.getDCVoltage(axis)
        return ans
    
    def volt_y(self):
        """
        Returns
        -------
        float: Voltage on y-axis

        """
        axis = 1
        ans = self.device.getDCVoltage(axis)
        return ans
    
    def volt_z(self):
        """
        Returns
        -------
        float: Voltage on z-axis

        """
        axis = 2
        ans = self.device.getDCVoltage(axis)
        return ans
    
    def set_volt_x(self, value):
        """
        set voltage on x-axis
        Returns
        -------
        None.

        """
        axis = 0
        self.device.setDCVoltage(axis, value)
        
    def set_volt_y(self, value):
        """
        set voltage on y-axis
        Returns
        -------
        None.

        """
        axis = 1
        self.device.setDCVoltage(axis, value)
        
    def set_volt_z(self, value):
        """
        set voltage on z-axis
        Returns
        -------
        None.

        """
        axis = 2
        self.device.setDCVoltage(axis, value)
        
    def freq_x(self):
        """
        Returns
        -------
        float: Frequency on x-axis

        """
        axis = 0
        ans = self.device.getFrequency(axis)
        return ans
    
    def freq_y(self):
        """
        Returns
        -------
        float: Frequency on y-axis

        """
        axis = 1
        ans = self.device.getFrequency(axis)
        return ans
    
    def freq_z(self):
        """
        Returns
        -------
        float: Frequency on z-axis

        """
        axis = 2
        ans = self.device.coarse.getFrequency(axis)
        return ans
    
    def set_freq_x(self, value):
        """
        set Frequency on x-axis
        Returns
        -------
        None.

        """
        axis = 0
        self.device.setFrequency(axis, value)
        
    def set_freq_y(self, value):
        """
        set Frequency on y-axis
        Returns
        -------
        None.

        """
        axis = 1
        self.device.setFrequency(axis, value)
        
    def set_freq_z(self, value):
        """
        set Frequency on z-axis
        Returns
        -------
        None.

        """
        axis = 2
        self.device.setFrequency(axis, value)
        
    def cap_x(self):
        """
        Returns
        -------
        float: Capacitance on x-axis

        """
        axis = 0
        
        ans = self.device.measureCapacitance(axis)
        return ans
    
    def cap_y(self):
        """
        Returns
        -------
        float: Capacitance on y-axis

        """
        axis = 1
        
        ans = self.device.measureCapacitance(axis)
        return ans
    
    def cap_z(self):
        """
        Returns
        -------
        float: Capacitance on z-axis

        """
        axis = 2
        
        ans = self.device.measureCapacitance(axis)
        return ans
    
    def close(self):
        self.device.disconnect()
        
if __name__ == '__main__':
    device = ANC350()
    try:
        device.set_gnd_all(1) #unground
        device.set_step_down_x(10) #10 steps up
        p = device.pos_x()
        print(f'X-position = {p}')
        pass
    except Exception as ex:
        print(f'Exception happened: {ex}')
    finally:
        device.close()
        pass
        