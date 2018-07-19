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

class dummy_chopper:
	
	def __init__(self,device='/dev/chopper',offset=1000):
		# Lock-check
		self._initialized=False
		self._device=device
		self._offset=offset

	def chopper_issue (self):
		assert not self._initialized
		
		print("Switch on a dummy chopper...")
		time.sleep(1)
		self._initialized=True

	def close (self):
		assert self._initialized
		print('Closing the dummy chopper')
		self._initialized=False
		
