#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Code to read temperature

Last modification: 29.03.2018
Author: Borys Dabrowski, dabrowski@mps.mpg.de
"""

import socket,time

class pt100:
	""" Interactions with wiltron68169B functionality

	Loads the shared wiltron-library as ../lib/libwiltron68169B.so on import
	and handles translation of python input to ctypes and ctypes output to
	python-readable variables

	Functions:
		ask_name:
			Asks the name (to see it there is a response)

		set_frequency:
			Sets the frequency to provided GHz
	"""

	def __init__(self, address=22,host='192.168.5.10', tcp_port=1234,
			timeout=5, name="pt100-python"):
		self._initialized=False
		self._address=address

		# Host information
		self._tcp_port=tcp_port
		self._host=host
		self._timeout=timeout

	def ohm2celsius(self,R_PT100):
		"""Converts Pt100 Ohm to deg. Celsius"""
		R0=100.0
		c=[-1.138628e-03, 2.559038e+00, 9.988525e-04, -1.061679e-06, 2.585121e-08]

		temp=c[4]
		for n in [3, 2, 1, 0]: temp=temp*(R_PT100-R0)+c[n]
		return temp

	def init(self):
		assert not self._initialized, "Cannot init initialized machine"

		# Open socket
		s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
		s.connect((self._host,self._tcp_port))
		s.setblocking(0)	# make socket non blocking

		# Set address
		s.sendall(b'++addr '+str(self._address).encode('ascii')+'\r\n')

		# Send setup
		s.sendall(b'++clr\r\n')
		time.sleep(2)
		s.sendall(b'F3 R2 N5 Z1 T4 M35 \r\n')
		time.sleep(2)
		s.sendall(b'F3 R2 N5 Z1 T4 M35 \r\n')

		# Close socket
		s.close()

		self._initialized=True

	def _get_resistance(self):
		assert self._initialized, "Cannot run uninitialized machine"

		s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
		s.connect((self._host,self._tcp_port))
		s.setblocking(0)	# make socket non blocking

		# Set address
		s.sendall(b'++addr '+str(self._address).encode('ascii')+'\r\n')
		
		# Trigger measurement, ask for results
		s.sendall(b'T3\r\n')

		# Set instrument to talk
		s.sendall(b'++read eoi\r\n')

		# Get the answer
		t0,ready=time.time(),False
		while time.time()-t0<self._timeout and not ready:
			try:
				answ=s.recv(1024)
				time.sleep(.5)
				try: answ=answ+s.recv(1024)
				except: pass
				ready=True
			except: pass
			time.sleep(.1)

		# Close socket
		s.close()

		if ready: return float(answ.replace('\r\n',''))
		else: return -1

	def get_temperature(self, unit='K'):
		assert self._initialized, "Cannot run uninitialized machine"

		res=-1
		while res<0:
			res=self._get_resistance()
			if res<0: time.sleep(.5)

		# Convert resistance to temperature
		temp=self.ohm2celsius(res)
		if unit == 'K': return temp+273.15
		else: return temp

	def close(self):
		assert self._initialized, "Cannot close uninitialized machine"
		self._initialized=False
