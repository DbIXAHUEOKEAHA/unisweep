from . import ACS
from .rtin import Rtin
from .control import Control
from .res import Res
from .rtout import Rtout
from .description import Description
from .update import Update
from .rotcomp import Rotcomp
from .test import Test
from .functions import Functions
from .status import Status
from .system_service import System_service
from .diagnostic import Diagnostic
from .amcids import Amcids
from .move import Move
from .network import Network
from .about import About
from .access import Access


class Device(ACS.Device):
    def __init__(self, address):
        super().__init__(address)

        self.rtin = Rtin(self)
        self.control = Control(self)
        self.res = Res(self)
        self.rtout = Rtout(self)
        self.description = Description(self)
        self.update = Update(self)
        self.rotcomp = Rotcomp(self)
        self.test = Test(self)
        self.functions = Functions(self)
        self.status = Status(self)
        self.system_service = System_service(self)
        self.diagnostic = Diagnostic(self)
        self.amcids = Amcids(self)
        self.move = Move(self)
        self.network = Network(self)
        self.about = About(self)
        self.access = Access(self)
        
        

def discover():
    return Device.discover("amc")
