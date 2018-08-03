"""
Author: Yann Goument

Last modification : 03.08.2018

Emulates the hardwares' function in case of malfunction
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

class dummy_hardware:
	"""Dummy class to emulate the functions of the machines"""
	def __init__(self,name):
		time.sleep(1)
		self._name=name

	def init (self):
		"""In case of error in initialization"""
		print("ERROR IN", self._name, "INITIALIZATION")
		time.sleep(0.5)
		print(" SWITCH ON DUMMY", self._name)
		time.sleep(1)

	def run_issue (self,time_wait=1,*args):
		"""In case of error when running the measurements"""
		time.sleep(time_wait)
		l=len(args)
		if l==0:
			print("FUNCTIONS NON-AVAILABLE ON DUMMY", self._name)
		else:
			for function in args:
				print("'",function,"' NON-AVAILABLE ON DUMMY", self._name)

	def save_issue (self):
		"""In case of error when saving data"""
		time.sleep(1)
		print("ERROR IN SAVING DATA, NON-AVAILABLE ON DUMMY",self._name)
