from ctypes import *
import time

if __name__ == '__main__':
    dllPath = "MRE_Controller_Data_Package\\WIN64\\MT_API.dll"
else:
    dllPath = "devices\\MRE_Controller_Data_Package\\WIN64\\MT_API.dll"


class MT24E():
    def __init__(self, adress):
        self.address = adress
        self.device = windll.LoadLibrary(dllPath)
        self.device.MT_Open_UART.argtypes = [c_char_p]
        self.device.MT_Init()
        charPointer = bytes(self.address, "gbk")
        self.device.MT_Open_UART(charPointer)
        
        iR = self.device.MT_Check()
        print("MT24E XYZ controller opened = ", bool(int(iR+1)))
            
        self.steps = 1000
        
        self.get_options = []
        self.set_options = []
        self.sweepable = [True, True, True]
        self.maxspeed = [10, 10, 10]
        
        self.set_default_speed()
        
        for i in range(3):
            self.__dict__[f'position_{i+1}'] = lambda i=i: self.position(i)
            self.__dict__[f'set_position_{i+1}'] = lambda value, speed=None, i=i: self.set_position(i, value, speed)
            self.get_options.append(f'position_{i+1}')
            self.set_options.append(f'position_{i+1}')
        
    def set_default_speed(self):
        
        self.device.MT_Set_Axis_Position_P_Target_Abs.argtypes = [c_int32, c_int32]
        self.device.MT_Set_Axis_Position_P_Target_Abs.restype  = None
        
        for i in range(3):
            self.device.MT_Set_Axis_Mode_Position_Open(i)
            #self.device.MT_Set_Axis_Mode_Position(i)
            self.device.MT_Set_Axis_Position_Acc(i, self.steps * 5)
            self.device.MT_Set_Axis_Position_Dec(i, self.steps * 5)
    
            self.device.MT_Set_Axis_Position_V_Max(i, self.steps * 5)
        
    def position(self, i):
        iPos = c_int32(0)
        pPos = pointer(iPos)

        self.device.MT_Get_Axis_Software_P_Now(c_int32(i), pPos)
        
        result = float(iPos.value) / self.steps
        
        return result
        
    def set_position(self, i, value, speed = None):
        if speed == None:
            speed = self.maxspeed[self.set_options.index(f'position_{i+1}')] * self.steps
        elif speed == 'SetGet':
            speed = self.maxspeed[self.set_options.index(f'position_{i+1}')] * self.steps
        else:
            maxspeed = self.maxspeed[self.set_options.index(f'position_{i+1}')] * self.steps
            speed = min(abs(speed)*self.steps, maxspeed)
    
        speed = int(speed)
    
        self.device.MT_Set_Axis_Mode_Position(c_int32(i))
        self.device.MT_Set_Axis_Position_V_Max(c_int32(i), c_int32(speed))
        
        steps_target = int(round(value * self.steps))
        self.device.MT_Set_Axis_Position_P_Target_Abs(c_int32(i), c_int32(steps_target))
        
    def close(self):
        # Close communication ports
        self.device.MT_Close_UART()
        self.device.MT_Close_Net()
        self.device.MT_Close_USB()

        # DeInit must be called last to release resources
        self.device.MT_DeInit()
        
def main():
    device = MT24E('COM16')
    try:
        p3 = device.position_3()
        print(p3)
        #device.set_position_3(0, 10)
        
    except Exception as ex:
        print(f'Exception happened: {ex}')
    finally:
        device.close()

if __name__ == '__main__':
    main()
    