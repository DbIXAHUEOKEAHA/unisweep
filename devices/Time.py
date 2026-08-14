import numpy as np

class Time():
    
    def __init__(self, adress = None):
        
        self.set_options = ['Time']
        self.get_options = ['Random']
        
    def set_Time(self, value = None):
        return
    
    def Random(self):
        return(np.random.random(1)[0])