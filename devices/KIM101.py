# -*- coding: utf-8 -*-
import sys
import time
import traceback
from typing import Any
from concurrent.futures import ThreadPoolExecutor, Future

import clr

# Append Kinesis path
sys.path.append(r"C:\Program Files\Thorlabs\Kinesis")

# Add references so Python can see .NET
clr.AddReference("System")
clr.AddReference("Thorlabs.MotionControl.DeviceManagerCLI")
clr.AddReference("Thorlabs.MotionControl.GenericMotorCLI")
clr.AddReference("Thorlabs.MotionControl.KCube.InertialMotorCLI")
clr.AddReference("Thorlabs.MotionControl.KCube.DCServoCLI")
clr.AddReference("Thorlabs.MotionControl.IntegratedStepperMotorsCLI")

from Thorlabs.MotionControl.DeviceManagerCLI import *
from Thorlabs.MotionControl.GenericMotorCLI import *
from Thorlabs.MotionControl.IntegratedStepperMotorsCLI import *
from Thorlabs.MotionControl.KCube.DCServoCLI import *
from Thorlabs.MotionControl.KCube.InertialMotorCLI import *

class GenericDevice:
    def __init__(self, serial: str = None, device_prefix: Any = None):
        self.serial = serial
        self.device_prefix = device_prefix
        self.device = None

    def initialize(self):
        DeviceManagerCLI.BuildDeviceList()
        device_list = (DeviceManagerCLI.GetDeviceList(self.device_prefix)
                       if self.device_prefix else DeviceManagerCLI.GetDeviceList())

        if not device_list:
            raise ConnectionError("No devices found")

        if self.serial is None:
            self.serial = device_list[0]  # Pick first by default (no input())

        if self.serial not in device_list:
            raise ConnectionError(f"Device {self.serial} not found in list")

        print(f"Device {self.serial} is available")


class my_KIM101(GenericDevice):
    def __init__(self, serial: str = None):
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.device_prefix = KCubeInertialMotor.DevicePrefix_KIM101
        self.channel1 = None
        self.channel2 = None
        self.channel3 = None
        self.channel4 = None
        super().__init__(serial=serial, device_prefix=self.device_prefix)
        self.init_future = self.executor.submit(self.init_device)

    def init_device(self):
        try:
            self.initialize()
            self.device = KCubeInertialMotor.CreateKCubeInertialMotor(self.serial)
            self.device.Connect(self.serial)
            timeout = 0
            while not self.device.IsSettingsInitialized() and timeout <= 10:
                self.device.WaitForSettingsInitialized(500)
                timeout += 1
            self.device.StartPolling(250)
            time.sleep(0.5)
            self.device.EnableDevice()
            self.device_info = self.device.GetDeviceInfo()
            print(f"Connected to {self.device_info.Name} ({self.device_info.SerialNumber})")

            self.configuration = self.device.GetInertialMotorConfiguration(self.serial)
            self.settings = ThorlabsInertialMotorSettings.GetSettings(self.configuration)

            self.channel1 = InertialMotorStatus.MotorChannels.Channel1
            self.channel2 = InertialMotorStatus.MotorChannels.Channel2
            self.channel3 = InertialMotorStatus.MotorChannels.Channel3
            self.channel4 = InertialMotorStatus.MotorChannels.Channel4

            for ch in [self.channel1, self.channel2, self.channel3, self.channel4]:
                self.settings.Drive.Channel(ch).StepRate = 2000
                self.settings.Drive.Channel(ch).StepAcceleration = 100000

            self.device.SetSettings(self.settings, True, True)
            print("Initialization complete")
        except Exception:
            print("ERROR: Initialization failed")
            print(traceback.format_exc())

    def get_position(self, channel: int) -> int:
        
        
        channel_map = {
            1: self.channel1,
            2: self.channel2,
            3: self.channel3,
            4: self.channel4,
        }
        
        if channel_map[channel] is None:
            raise RuntimeError("Device not initialized properly (channel is None)")
        
        return self.device.GetPosition(channel_map[channel])

    def move_to(self, channel: int, pos: int, timeout: int = 2000) -> int:
        try:
            channel_map = {
                1: self.channel1,
                2: self.channel2,
                3: self.channel3,
                4: self.channel4,
            }
            self.device.MoveTo(channel_map[channel], int(pos), int(timeout))
            return self.get_position(channel)
        except Exception:
            print("ERROR: Failed to move")
            print(traceback.format_exc())
            return -1

    def close(self):
        #self.device.StopPolling()
        #self.device.Disconnect(True)
        pass

class KIM101:
    def __init__(self, adress):
        self.device = my_KIM101("97251168")
        self.get_options = ['Ch1', 'Ch2', 'Ch3', 'Ch4']
        self.set_options = ['Ch1', 'Ch2', 'Ch3', 'Ch4']
        self.sweepable = [True, True, True, True]
        self.maxspeed = [2000, 2000, 2000, 2000]
        self.eps = [50, 50, 50, 50]
        self.timeout = 1000000000
        
        for i in [1, 2, 3, 4]:
            self.__dict__[f'Ch{i}'] = lambda i=i: self.Ch(i)
            self.__dict__[f'set_Ch{i}'] = lambda value, speed=None, i=i: self.set_Ch(i, value, speed)

    def _wait_init(self):
        self.device.init_future.result()

    def Ch(self, i) -> int:
        self._wait_init()
        ans = self.device.executor.submit(self.device.get_position, i).result(5)
        return ans

    def set_Ch(self, i: int, value: int, speed=None) -> Future:
        self._wait_init()
        if speed == 'SetGet':
            speed = self.maxspeed[0]
            speed = int(abs(speed))
            self.device.settings.Drive.Channel(getattr(self.device, f'channel{i}')).StepRate = speed
            self.device.executor.submit(self.device.device.SetSettings, self.device.settings, True, True)
        elif speed:
            speed = int(abs(speed))
            speed = min(speed, self.maxspeed[0])
            self.device.settings.Drive.Channel(getattr(self.device, f'channel{i}')).StepRate = speed
            self.device.executor.submit(self.device.device.SetSettings, self.device.settings, True, True)
        try:
            value
        except ValueError:
            return
        return self.device.executor.submit(self.device.move_to, i, value, self.timeout)

    def stop(self):
        for i in [1, 2, 3, 4]:
            current_pos = self.device.__dict__[f'Ch{i}']()
            self.device.__dict__[f'set_Ch{i}'](current_pos)
    
    def close(self):
        try:
            if self.device is not None:
                self.device.device.StopPolling()
                self.device.device.DisableDevice()
                self.device.device.Disconnect(True)
                self.device.device.Dispose()
            if self.device.executor:
                self.device.executor.shutdown(wait=True)

            print("Device closed properly")
        except Exception as ex:
            print(f"Error while closing: {ex}")
def main():
    try:
        device = KIM101('COM14')
        #device.set_Ch1(7900, 'SetGet')
        x1 = device.Ch1()
        x2 = device.Ch2()
        print(f"X1: {x1}, X2: {x2}")
    except Exception as ex:
        print(f"Exception occurred in KIM101: {ex}")
    finally:
        device.close()


if __name__ == '__main__':
    main()