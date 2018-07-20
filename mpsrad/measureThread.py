# -*- coding: utf-8 -*-
"""
Measurements as separate thread

Last modification: 29.06.2018

Author: Borys Dabrowski
"""
# =============================================================================
from threading import Thread
from time import localtime,sleep,time

class measure(Thread):
	def __init__(self,parent):
		Thread.__init__(self)
		self.parent=parent
		self.close_flag=False
		self.cmd=None
		self.measurements=None
		self.now=time()
		self.start()

	def close(self):
		self.close_flag=True

	def do(self,cmd):
		self.cmd=cmd

	def busy(self):
		return self.cmd is not None

	def run(self):
		while not self.close_flag:
			sleep(.01)
			# init measurements
			if self.cmd is 'init':
				if self.measurements is None:
					self.parent.setMeasurement()
					self.measurements=self.parent.measurements
				self.measurements.init()
				print('Ready to measure')
				self.cmd=None

			# run measurements (main loop)
			elif self.cmd is 'run':
					self.measurements.run()
					self.measurements.save()
					self.measurements.update()

			# stop measurements
			elif self.cmd is 'stop': self.cmd=None

			# stop measurements and close all devices
			elif self.cmd is 'close':
				if self.measurements._initialized: self.measurements.close()
				self.measurements=None
				self.parent.measurements=None
				self.cmd=None

			# tests (ssingle and repetitive)
			elif self.cmd is 'test':
				print(localtime())
				self.cmd=None
			elif self.cmd is 'periodic':
				if time()-self.now>1:
					self.now=time()
					print(localtime().tm_sec)
			else: pass

		if self.measurements is not None:
			if self.measurements._initialized: self.measurements.close()
# =============================================================================
