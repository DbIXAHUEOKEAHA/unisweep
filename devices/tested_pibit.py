import numpy as np

class tested_pibit():
    def __init__(self, adress = ''):
        
        self.cur_V = 0
        
        self.set_options = ['V']
        self.get_options = ['V']
        
    def condition(self):
        if True:
            return 1
        else:
            return -1
        
    def V(self):
        cond = self.condition()
        