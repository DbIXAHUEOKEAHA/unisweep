from . import ACS
from .functions import Functions
from .nlc import Nlc
from .manual import Manual
from .about import About
from .realtime import Realtime
from .displacement import Displacement
from .pilotlaser import Pilotlaser
from .access import Access
from .axis import Axis
from .update import Update
from .system import System
from .adjustment import Adjustment
from .ecu import Ecu
from .network import Network
from .system_service import System_service
try:
    from streaming.streaming import Streaming
except:
    pass


class Device(ACS.Device):
    def __init__(self, address):
        super().__init__(address)

        self.functions = Functions(self)
        self.nlc = Nlc(self)
        self.manual = Manual(self)
        self.about = About(self)
        self.realtime = Realtime(self)
        self.displacement = Displacement(self)
        self.pilotlaser = Pilotlaser(self)
        self.access = Access(self)
        self.axis = Axis(self)
        self.update = Update(self)
        self.system = System(self)
        self.adjustment = Adjustment(self)
        self.ecu = Ecu(self)
        self.network = Network(self)
        self.system_service = System_service(self)
        
        try:
            self.streaming = Streaming(self)
        except NameError as e:
            if "Streaming" in str(e):
                print("Warning: Streaming is not supported on your platform")
            else:
                raise e
        

def discover():
    return Device.discover("ids")
