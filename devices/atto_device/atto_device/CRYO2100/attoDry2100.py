from . import ACS
from .vti import Vti
from .dumpInValve import Dumpinvalve
from .system_service import System_service
from .main import Main
from .access import Access
from .scrollPump import Scrollpump
from .functions import Functions
from .network import Network
from .tboard import Tboard
from .condenser import Condenser
from .about import About
from .system import System
from .cryoInValve import Cryoinvalve
from .action import Action
from .sample import Sample
from .update import Update
from .stage40k import Stage40k
from .magnet import Magnet
from .pressures import Pressures
from .cryoOutValve import Cryooutvalve
from .dumpOutValve import Dumpoutvalve


class Device(ACS.Device):
    def __init__(self, address):
        super().__init__(address)

        self.vti = Vti(self)
        self.dumpInValve = Dumpinvalve(self)
        self.system_service = System_service(self)
        self.main = Main(self)
        self.access = Access(self)
        self.scrollPump = Scrollpump(self)
        self.functions = Functions(self)
        self.network = Network(self)
        self.tboard = Tboard(self)
        self.condenser = Condenser(self)
        self.about = About(self)
        self.system = System(self)
        self.cryoInValve = Cryoinvalve(self)
        self.action = Action(self)
        self.sample = Sample(self)
        self.update = Update(self)
        self.stage40k = Stage40k(self)
        self.magnet = Magnet(self)
        self.pressures = Pressures(self)
        self.cryoOutValve = Cryooutvalve(self)
        self.dumpOutValve = Dumpoutvalve(self)
        
        

def discover():
    return Device.discover("attodry2100")
