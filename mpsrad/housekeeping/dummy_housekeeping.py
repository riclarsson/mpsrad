
#============================================================================================

# imports and definitions #==================================================================


import datetime
import socket
import re
import time
import numpy as np
import sys



#============================================================================================


class dummy_sensors:

	def __init__(self):
		self._initialized=False
		

	def init(self):
		self._sensors=['Temp0','Temp1','Temp2','Humidity']
		self._initialized=True


	def values(self):
		assert self._initialized, "Cannot run uninitialized machine"
		print("Running dummy sensors...")
		time.sleep(1)
		dummy_list=[]
		for i in range (len(self._sensors)):
			dummy_list.append(np.ones(7504))
		data=dict(zip(self._sensors,dummy_list))
		return(data)

	def C2K(self,temp):
		return (temp+273.15)

	def temperature(self, unit='K', sensor='Temp0'):
		assert self._initialized, "Cannot run uninitialized machine"
		temp=self.values()[sensor]
		if unit == 'K': return self.C2K(temp)
		return (temp)


	def humidity(self):
		assert self._initialized, "Cannot run uninitialized machine"
		return (self.values()['Humidity'])


	def close(self):
		assert self._initialized, "Cannot close uninitialized sensors"
		self._initialized=False
