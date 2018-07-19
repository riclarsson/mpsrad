"""
Author: Yann Goument

Emulate the spectrometer in case of dysfunction
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


class dummy_spectrometer:
	
	def __init__(self,
			name="rcts104",
			host="sofia4",
			tcp_port=1788,
			udp_port=None,
			channels=7504,
			integration_time=1000,
			blank_time=None,
			data_storage_containers=4):

		self.name=name

		# Lock-check
		self._initialized=False
		self._sent=False

		# Set the runtime
		self._runtime=integration_time*1e-3

		# Constants
		self._channels=channels
		self._copies_of_vectors=int(data_storage_containers)

		# Host information
		self._tcp_port=tcp_port
		self._host=host

	def data (self):
		
		time.sleep(.5)
		print('Switch on dummy spectrometer...')
		time.sleep(.5)
		
		# Initiate data
		self._data=[]
		for i in range(self._copies_of_vectors):
			#matrix of -1 for data
			self._data.append(np.full((self._channels),-1, dtype=np.float64))
			

		
		# We are now initialize	
		self._initialized=True
		
		dummy_data=save_data()
		
		


	def save_data (self, basename="/home/dabrowski/data/test/CTS", file=None, binary=True):
		
		assert self._initialized
		now=datetime.datetime,now()
		if file is None:
			filename=self._hostname + now.strftime("-%Y%m%d%H%M%S-%f")
		else:
			filename=str(file)

		if binary: np.save(basename+ file, self._data)
		else: np.savetxt(basename+filename, self._data)

		print(' Dummy data save in %s %s' %(basename,filename))
		return(filename)




	def close(self):
		assert not self._initialized, "Can't close if no data"
		self._initialized=False



#============================================================================================

