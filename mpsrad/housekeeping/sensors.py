# -*- coding: utf-8 -*-
"""
Created: 26.04.2018

Author: Borys Dabrowski

Last modification: 09.07.2018

Get the temperature of... in order to ...
"""

from . import dummy_housekeeping
import serial
from time import time,sleep

try : 
	a=serial.Serial
	del(a)
except :
	raise RuntimeError('Please install pyserial, not serial')

class sensors:
	def __init__(self,device='/dev/sensors'):
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
		assert not self._initialized, "Cannot init initialized sensors"
		try :
			self._serial=serial.Serial(self._device,115200,timeout=2)

			self._sensors=['Temp0','Temp1','Temp2','Humidity']
			# get greetings
			greetings=self._ask('GS')
			self._initialized=True
			return greetings
		except :
			self._dummy_sensors=dummy_housekeeping.dummy_sensors()

	def get_values(self):
		assert self._initialized, "Cannot run uninitialized machine"
		values=self._get_values()
		return dict(zip(self._sensors,values))

	def C2K(self,temp):
		return temp+273.15

	def get_temperature(self, unit='K',sensor='Temp0'):
		assert self._initialized, "Cannot run uninitialized machine"
		temp=self.get_values()[sensor]
		if unit == 'K': return self.C2K(temp)
		return temp

	def get_humidity(self):
		assert self._initialized, "Cannot run uninitialized machine"
		return self._get_values()[3]

	def _close_and_restore(self):
		""" Close the device access"""
		assert self._initialized, "Cannot close uninitialized sensors"
		self._serial.close()
		self._initialized=False

	close=_close_and_restore
