# -*- coding: utf-8 -*-

"""
Author: Borys Dabrowski

Last modification: 29.06.2018
"""
# =============================================================================
from threading import Thread
from time import localtime,sleep,time

class measure(Thread):
	"""Measurements as separate thread

	.. note:: For more information about the Thread’s methods and attributes used here, please refer to the `threading.Thread class documentation <https://docs.python.org/3/library/threading.html>`_
	"""
	def __init__(self,parent):
		Thread.__init__(self)
		self.parent=parent
		self.close_flag=False
		self.cmd=None
		self.measurements=None
		self.now=time()
		self.start()

	def close(self):
		"""Close the flag"""
		self.close_flag=True

	def do(self,cmd):
		"""Execute the command

		Parameters 
			cmd (str):
				Command to be runned
		"""
		self.cmd=cmd

	def busy(self):
		"""Check if a command is aleady active

		Return:
			Boolean whether or not a command is active
		"""
		return self.cmd is not None

	def run(self):
		"""Run the measure according to the command.

		The command could be : init / run / stop / close / test / periodic
		"""
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

class measure2(Thread):
	"""Measurements as separate thread

	.. note:: For more information about the Thread’s methods and attributes used here, please refer to the `threading.Thread class documentation <https://docs.python.org/3/library/threading.html>`_
	"""
	def __init__(self,parent):
		Thread.__init__(self)
		self.parent=parent
		self.close_flag=False
		self.cmd=None
		self.measurements=None
		self.now=time()
		self.start()

	def close(self):
		"""Close the flag"""
		self.close_flag=True

	def do(self,cmd):
		"""Execute the command

		Parameters 
			cmd (str):
				Command to be runned
		"""
		self.cmd=cmd

	def busy(self):
		"""Check if a command is aleady active

		Return:
			Boolean whether or not a command is active
		"""
		return self.cmd is not None

	def run(self):
		"""Run the measure according to the command.

		The command could be : init / run / stop / close / test / periodic
		"""
		while not self.close_flag:
			sleep(.01)
			# init measurements
			if self.cmd is 'init':
				if self.measurements is None:
					self.parent.setMeasurement()
					self.measurements=self.parent.measurements
				self.measurements.init()
				print('Ready to OEM')
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
