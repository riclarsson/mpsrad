# -*- coding: utf-8 -*-
"""
Created: 09.07.2018

Last modification: 23.05.2018

Author: Borys Dabrowski

Interactions with CTS functionality
"""

import datetime,socket,re,time
import numpy as np

class rcts104:
	""" Interactions with CTS functionality
	"""
	def __init__(self,
			name="rcts104",
			host="sofia4",
			tcp_port=1788,
			udp_port=None,
			channels=7504,
			integration_time=1000,
			blank_time=None,
			data_storage_containers=4):
		"""
		Parameters:
			name (any):
				Name of the mahcine (unused, kept as housekeeping)
			host (str):
				Name of the host, IP or DNS
			tcp_port (str):
				First port to communicate with the FW spectrometer
			udp_port (str):
				Second port to communicate with the FW spectrometer
			channels (array of int):
				Numbers of channel to **info**
			integration_time (int):
				**info**
			blank_time (int):
				**info**
			data_storage_containers (int):
				**info**
		"""
		self.name=name

		# Lock-check
		self._initialized=False
		self._sent=False

		# Set the runtime
		self._runtime=integration_time*1e-3

		# Constants
		self._channels=channels
		self._copies_of_vectors=int(data_storage_containers)

		# Host information
		self._tcp_port=tcp_port
		self._host=host


	def _pc104connect(self):
		"""Initialize the machine by locking onto it

		Musn't be initialized already.
		"""
		assert not self._initialized, "Cannot init an initialized CTS"

		# Socket
		self._socket=socket.socket(socket.AF_INET,socket.SOCK_STREAM)

		# Connect to the machine
		self._socket.connect((self._host,self._tcp_port))
		greetings=self._socket.recv(1024)
		assert len(greetings)>0,\
			"Failed to connect to "+self._host+":"+str(self._tcp_port)

		parse=re.search(b"connected to (.+?) on (.+$)",greetings)
		assert len(parse.groups())==2, "Failed to read the greetings"

		self._hostname,self._stream=parse.group(1),parse.group(2)

		# Initiate things on the machine
		self._send_cmd(b"cts config datafile "+self._stream)
		self._send_cmd(b"cts init time 1.0")
		self._send_cmd(b"cts init time %.4f"%self._runtime)


		# Initiate data
		self._data=[]
		for i in range(self._copies_of_vectors):
			self._data.append(np.zeros((self._channels,), dtype=np.float64))

		# We are now initialized
		self._initialized=True

	init=_pc104connect

	def _pc104disconnect(self):
		"""Remove the lock of the machine
		"""
		assert self._initialized, "Cannot close an uninitialized CTS"
		self._socket.close()
		del self._data
		self._initialized=False
	close=_pc104disconnect


	def send_cmd(self,command):
		"""Must be initialized already.
		"""
		assert self._initialized, "Must first initialize the CTS"
		return self._send_cmd(command)

	def _send_cmd(self,command):
#		print(command)
		self._socket.setblocking(1)	# make socket blocking
		self._socket.sendall(command+b"\n")
		reply=self._socket.recv(1024)
#		print(reply)
		return reply

	def run(self):
		"""Runs the CTS

		Must be initialized already

		Use the index to access different data (e.g., cold/hot/ant/ref/calib)
		"""
		assert self._initialized, "Must first initialize the CTS"
		assert not self._sent, "Cannot resend running without downloading"

		self._socket.setblocking(0)	# make socket non blocking
		self._socket.sendall(b"cts run\n")
		self._sent=True

	def get_data(self, i=0):
		"""Runs the CTS

		Must be initialized already
		
		Use the index to access different data (e.g., cold/hot/ant/ref/calib)
		"""
		assert self._initialized, "Must first initialize the CTS"
		assert i < self._copies_of_vectors and i > -1, "Bad index"
		assert self._sent, "Cannot download without first running the machine"


		begin=time.time()

		reply=b""
		while reply.find(b"delay ")==-1 and time.time()-begin<self._runtime*2:
			time.sleep(0.1)
			try: reply+=self._socket.recv(65536)
			except: pass

		assert len(reply)>0, "Failed to attain data from the machine"

		self._reply=reply	# test line

		x=map(int,reply.split(b'{')[1].split(b'}')[0].split(b' '))
		cycles=float(reply.split(b'cycles ')[1].split(b' ')[0])
		self._data[int(i)]=np.array([n/cycles for n in x])

		self._sent=False


	def save_data(self, basename="/home/dabrowski/data/test/CTS", file=None,
			binary=True):
		"""Saves data to file at basename+file.

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
