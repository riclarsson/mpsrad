#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Dec  4 16:11:55 2017

Author: Richard Larsson

Quick and dirty connection to the DBR computer to execute commands that changes
the frequency settings of the machine.  Remember to set the correct frequency
in the Reference Local Oscillator before executing this code
"""

try:
	from xmlrpc.client import ServerProxy
except:
	from xmlrpclib import ServerProxy

from . import dummy_frontend

class dbr:
	# Constants:
	band3switch = 246
	reflimits = (13, 16.4)
	gunnlimits = (65, 115)
	iflimits = (3.8, 11.7)
	band2limits = (135, 164)  # IRAM DOC says 168 but this is above REF 16.4
	band3limits = (206, 268)

	def __init__(self, server='dbr', port=1080):
		self._s = str(server)
		self._p = str(port)
		self._initialized = False

	def init(self):
		assert not self._initialized, "Can only call when uninitialized"
		self._server = ServerProxy('http://' + self._s + ":" + self._p)
		self._initialized = True

	def LOband(self, band=2):
		if band == 2:
			return self.LO <= self.band2limits[1] and \
				self.LO >= self.band2limits[0]
		elif band == 3:
			return self.LO <= self.band3limits[1] and \
					self.LO >= self.band3limits[0]
		else:
			return None

	def goodREF(self):
		return self.reflimits[0] <= self.REF and \
			self.reflimits[1] >= self.REF

	def goodIF(self):
		return self.iflimits[0] <= self.IF and \
			self.iflimits[1] >= self.IF

	def goodGUNN(self):
		return self.gunnlimits[0] <= self.GUNN and \
			self.gunnlimits[1] >= self.GUNN

	def set_frequency(self, lo, if_offset=6):
		assert self._initialized, "Can only set frequency when initialized"
		self.IF = float(if_offset)
		self.LO = float(lo) - self.IF
		if self.LOband(3):
			if self.get_value('B3.flo.req') != self.LO:
				self.tune_lo(3, self.LO)
				self.tune_mixer(3, self.LO)
		elif self.LOband(2):
			if self.get_value('B2.flo.req') != self.LO:
				self.tune_lo(2, self.LO)
				self.tune_mixer(2, self.LO)
		else:
			return 1
		return 0

	def device_list(self):
		assert self._initialized, "Can only call when initialized"
		return self._server.deviceList()

	def device_property(self, device):
		assert self._initialized, "Can only call when initialized"
		return self._server.deviceProperties(str(device))

	def get_status(self):
		assert self._initialized, "Can only call when initialized"
		try: return self._server.getStatus()
		except : 
			dummy_dbr=dummy_frontend.dummy_dbr()
			status=dummy_dbr.getStatus()
			return(status)

	def get_value(self, variable):
		assert self._initialized, "Can only call when initialized"
		return self._server.getValue(str(variable))

	def tune_lo(self, band, value, deltaf=0):
		assert self._initialized, "Can only call when initialized"
		return self._server.tuneLo(int(band), float(value), int(deltaf))

	def tune_mixer(self, band, value):
		assert self._initialized, "Can only call when initialized"
		return self._server.tuneMixer(int(band), float(value))

	def get_reference_frequency(self, lo, if_offset=6):
		self.IF = float(if_offset)
		self.LO = float(lo) - self.IF

		if self.LOband(3):
			self.GUNN = self.LO / 3.0
			if self.LO < self.band3switch:
				self.REF = (self.GUNN - 0.1) / 5.0
			else:
				self.REF = (self.GUNN - 0.1) / 6.0
		elif self.LOband(2):
			self.GUNN = self.LO / 2.0
			self.REF = (self.GUNN - 0.1) / 5.0
		else:
			return -1.0

		if not (self.goodREF() and self.goodGUNN()):
			return -1.0

		return self.REF

	def get_gunn_frequency(self, ref, band=2, divisor=5.0):
		assert band in (2, 3), "Must have band nummer 2 or 3"
		assert (band == 3 and divisor in (6.0, 5.0)) or \
			(band == 2 and divisor == 5.0), \
			"Must have divisor 5 or 6 for band 3.  Only divisor 5 for band 2."
		assert (ref >= self.reflimits[0] and ref <= self.reflimits[1]), \
			"Not within limits of reference frequency values"

		self.REF = ref
		self.GUNN = self.REF * divisor + 0.1
		if self.goodGUNN() and self.goodREF():
			return self.GUNN
		else:
			return -1.0

	def close(self):
		assert self._initialized, "Can only call when initialized"
		del self._server
		self._initialized = False
