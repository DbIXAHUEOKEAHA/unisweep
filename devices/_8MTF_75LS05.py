from libximc import *
from ctypes import *
import time

import sys
import glob
import serial

class _8MTF_75LS05():
    def __init__(self, adress = 'COM9'):
        print(f'XStage adress is {adress}')
        num = [str(int(x)) for x in adress if x.isdigit()]
        ind = ''
        for i in num:
            ind  += i
        self.open_name = b'xi-com:\\\\.\\COM' + bytes(ind, encoding = 'utf-8')
        self.device_id = lib.open_device(self.open_name)
        self.open_device()
        
        self.worst_result = Result.Ok
        self.result = Result.Ok
        # Create engine settings structure
        self.eng = engine_settings_t()
        result_eng = lib.get_engine_settings(self.device_id, byref(self.eng))

        # Create user unit settings structure
        self.user_unit = calibration_t()
        self.user_unit.MicrostepMode = self.eng.MicrostepMode
        self.user_unit.A = 1 / 380
        
        self.commands = [None]
        
        self.set_options = ['position', 'shift']
        self.sweepable = [True, True]
        self.maxspeed = [20, 20]
        self.eps = [0.01, 0.01]
        self.get_options = ['position', 'I_pwr', 'U_pwr', 'T_proc']
        
        self.left_border = -14250
        self.right_border = 14250
        self.fasthome = 500
        self.slowhome = 500
        self.homedelta = 15000
        self.speed = 2000
        self.accel = 2000
        self.decel = 5000
        
    def settings(self, lib, id):
        worst_result = Result.Ok
        result = Result.Ok

        feedback_settings = feedback_settings_t()

        feedback_settings.IPS = 4000
        class FeedbackType_:
            FEEDBACK_ENCODER_MEDIATED = 6
            FEEDBACK_NONE = 5
            FEEDBACK_EMF = 4
            FEEDBACK_ENCODER = 1
        feedback_settings.FeedbackType = FeedbackType_.FEEDBACK_EMF
        class FeedbackFlags_:
            FEEDBACK_ENC_TYPE_BITS = 192
            FEEDBACK_ENC_TYPE_DIFFERENTIAL = 128
            FEEDBACK_ENC_TYPE_SINGLE_ENDED = 64
            FEEDBACK_ENC_REVERSE = 1
            FEEDBACK_ENC_TYPE_AUTO = 0
        feedback_settings.FeedbackFlags = FeedbackFlags_.FEEDBACK_ENC_TYPE_SINGLE_ENDED | FeedbackFlags_.FEEDBACK_ENC_TYPE_AUTO
        feedback_settings.CountsPerTurn = 4000
        result = lib.set_feedback_settings(id, byref(feedback_settings))

        if result != Result.Ok:
            if worst_result == Result.Ok or worst_result == Result.ValueError:
                worst_result = result

        home_settings = home_settings_t()

        home_settings.FastHome = self.fasthome
        home_settings.uFastHome = 0
        home_settings.SlowHome = self.slowhome
        home_settings.uSlowHome = 0
        home_settings.HomeDelta = self.homedelta
        home_settings.uHomeDelta = 0
        class HomeFlags_:
            HOME_USE_FAST = 256
            HOME_STOP_SECOND_BITS = 192
            HOME_STOP_SECOND_LIM = 192
            HOME_STOP_SECOND_SYN = 128
            HOME_STOP_SECOND_REV = 64
            HOME_STOP_FIRST_BITS = 48
            HOME_STOP_FIRST_LIM = 48
            HOME_STOP_FIRST_SYN = 32
            HOME_STOP_FIRST_REV = 16
            HOME_HALF_MV = 8
            HOME_MV_SEC_EN = 4
            HOME_DIR_SECOND = 2
            HOME_DIR_FIRST = 1
        home_settings.HomeFlags = HomeFlags_.HOME_USE_FAST | HomeFlags_.HOME_STOP_SECOND_REV | HomeFlags_.HOME_STOP_FIRST_BITS | HomeFlags_.HOME_DIR_SECOND
        result = lib.set_home_settings(id, byref(home_settings))

        if result != Result.Ok:
            if worst_result == Result.Ok or worst_result == Result.ValueError:
                worst_result = result

        move_settings = move_settings_t()

        move_settings.Speed = self.speed
        move_settings.uSpeed = 0
        move_settings.Accel = self.accel
        move_settings.Decel = self.decel
        move_settings.AntiplaySpeed = 2000
        move_settings.uAntiplaySpeed = 0
        class MoveFlags_:
            RPM_DIV_1000 = 1

        result = lib.set_move_settings(id, byref(move_settings))

        if result != Result.Ok:
            if worst_result == Result.Ok or worst_result == Result.ValueError:
                worst_result = result

        engine_settings = engine_settings_t()

        engine_settings.NomVoltage = 360
        engine_settings.NomCurrent = 670
        engine_settings.NomSpeed = 4000
        engine_settings.uNomSpeed = 0
        class EngineFlags_:
            ENGINE_LIMIT_RPM = 128
            ENGINE_LIMIT_CURR = 64
            ENGINE_LIMIT_VOLT = 32
            ENGINE_ACCEL_ON = 16
            ENGINE_ANTIPLAY = 8
            ENGINE_MAX_SPEED = 4
            ENGINE_CURRENT_AS_RMS = 2
            ENGINE_REVERSE = 1
        engine_settings.EngineFlags = EngineFlags_.ENGINE_LIMIT_RPM | EngineFlags_.ENGINE_ACCEL_ON | EngineFlags_.ENGINE_REVERSE
        engine_settings.Antiplay = 1800
        class MicrostepMode_:
            MICROSTEP_MODE_FRAC_256 = 9
            MICROSTEP_MODE_FRAC_128 = 8
            MICROSTEP_MODE_FRAC_64 = 7
            MICROSTEP_MODE_FRAC_32 = 6
            MICROSTEP_MODE_FRAC_16 = 5
            MICROSTEP_MODE_FRAC_8 = 4
            MICROSTEP_MODE_FRAC_4 = 3
            MICROSTEP_MODE_FRAC_2 = 2
            MICROSTEP_MODE_FULL = 1
        engine_settings.MicrostepMode = MicrostepMode_.MICROSTEP_MODE_FRAC_256
        engine_settings.StepsPerRev = 200
        result = lib.set_engine_settings(id, byref(engine_settings))

        if result != Result.Ok:
            if worst_result == Result.Ok or worst_result == Result.ValueError:
                worst_result = result

        entype_settings = entype_settings_t()

        class EngineType_:
            ENGINE_TYPE_BRUSHLESS = 5
            ENGINE_TYPE_TEST = 4
            ENGINE_TYPE_STEP = 3
            ENGINE_TYPE_2DC = 2
            ENGINE_TYPE_DC = 1
            ENGINE_TYPE_NONE = 0
        entype_settings.EngineType = EngineType_.ENGINE_TYPE_STEP | EngineType_.ENGINE_TYPE_NONE
        class DriverType_:
            DRIVER_TYPE_EXTERNAL = 3
            DRIVER_TYPE_INTEGRATE = 2
            DRIVER_TYPE_DISCRETE_FET = 1
        entype_settings.DriverType = DriverType_.DRIVER_TYPE_INTEGRATE
        result = lib.set_entype_settings(id, byref(entype_settings))

        if result != Result.Ok:
            if worst_result == Result.Ok or worst_result == Result.ValueError:
                worst_result = result

        power_settings = power_settings_t()

        power_settings.HoldCurrent = 50
        power_settings.CurrReductDelay = 1000
        power_settings.PowerOffDelay = 60
        power_settings.CurrentSetTime = 300
        class PowerFlags_:
            POWER_SMOOTH_CURRENT = 4
            POWER_OFF_ENABLED = 2
            POWER_REDUCT_ENABLED = 1
        power_settings.PowerFlags = PowerFlags_.POWER_SMOOTH_CURRENT | PowerFlags_.POWER_REDUCT_ENABLED
        result = lib.set_power_settings(id, byref(power_settings))

        if result != Result.Ok:
            if worst_result == Result.Ok or worst_result == Result.ValueError:
                worst_result = result

        secure_settings = secure_settings_t()

        secure_settings.LowUpwrOff = 800
        secure_settings.CriticalIpwr = 4000
        secure_settings.CriticalUpwr = 5500
        secure_settings.CriticalT = 800
        secure_settings.CriticalIusb = 450
        secure_settings.CriticalUusb = 520
        secure_settings.MinimumUusb = 420
        class Flags_:
            ALARM_ENGINE_RESPONSE = 128
            ALARM_WINDING_MISMATCH = 64
            USB_BREAK_RECONNECT = 32
            ALARM_FLAGS_STICKING = 16
            ALARM_ON_BORDERS_SWAP_MISSET = 8
            H_BRIDGE_ALERT = 4
            LOW_UPWR_PROTECTION = 2
            ALARM_ON_DRIVER_OVERHEATING = 1
        secure_settings.Flags = Flags_.ALARM_ENGINE_RESPONSE | Flags_.ALARM_FLAGS_STICKING | Flags_.ALARM_ON_BORDERS_SWAP_MISSET | Flags_.H_BRIDGE_ALERT | Flags_.ALARM_ON_DRIVER_OVERHEATING
        result = lib.set_secure_settings(id, byref(secure_settings))

        if result != Result.Ok:
            if worst_result == Result.Ok or worst_result == Result.ValueError:
                worst_result = result

        edges_settings = edges_settings_t()

        class BorderFlags_:
            BORDERS_SWAP_MISSET_DETECTION = 8
            BORDER_STOP_RIGHT = 4
            BORDER_STOP_LEFT = 2
            BORDER_IS_ENCODER = 1
        edges_settings.BorderFlags = BorderFlags_.BORDER_STOP_RIGHT | BorderFlags_.BORDER_STOP_LEFT
        class EnderFlags_:
            ENDER_SW2_ACTIVE_LOW = 4
            ENDER_SW1_ACTIVE_LOW = 2
            ENDER_SWAP = 1
        edges_settings.EnderFlags = EnderFlags_.ENDER_SW2_ACTIVE_LOW | EnderFlags_.ENDER_SW1_ACTIVE_LOW | EnderFlags_.ENDER_SWAP
        edges_settings.LeftBorder = self.left_border
        edges_settings.uLeftBorder = 0
        edges_settings.RightBorder = self.right_border
        edges_settings.uRightBorder = 0
        result = lib.set_edges_settings(id, byref(edges_settings))

        if result != Result.Ok:
            if worst_result == Result.Ok or worst_result == Result.ValueError:
                worst_result = result
        
    def open_device(self):
        if self.device_id <= 0:
            for device_id in [1, 2]:
                lib.close_device(byref(cast(device_id, POINTER(c_int))))
            self.device_id = lib.open_device(self.open_name)
        
    def status_running(self):
        """
    
        Returns True if motor is running
                False if motor is not running
        """
        def get_status():
            """
            A function of reading status information from the device
            You can use this function to get basic information about the device status.
            
            :param lib: structure for accessing the functionality of the libximc library.
            :param device_id:  device id.
            """
            
            x_status = status_t()
            result = lib.get_status(self.device_id, byref(x_status))
            if result == Result.Ok:
                return x_status
            else:
                return None
        
        currStatus = get_status()
        if currStatus != None:
            return (currStatus.MvCmdSts & MvcmdStatus.MVCMD_RUNNING)
    
    def set_left_border(self, value = -75):
        """
        Set left border
        """
        self.left_border = int(value / self.user_unit.A)
        self.settings(lib, self.device_id)
                
    def set_right_border(self, value = 75):
        """
        Set right border
        """
        self.right_border = int(value / self.user_unit.A)
        self.settings(lib, self.device_id)
    
    def set_position(self, value, speed = None):
        
        if speed == None:
            if  not self.status_running():
                result = lib.command_move_calb(self.device_id, c_float(value), byref(self.user_unit))
        else:
            speed = abs(speed)
            if  not self.status_running():
                self.set_speed(speed)
                result = lib.command_move_calb(self.device_id, c_float(value), byref(self.user_unit))
    
    def set_shift(self, value, speed = None):
        if speed == None:
            if  not self.status_running():
                result = lib.command_movr_calb(self.device_id, c_float(value), byref(self.user_unit))
        else:
            speed = abs(speed)
            if  not self.status_running():
                self.set_speed(speed)
                result = lib.command_movr_calb(self.device_id, c_float(value), byref(self.user_unit))
        
    def position(self):
        """
        Obtaining information about the position of the positioner.
        
        This function allows you to get information about the current positioner coordinates,
        both in steps and in encoder counts, if it is set.
        Also, depending on the state of the mode parameter, information can be obtained in user units.
        
        :param lib: structure for accessing the functionality of the libximc library.
        :param device_id: device id.
        :param mode: mode in feedback counts or in user units. (Default value = 1)
        """
        x_pos = get_position_calb_t()
        self.result = lib.get_position_calb(self.device_id, byref(x_pos), byref(self.user_unit))
        if self.result == Result.Ok:
            return x_pos.Position
        else:
            return 'Could not get a position'
        
    def home_speed1(self, value = 2.5):
        """
        value - Speed used for first motion.
        """
        
        self.fasthome = int(value / self.user_unit.A)
        self.settings(lib, self.device_id)
                
    def home_speed2(self, value = 1.5):
        """
        value - Speed used for second motion.
        """
        self.slowhome = int(value / self.user_unit.A)
        self.settings(lib, self.device_id)
        
    def home_delta(self, value = 1):
        """
        value - Distance from break point.
        """
        self.homedelta = int(value / self.user_unit.A)
        self.settings(lib, self.device_id)
        
    def set_speed(self, value = 5):
        """
        Set speed as user units / sec range(0, 20)
        """
        
        maxspeed = self.maxspeed[self.set_options.index('position')]
        
        if value == 'SetGet':
            value = self.speed * self.user_unit.A
        
        elif value == None:
            value = maxspeed
            
        else:
            value = min(float(value), maxspeed)
        
        self.speed = int(value / self.user_unit.A)
        self.settings(lib, self.device_id)
                
    def set_accel(self, value = 10):
        """
        Motor shaft acceleration, steps/s^2(stepper motor)
        """
        
        self.accel = int(value / self.user_unit.A)
        self.settings(lib, self.device_id)
                
    def set_decel(self, value = 10):
        """
        Motor shaft acceleration, steps/s^2(stepper motor)
        """
        
        self.decel = int(value / self.user_unit.A)
        self.settings(lib, self.device_id)
    
    def I_pwr(self):
        '''
        Consumable current on a power part, A
        '''
        status = status_t()
        result_status = lib.get_status(self.device_id, byref(status))

        return status.Ipwr * 1e-3
        
    def U_pwr(self):
        '''
        Consumable voltage on a power part, V
        '''
        status = status_t()
        result_status = lib.get_status(self.device_id, byref(status))

        return status.Upwr * 1e-3
        
    def T_proc(self):
        '''
        Current temperature of CPU
        '''
        status = status_t()
        result_status = lib.get_status(self.device_id, byref(status))

        return status.CurT / 10

    def stop(self):

        currStatus = status_t()
        currStatus.MvCmdSts = 0x08
        
        self.result = lib.get_status(self.device_id, byref(currStatus))
        print(self.result)

    def close(self):
        lib.close_device(byref(cast(self.device_id, POINTER(c_int))))

def main():
    adress = 'COM4'
    stage = _8MTF_75LS05(adress)  
    stage.set_position(25.7955284118652, 10)

    try:
        print(f'Current position is {stage.position()}')
    except:
        stage.close()
    finally:
        stage.close()
        
if __name__ == '__main__':
    main()