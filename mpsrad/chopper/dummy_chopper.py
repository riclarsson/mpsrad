"""
Author: Yann Goument

Emulates the chopper's function in case of malfunction
"""

#============================================================================================

# imports and definitions #==================================================================


import datetime
import socket
import re
import time
import numpy as np
import sys




#============================================================================================

class dummy_hardware:
	
	def __init__(self,name):
		time.sleep(1)
		self._name=name

	def init (self):
		print("Issue in the", self._name, "initialization, switch on the dummy", self._name)

	def issue (self,function=None):
		if function == None:
			print("The function you want to use is not available on the dummy", self._name)
		else:
			print("The '",function,"' function you want to use is not available on the dummy", self._name)
