
#============================================================================================

# imports and definitions #==================================================================


import datetime
import socket
import re
import time
import sys
import numpy as np




#============================================================================================

class dummy_wobbler:

	def __init__(self,device='/dev/wobbler',baud=9600,address='0'):
		self._initialized=False

		# Set device
		assert len(device), "Need to have a device of length at least 1"
		self._device=device
		self._baud=baud

		# Set the address
		assert len(address)==1, "Can only have 1-long characters as address"
		self._address=address

		# Device number is not initialized
		self.dev=None

		# Position initializations
		self._maxpos=40000
		self._minpos=0


	def wobbler_issue (self):
		assert not self._initialized
		assert not issue, "Cannot be used without a problem"

		time.sleep(1)
		self._initialized=True

	def close(self):
		assert self._initialized
		self._initialized=False

		
