from . import ACS
from .functions import Functions
from .pressures import Pressures
from .sampleValve import Samplevalve
from .system import System
from .main import Main
from .sample import Sample
from .membranePump import Membranepump
from .system_service import System_service
from .action import Action
from .compressor import Compressor
from .network import Network
from .access import Access
from .turboPump import Turbopump
from .tboard import Tboard
from .exchange import Exchange
from .pumpValve import Pumpvalve
from .breakVacuumValve import Breakvacuumvalve
from .update import Update
from .about import About


class Device(ACS.Device):
    def __init__(self, address):
        super().__init__(address)

        self.functions = Functions(self)
        self.pressures = Pressures(self)
        self.sampleValve = Samplevalve(self)
        self.system = System(self)
        self.main = Main(self)
        self.sample = Sample(self)
        self.membranePump = Membranepump(self)
        self.system_service = System_service(self)
        self.action = Action(self)
        self.compressor = Compressor(self)
        self.network = Network(self)
        self.access = Access(self)
        self.turboPump = Turbopump(self)
        self.tboard = Tboard(self)
        self.exchange = Exchange(self)
        self.pumpValve = Pumpvalve(self)
        self.breakVacuumValve = Breakvacuumvalve(self)
        self.update = Update(self)
        self.about = About(self)
        
        

def discover():
    return Device.discover("attodry800")
