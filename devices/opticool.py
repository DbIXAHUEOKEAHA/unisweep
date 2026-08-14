import MultiPyVu as mpv
#from MultiPyVu import MultiVuClient as mvc
from enum import IntEnum

import time

MAX_TRIES = 3
#import socket
#from MultiPyVu.SocketMessageClient import ClientMessage
#from MultiPyVu.instrument import MultiVuExeException
#from typing import Dict
#import time
#import sys
#if sys.platform == 'win32':
#    try:
#        import msvcrt    # Used to help detect the esc-key
#    except ImportError:
#        print("Must import the pywin32 module.  Use:  ")
#        print("\tconda install -c conda-forge pywin32")
#        print("   or")
#       print("\tpip install pywin32")
#        sys.exit(0)

'''
class client(mvc.MultiVuClient):
    
    def __enter__(self):
        self.logger.info(f'Starting connection to {self._addr}')
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setblocking(False)
        self.sock.connect_ex(self._addr)

        self._message = ClientMessage(self._sel,
                                      self.sock,
                                      )
        # send a request to the sever to confirm a connection
        max_tries = 1
        action = 'START'
        for attempt in range(max_tries):
            try:
                self.response = self._send_and_receive(action)
            except OSError as e:
                msg = f'Attempt {attempt + 1} of {max_tries} failed:  {e}'
                self.logger.info(msg)
                time.sleep(1)
                if attempt == max_tries - 1:
                    err_msg = 'Failed to make a connection to the '
                    err_msg += 'server.  Check if the MultiVuServer '
                    err_msg += 'is running.'
                    self.logger.info(err_msg)
            else:
                self.logger.info(self.response['result'])
                break

        return self
    
    def _monitor_and_get_response(self) -> Dict[str, str]:
        #This monitors the traffic going on.  It asks the SocketMessageClient
        #class for help in understanding the data.  This is also used to handle
        #he possible errors that SocketMessageClient could generate.

        #Raises
        #------
        #ConnectionRefusedError
        #    Could be raised if the server is not running.
        #ConnectionError
        #    Could be raised if there are connection issues with the server.
        #KeyboardInterrupt
        #    This is used by the user to close the connection.
        #MultiVuExeException
        #    Raised if there are issues with the request for MultiVu commands.

        #Returns
        #-------
        #TYPE
        #    The information retrived from the socket and interpreted by
        #    SocketMessageClient class.

        while True:
            events = self._sel.select(timeout=self._socketIoTimeout)
            if events:
                for key, mask in events:
                    message = key.data
                    try:
                        message.process_events(mask)
                    except ConnectionAbortedError as e:
                        # Client closed the server
                        raise ConnectionAbortedError from e
                    except ConnectionError as e:
                        # Client closed the client
                        raise ConnectionError from e
                    except Exception:
                        self._close_and_exit()
                    else:
                        # Windows looks for the ESC key to quit.
                        if sys.platform == 'win32':
                            escKey = chr(27)
                            if (msvcrt.kbhit()
                                    and msvcrt.getch().decode() == escKey):
                                self._thread_running = False
                                raise KeyboardInterrupt
                        # return the response
                        self.response = message.response
                        if (self.response is not None
                                and message.request is None):
                            rslt = self.response['result']
                            if rslt.startswith('MultiVuError:'):
                                self.logger.info(self.response['result'])
                                message.close()
                                raise MultiVuExeException(rslt)
                            else:
                                return self.response
            else:
                # An empty list means the selector timed out
                msg = 'Socket timed out after '
                msg += f'{self._socketIoTimeout} seconds.'
                raise TimeoutError(msg)
            # Check for a socket being monitored to continue.
            if not self._sel.get_map():
                break
'''

class opticool():
    def __init__(self, adress = '192.168.0.181:5000'):
        host, port = adress.split(':')
        port = int(port)
        
        timeout = 1 #s
        
        self._addr = (host, port)
        self._socket_timeout = timeout
        self._message = None     # ClientMessage object
        self._sock = None
        self._request = {}
        self._response = {}
        self._instr = None
        self.instrument_name = ''
        
        self.device = mpv.Client(host=host, port = port, socket_timeout = timeout)
        self.device.open()
        self.T_states = self.device.temperature.state_code_dict()
        self._T_approach = self.device.temperature.approach_mode(1)
        self._Field_approach = self.device.field.approach_mode(0)
        self._Field_driven = self.device.field.driven_mode(1)
        self._chamber_state = self.device.chamber.mode(1)
        #self._T_rate = self.device.temperature.set_rate_per_min
        #self._Field_rate = self.device.field.set_rate_per_sec
        self.set_options = ['T_sample', 'T_finger', 'Field', 'T_rate', 'Field_rate', 'T_approach', 'Field_approach', 'Field_driven']
        self.get_options = ['T_sample', 'T_finger', 'Field', 'T_rate', 'Field_rate', 'T_approach', 'Field_approach', 'Field_driven']
        self.sweepable = [True, True, True, False, False, False, False, False]
        self.maxspeed = [5, 5, self.max_Field_speed(), None, None, None, None, None, None]
        self.eps = [0.05, 0.05, 50, None, None, None, None, None, None]
    
    
    def max_Field_speed(self):
        '''
        if not hasattr(self, 'cur_field'):
            self.Field()
        if abs(self.cur_Field) < 60050 and abs(self.cur_Field) >= 0:
            return 110
        elif abs(self.cur_Field) < 65050 and abs(self.cur_Field) >= 60050:
            return 30
        elif abs(self.cur_Field) < 80000 and abs(self.cur_Field) >= 65050:
            return 10
        '''
        return 110
    
    def Field(self):
        self.cur_Field, self.state_Field = self.device.get_field()
        result = self.cur_Field
        return result

    def Field_approach(self):
        
        """
        linear = 0
        no_overshoot = 1
        oscillate = 2
        """
        
        return self._Field_approach.value
    
    def Field_driven(self):
        
        """
        persistent = 0
        driven = 1
        """
        
        return self._Field_driven.value

    def T_approach(self):
        
        """
        fast_settle = 0
        no_overshoot = 1
        """
        
        return self._T_approach.value

    def T_sample(self):
        self.sample_temperature, self.sample_temperature_status = self.device.get_aux_temperature()
        result = self.sample_temperature
        time.sleep(0.05)
        return result

    def T_finger(self):
       self.temperature, self.state_temperature = self.device.get_temperature()
       result = self.temperature
       time.sleep(0.05)
       return result
   
    def T_rate(self):
        return self._T_rate
    
    def Field_rate(self):
        return self._Field_rate
   
    def set_T_rate(self, value):
        maxspeed = self.maxspeed[self.set_options.index('T_finger')]
        if value > maxspeed:
            value = maxspeed
        self._T_rate = float(value)
        self.device.temperature.set_rate_per_min = self._T_rate
    
    def set_Field_rate(self, value):
        maxspeed = self.maxspeed[self.set_options.index('Field')]
        if value > maxspeed:
            value = maxspeed
        self._Field_rate = float(value)
        self.device.field.set_rate_per_sec = self._Field_rate
    
    def Field_state(self):
        if hasattr(self, 'state_Field'):
            result = self.state_Field
        else:
            self.Field()
            result = self.state_Field
        return result
    
    def T_state(self):
        if hasattr(self, 'state_temperature'):
            result = self.state_temperature
        else:
            self.T()
            result = self.state_temperature
        return result
    
    def set_T_finger(self, value, speed = None):
        """

        Parameters
        ----------
        value : float, target temperature
        speed : rate per minute
        Units: K
        max is 1.

        """
        
        
        maxspeed = self.maxspeed[self.set_options.index('T_finger')]
        
        if speed == None:
            speed = maxspeed
                
        elif speed == 'SetGet':
            speed = self._T_rate
        
        else:
            speed = abs(speed)
            speed = min(float(speed), maxspeed)
            
        #checking minimum speed
        if speed < 0.5:
            speed = 0.5
        
        #self._T_rate = 1
        self.set_T_rate(speed)
        self.device.temperature.set_point = value
        self.device.set_temperature(value, self._T_rate, self._T_approach)
        
    def set_T_sample(self, value, speed = None):
        self.set_T_finger(value, speed)
        
    def set_T_approach(self, value):
        
        value = int(value)
        
        class ApproachEnum(IntEnum):
            fast_settle = 0
            no_overshoot = 1
        
        self._T_approach = ApproachEnum(value)
        self.device.temperature.set_approach = self._T_approach.value
        
    def set_Field(self, value, speed = None):
        """

        Parameters
        ----------
        value : float, target temperature
        speed : rate per second
        Units : Oe
        max is 1.

        """
        
        print(f'Value = {value}, speed = {speed}')
        
        maxspeed = self.maxspeed[self.set_options.index('Field')]
        
        if speed == None:
            speed = maxspeed
                
        elif speed == 'SetGet':
            speed = self._T_rate
        
        else:
            speed = abs(speed)
            speed = min(float(speed), maxspeed)
        
        self.set_Field_rate(speed)
        
        #self._Field_rate = 50
        self.device.field.set_point = value
        self.device.set_field(value, self._Field_rate, self._Field_approach)
    
    def set_Field_approach(self, value):
        
        value = int(value)
        
        class ApproachEnum(IntEnum):
            linear = 0
            no_overshoot = 1
            oscillate = 2
        
        self._Field_approach = ApproachEnum(value)
        self.device.field.set_approach = self._Field_approach.value
        
    def set_Field_driven(self, value):
        
        value = int(value)
        
        class drivenEnum(IntEnum):
            persistent = 0
            driven = 1
        
        self._Field_driven = drivenEnum(value)
        self.device.field.set_driven = self._Field_driven.value
        
    def stop(self):
        self.device.close_client()
    
def main():
    device = opticool('192.168.0.100:5000')
    print(f'Field = {device.Field()} Oe')
    print(f'Cold finger temp = {device.T_finger()} K')
    #print(f'Aux temp = {device.T_sample()} K')
    #device.set_T_finger(2)
    device.stop()
    
if __name__ == '__main__':
    main()
