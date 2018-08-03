# -*- coding: utf-8 -*-
"""
Created: 26.04.2018

Author: Borys Dabrowski

Last modification: 09.07.2018

Get the temperature of various external sensors in order to store as housekeeping data
"""

from . import dummy_housekeeping
import serial
from time import time,sleep
from mpsrad.helper import serialCheck

class sensors:
	"""Get the temperature of various external sensors in order to store as housekeeping data
	"""
	def __init__(self,device='/dev/sensors'):
		"""
		Parameters:
			device (str):
				sensors device's path
		"""
		# Lock-check
		self._initialized=False
		self._device=device

	def _ask(self,cmd):
		if isinstance(cmd,str): cmd=cmd.encode()
		self._serial.flushInput()

		while self._serial.in_waiting==0:
			self._serial.flushInput()
			self._serial.write(cmd+b'\n')
			t0=time()
			while self._serial.in_waiting==0 and time()-t0<1: sleep(.01)

		answ=self._serial.readline().replace(b'\r\n',b'')

		return answ

	def _get_values(self):
		values=self._ask('S').replace(b'Read fail',b'').replace(b'S:',b'')
		values=[float(n) for n in values.split(b',')]
		return values

	def init(self):
		"""Set the connection to the device

		Musn't be initialized already.
		"""
		assert not self._initialized, "Cannot init initialized sensors"
		checkserial=serialCheck.serialcheck()	#make sure to use pyserial
		try :
			self._serial=serial.Serial(self._device,115200,timeout=2)

			self._sensors=['Temp0','Temp1','Temp2','Humidity']
			# get greetings
			greetings=self._ask('GS')
			self._initialized=True
			return greetings
		except :
			print('Dummy sensors...')
			self._dummy_sensors=dummy_housekeeping.dummy_sensors()

	def get_values(self):
		"""Function to obtain values from the sensor
		"""
		assert self._initialized, "Cannot run uninitialized machine"
		values=self._get_values()
		return dict(zip(self._sensors,values))

	def C2K(self,temp):
		"""Convert Celius to Kelvin
		"""
		return temp+273.15

	def get_temperature(self, unit='K',sensor='Temp0'):
		"""Get the temperature of the atmosphere
		"""
		assert self._initialized, "Cannot run uninitialized machine"
		temp=self.get_values()[sensor]
		if unit == 'K': return self.C2K(temp)
		return temp

	def get_humidity(self):
		"""Get the humidity values of the atmosphere
		"""
		assert self._initialized, "Cannot run uninitialized machine"
		return self._get_values()[3]

	def _close_and_restore(self):
		""" Close the device access"""
		assert self._initialized, "Cannot close uninitialized sensors"
		self._serial.close()
		self._initialized=False

	close=_close_and_restore
