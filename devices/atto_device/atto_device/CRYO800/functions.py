class Functions:
    def __init__(self, device):
        self.device = device
        self.interface_name = "com.attocube.cryostat.interface.functions"

    def checkAMCinRack(self):
        # type: () -> ()
        """
        If AMC is on Rack position 0, use it as DHCP server, else use it as DHCP client
        """
        
        response = self.device.request(self.interface_name + ".checkAMCinRack")
        self.device.handleError(response)
        return                 

