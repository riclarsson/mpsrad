# -*- coding: utf-8 -*-
"""
Wobbler control for water vapor radiometer

Last modification: 19.06.2018
Author: Borys Dabrowski, dabrowski@mps.mpg.de
"""
import serial
from time import time,sleep

class wobbler:
	def __init__(self,device='/dev/wobbler',baud=115200,address="None"):
		self._initialized=False

		# Set device
		assert len(device), "Need to have a device of length at least 1"
		self._device=device
		self._baud=baud

		# Device number is not initialized
		self.dev=None

		# Position initializations
		self._maxpos=40000
		self._minpos=0
		self._pos=None

		self.maxWobblerFreq=5000
		self.stepLength=1.5625e-6

	def init(self,position,frequency=2000):
		assert not self._initialized, "Cannot init initialized wobbler"

		# Open a serial port
		self._serial=serial.Serial(self._device,self._baud,timeout=2)
		assert b'Wobbler' in self._ask("G"), "Wobbler is not responding"

		# Set the command to Go to Initialization + position
		self._ask("Z",timeout=20)

		self._setFrequency(frequency)
		self._dt=1/frequency

		# Finally, move to indicated position
		self._move(position)
		self._wait()

		self._initialized=True

	def close(self):
		""" Close the device access"""
		assert self._initialized, "Cannot close uninitialized wobbler"
		self._serial.close()
		self._initialized=False

	def _read(self):
		return self._serial.readline().replace(b'\r\n',b'')

	def _write(self,cmd):
		if isinstance(cmd,str): cmd=cmd.encode()
		self._serial.flushInput()
		self._serial.flushOutput()
		self._serial.write(cmd+b'\n')

	def _ask(self,cmd,timeout=2):
		self._serial.flushInput()
		self._serial.flushOutput()
		while self._serial.in_waiting==0:
			self._write(cmd)
			t0=time()
			while self._serial.in_waiting==0 and time()-t0<timeout: sleep(.1)

		return self._read()

	def move(self,position,unit='steps'):
		assert self._initialized, "Must initialize the wobbler before wait"
		self._move(position,unit)

	def _move(self,position,unit='steps'):
		if unit=='mm': position=int(position/self.stepLength)
		assert position<=self._maxpos and position>=self._minpos,\
		"Wobbler position is not within max-min positions"

		# Tell the machine to Go to Absolute position
		self._pos=position
		self._write("P"+str(self._pos))

	def wait(self, timeout=0):
		assert self._initialized, "Must initialize the wobbler before wait"
		return self._wait(timeout)

	def _wait(self, timeout=0):
		t0=time()
		while self._serial.in_waiting==0 and time()-t0<timeout: sleep(.01)
		self._read()
		assert self._pos==self._getPosition(), "Wobbler position not accurate"

		return 0

	def getFrequency(self):
		assert self._initialized, "Must first initialize the wobbler"
		return self._getFrequency()

	def _getFrequency(self):
		"""Ask the machine for the frequency it is moving with"""
		return int(self._ask("F?").replace(b'F:',b''))

	def setFrequency(self,frequency):
		assert self._initialized, "Must first initialize the wobbler"
		return self._setFrequency(frequency)

	def _setFrequency(self,frequency):
		"""Set the frequency the stepper is moving with"""
		return int(self._ask("F"+str(frequency)).replace(b'F:',b''))

	def getPosition(self,unit='steps'):
		assert self._initialized, "Must first initialize the wobbler"
		return self._getPosition(unit)

	def _getPosition(self,unit='steps'):
		"""Ask the machine where it think it is"""
		if unit=='mm': d=self.stepLength
		else: d=1
		return int(self._ask("P?").replace(b'P:',b''))*d

	def getFrequencyAndTime(self,f0,ti0_ms):
		maxti_ms=7500				# max integration time [ms]
		assert ti0_ms<=maxti_ms, "Integration time maximum %i ms"%maxti_ms
		ti0=ti0_ms*1e-3				# proposed integration time [s]

		c=3e8						# speed of light [m/s]
		d=self.stepLength			# step length [m]
		fwm=self.maxWobblerFreq		# max wobler frequency
		maxSteps=ti0*fwm				# max number of steps possible

		waveSteps=c/f0/d				# wavelength in steps

		N=maxSteps//waveSteps		# max number of full wavelengths on path
		assert N>0, "Integration time too short"

		fw=(N*waveSteps)//ti0		# wobbler frequency
		fw=int(5e5/(5e5//fw))		# rounding period to two microseconds

		ti_ms=N*waveSteps/fw//1e-3	# finding proper integration time [us]

		return int(fw),int(ti_ms)

	def get_recommended_movements(self,integration_time,le=4,st=1):
		ds=int(integration_time/self._dt/100.)*100+100
		position=self._pos*1
		if position-self._maxpos//2>0: ds*=-1

		assert not (le//2)%st, "Not cyclic"

		p=[]
		for i in range(le):
			position+=ds
			p.append(position)
			if not i % st: ds*=-1

		assert p[-1]==self._pos, "Not cyclic"
		return p
