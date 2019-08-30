# -*- coding: utf-8 -*-
"""
Created: 07.03.2018

Last modification: 17.05.2019

Author: Borys Dabrowski

Controls the Chopper
"""
import serial

from time import time,sleep
from mpsrad.helper import serialCheck

class chopper:
	def __init__(self,device='/dev/chopper',offset=1000, sleeptime=0):
		"""
		Parameters:
			device (str):
				chopper device's path
			offset (int):
				**info**
		"""
		# Lock-check
		self._initialized=False
		self._device=device
		self._offset=offset
		self._oldpos=None
		self.sleeptime = sleeptime

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

	def set_cold(self):
		"""Sets the device pointing towards the cold load"""
		return self.set_pos('C')

	def set_ref(self):
		"""Sets the device pointing towards the reference source"""
		return self.set_pos('R')

	def set_hot(self):
		"""Sets the device pointing towards the hot load"""
		return self.set_pos('H')

	def set_ant(self,offset=None):
		"""Sets the device pointing towards the atmosphere"""
		pos='A'
		if offset is None: offset=self._offset
		pos=pos+str(offset)
		return self.set_pos(pos)

	def set_pos(self,new_pos):
		"""Sets the device pointing towards selected direction

		Must be initialized already.
		"""
		if isinstance(new_pos,str): new_pos=new_pos.encode()
		assert self._initialized, "Must first initialize the chopper"
		old_pos=self.get_pos()
		assert not old_pos[0]==b'E'[0], "Must reset the chopper controller"

		order=b"RAHC"
		try: a,b=order.index(old_pos[0]),order.index(new_pos[0])
		except:
			print("Old: ",old_pos)
			print("New: ",new_pos)
			with open("/home/dabrowski/error.msg","w") as file: file.write("Chopper error!")
			assert 0, "Chopper error"



		d=-1 if a>b else 1
		if old_pos[0]==new_pos[0]==b'A'[0]: r=[1]
		else: r=range(a,b+d,d)[1:]
		for n in r:
			if n==b: cmd=new_pos
			else: cmd=b'%c'%order[n]


# Quick fix for the chopper issue
#			if self._ask(cmd)[0]==b'E': return 1
			self._oldpos=cmd
			self._ask(cmd)

		sleep(self.sleeptime)

		return 0

	def get_pos(self):
		"""Gets the device pointing"""
		assert self._initialized, "Must first initialize the chopper"
		answ=self._ask('?')


# Quick fix for the chopper issue
		if answ[0]==b'E'[0]:
			answ=self._oldpos
			print("Problem with chopper, adjusting")
#			with open("/home/dabrowski/chopper.msg","ab") as file: file.write(b"%c\n"%answ)


		return answ

	def init(self):
		"""Connection with the chopper and set the device access

		Musn't be initialized already.
		"""
		assert not self._initialized, "Cannot init initialized chopper"
		checkserial=serialCheck.serialcheck()	#make sure to use pyserial
		self._serial=serial.Serial(self._device,115200,timeout=2)

		# get greetings
		greetings=self._ask('G')
		self._initialized=True
		return greetings

	def set_housekeeping(self, hk):
		""" Sets the housekeeping data dictionary.  hk must be dictionary """
		assert self._initialized, "Can set housekeeping when initialized"

		hk['Instrument']['Chopper'] = {"Position": self.get_pos()}

	def _close_and_restore(self):
		""" Close the device access"""
		assert self._initialized, "Cannot close uninitialized chopper"
		self._serial.close()
		self._initialized=False

	close=_close_and_restore
