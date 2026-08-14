# -*- coding: utf-8 -*-
"""
ctypes file for adapting the cryostat dll to python. In order to run this on
your computer you must first register attoDRYLib.dll (located in the same
directory as this file) with Windows.

Created on Tue Mar  9 10:04:31 2021

@author: mccambria
"""


# %% Imports


# Usually 'import *' is bad practice, but it's the norm for ctypes
from ctypes import *


# %% Functions


def hello_world():
    print('hello world')
    
    
def load():
    # cdll.LoadLibrary('attoDRYLib') 
    # print(cdll.attoDRYLib)
    try:
        dll = CDLL('attoDRYLib.dll')
        return 'yeah!'
    except Exception as e:
        return e
    
if __name__ == "__main__":
    print(load())
    