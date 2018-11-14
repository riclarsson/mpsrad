# -*- coding: utf-8 -*-
"""
SWI CTS control

Last modification: 02.10.2018
Author: Borys Dabrowski, dabrowski@mps.mpg.de
"""

import datetime,socket,time
import numpy as np

class swicts:
	""" Interactions with CTS functionality

	Functions:
		init:
			Initialize the machine by locking onto it
		close:
			Remove the lock of the machine
		run:
			Runs the machine and fills requested channel
		save_data:
			Saves data to file
	"""
	def __init__(self,
			name="SWI_CTS",
			frequency=[[5500,6500]],
			f0=6000,
			host="134.76.235.26",
			tcp_port=9900,
			udp_port=None,
			channels=[10000],
			integration_time=1000,
			blank_time=None,
			data_storage_containers=4):

		self.name=name
		self.frequency=frequency
		self.f0=f0

		# Lock-check
		self._initialized=False
		self._sent=False

		# Set the runtime
		self._runtime=integration_time

		# Constants
		self._channels=channels[0]
		self._copies_of_vectors=int(data_storage_containers)

		# Host information
		self._tcp_port=tcp_port
		self._host=host


	def _swictsconnect(self):
		assert not self._initialized, "Cannot init an initialized CTS"

		# Socket
		self._socket=socket.socket(socket.AF_INET,socket.SOCK_STREAM)

		# Connect to the machine
		self._socket.connect((self._host,self._tcp_port))
		greetings=self._socket.recv(1024)
		assert len(greetings)>0,\
			"Failed to connect to "+self._host+":"+str(self._tcp_port)

		# Initiate things on the machine
		self._send_cmd(b"init")
		self._send_cmd(b"time %d"%self._runtime)

		# Initiate data
		self._data=[]
		for i in range(self._copies_of_vectors):
			self._data.append(np.zeros((self._channels,), dtype=np.float64))

		# We are now initialized
		self._initialized=True
	init=_swictsconnect

	def _swictsdisconnect(self):
		assert self._initialized, "Cannot close an uninitialized CTS"
		self._socket.close()
		del self._data
		self._initialized=False
	close=_swictsdisconnect


	def send_cmd(self,command):
		assert self._initialized, "Must first initialize the CTS"
		return self._send_cmd(command)

	def _send_cmd(self,command):
		self._socket.setblocking(1)	# make socket blocking
		self._socket.sendall(command+b"\n")
		reply=self._socket.recv(1024)
#		print(reply)
		return reply

	def run(self):
		"""Runs the CTS
		Use the index to access different data (e.g., cold/hot/ant/ref/calib)
		"""
		assert self._initialized, "Must first initialize the CTS"
		assert not self._sent, "Cannot resend running without downloading"

		self._socket.setblocking(0)	# make socket non blocking
		self._socket.sendall(b"run\n")
		self._sent=True

	def get_data(self, i=0):
		"""Runs the CTS
		Use the index to access different data (e.g., cold/hot/ant/ref/calib)
		"""
		assert self._initialized, "Must first initialize the CTS"
		assert i < self._copies_of_vectors and i > -1, "Bad index"
		assert self._sent, "Cannot download without first running the machine"

		begin=time.time()

		reply=b''
		while reply.find(b"# end data\n")==-1 and time.time()-begin<self._runtime*2:
			time.sleep(0.1)
			try: reply+=self._socket.recv(65536)
			except: pass

		assert len(reply)>0, "Failed to attain data from the machine"

		self._reply=reply	# test line

		data=reply[reply.find(b'\n',1)+1:reply.find(b'# end data\n')]
		self._data[int(i)]=np.ndarray(shape=(-1,),dtype='>d',buffer=data)
		self._data[int(i)] = self._data[int(i)]

		self._sent=False

	def save_data(self, basename="/home/dabrowski/data/test/SWICTS", file=None,
			binary=True):
		"""Saves data to file at basename+file
		If file is None, the current time is used to create the filename
		Saves with numpy binary format if binary is true or as ascii otherwise
		"""
		assert self._initialized, "No data exists for an uninitialized CTS"

		now=datetime.datetime.now()
		if file is None:
			filename=self._hostname + now.strftime("-%Y%m%d%H%M%S-%f")
		else:
			filename=str(file)

		if binary: np.save(basename+filename, self._data)
		else: np.savetxt(basename+filename, self._data)

		return filename
