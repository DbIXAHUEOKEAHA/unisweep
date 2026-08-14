from . import ACS
from .pressures import Pressures
from .valves import Valves
from .scrollPump import Scrollpump
from .functions import Functions
from .about import About
from .membranePump import Membranepump
from .heater import Heater
from .main import Main
from .update import Update
from .access import Access
from .turboPump import Turbopump
from .network import Network
from .system_service import System_service
from .compressor import Compressor
from .system import System
from .tboard import Tboard


class Device(ACS.Device):
    def __init__(self, address):
        super().__init__(address)

        self.pressures = Pressures(self)
        self.valves = Valves(self)
        self.scrollPump = Scrollpump(self)
        self.functions = Functions(self)
        self.about = About(self)
        self.membranePump = Membranepump(self)
        self.heater = Heater(self)
        self.main = Main(self)
        self.update = Update(self)
        self.access = Access(self)
        self.turboPump = Turbopump(self)
        self.network = Network(self)
        self.system_service = System_service(self)
        self.compressor = Compressor(self)
        self.system = System(self)
        self.tboard = Tboard(self)
        
        

def discover():
    return Device.discover("attodryevu")
