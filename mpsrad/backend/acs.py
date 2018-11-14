# -*- coding: utf-8 -*-
"""
ACS control

Last modification: 21.08.2018
Author: Borys Dabrowski, dabrowski@mps.mpg.de
"""
from . import cheetah_py as spi
import datetime
import numpy as np
from time import time,sleep
from .qc_kk import qc_kk

class acs:
	""" Interactions with ACS functionality

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
			name="acs",
			frequency=[[4400,8800]],
			f0=6000,
			host="",
			tcp_port=None,
			udp_port=None,
			channels=[1023],
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
		self._runtime=integration_time*1e-3

		# Constants
		self._channels=channels[0]
		self._copies_of_vectors=int(data_storage_containers)

		# Host information
		self._tcp_port=tcp_port
		self._host=host

		self.dB=0

	def init(self):
		assert not self._initialized, "Cannot init an initialized ACS"

		# Find CHEETAH SPI device
		(num,ports,unique_ids)=spi.ch_find_devices_ext(16,16)
		assert num==1, "%d SPI devices found!" % num
		spi_port=ports[0]

			# Determine if the device is in-use
		if (spi_port & spi.CH_PORT_NOT_FREE):
			inuse,spi_port="(in-use)",spi_port & ~spi.CH_PORT_NOT_FREE
		else: inuse="(avail)"
		assert inuse=="(avail)", "Cheetah device busy!"

		# Configure SPI
		spi_h=spi.ch_open(spi_port)
		assert spi_h>0, "Unable to open Cheetah device on port %d" % spi_port

		mode=0
		spi.ch_spi_configure(spi_h,(mode>>1),mode&1,spi.CH_SPI_BITORDER_MSB,0x0)

		# target power off
		spi.ch_target_power(spi_h,spi.CH_TARGET_POWER_OFF)

		bitrate=2000
		bitrate=spi.ch_spi_bitrate(spi_h,bitrate)
		assert bitrate>=0, "Could not set the bitrate"

		self._spi_h=spi_h

		self._commands={
			# General commands
			'STATUS':0x00,
			'FPGA_RESET':0x02,
			'READOUT_TEST_OFF':0x0E,
			'READOUT_TEST_ON':0x10,
			'RF_POWER_UP':0x68,
			'RF_POWER_DOWN':0x66,

			# General ACS commands
			'ACS_SCK_DIV_1':0x06,
			'ACS_SCK_DIV_2':0x08,
			'ACS_SCK_DIV_4':0x0A,
			'ACS_SCK_DIV_8':0x0C,
			'AMP_GAIN_AB':0x64,
			'TRIG_INT_AB':0x04,

			# ACS A commands
			'READOUT_A':0x14,
			'FORCE_READOUT_A':0x16,
			'TRIG_INT_A':0x18,
			'FIFO_COUNT_A':0x1A,
			'INT_T_A':0x1C,
			'INT_RESET_A':0x1E,
			'LAGS_000_A':0x20,
			'LAGS_128_A':0x22,
			'LAGS_256_A':0x24,
			'LAGS_384_A':0x26,
			'LAGS_512_A':0x28,

			# ACS B commands
			'READOUT_B':0x2A,
			'FORCE_READOUT_B':0x2C,
			'TRIG_INT_B':0x2E,
			'FIFO_COUNT_B':0x30,
			'INT_T_B':0x32,
			'INT_RESET_B':0x34,
			'LAGS_000_B':0x36,
			'LAGS_128_B':0x38,
			'LAGS_256_B':0x3A,
			'LAGS_384_B':0x3C,
			'LAGS_512_B':0x3E,

			# VTF A commands
			'VTF_TRIG_INT_A':0x40,
			'VTF_CANCEL_INT_A':0x42,
			'VTF_T_INT_A':0x44,
			'VTF_INT_COUNT_A':0x46,
			'VTF_INT_START_T_A':0x48,
			'VTF_INT_STOP_T_A':0x4A,

			# VTF B commands
			'VTF_TRIG_INT_B':0x52,
			'VTF_CANCEL_INT_B':0x54,
			'VTF_T_INT_B':0x56,
			'VTF_INT_COUNT_B':0x58,
			'VTF_INT_START_T_B':0x5A,
			'VTF_INT_STOP_T_B':0x5C
			}

		# Initiate data
		self._data=[]
		for i in range(self._copies_of_vectors):
			self._data.append(np.zeros((self._channels,), dtype=np.float64))

		# Initiate data
		self._testarray=[]
		for i in range(self._copies_of_vectors):
			self._testarray.append(np.zeros((self._channels*2,), dtype=int))

		# We are now initialized
		self._initialized=True

	def close(self):
		assert self._initialized, "Cannot close an uninitialized ACS"
		spi.ch_close(self._spi_h)
		del self._data
		self._initialized=False

	def cmd(self,command,data=[0x00,0x00,0x00]):
		assert self._initialized, "Must first initialize the ACS"
		return self._cmd(command,data)

	def _cmd(self,command,data=[0x00,0x00,0x00]):
		cmd=self._commands[command]
		spi.ch_spi_queue_clear(self._spi_h)			# clear the batch queue
		spi.ch_spi_queue_oe(self._spi_h,1)				# output enable(1)
		spi.ch_spi_queue_ss(self._spi_h,0b000)		# queue "slave select" assertion(1)/deassertion(0)
		cmd_out=spi.array('B',[cmd&0xFF]+[n&0xFF for n in data])
		spi.ch_spi_queue_array(self._spi_h,cmd_out)	# queue command
		spi.ch_spi_queue_ss(self._spi_h,0b111)

		# send the command, get the answer
		l=spi.ch_spi_batch_length(self._spi_h)
		data_in=spi.array('B',[0 for i in range(l)])
		(count,data_in)=spi.ch_spi_batch_shift(self._spi_h,l)

		# clear the state of the bus
		spi.ch_spi_queue_clear(self._spi_h)
		spi.ch_spi_queue_ss(self._spi_h,0b111)
		spi.ch_spi_queue_oe(self._spi_h,0)
		spi.ch_spi_batch_shift(self._spi_h,0)

		return data_in

	def run(self):
		"""Runs the ACS
		Use the index to access different data (e.g., cold/hot/ant/ref/calib)
		"""
		assert self._initialized, "Must first initialize the ACS"
		assert not self._sent, "Cannot resend running without downloading"

		self.cmd('READOUT_TEST_OFF')
		self.cmd('RF_POWER_UP')

#		dB=6
		a=(0x0f+int(self.dB/.5))&0b11111

		self.cmd('AMP_GAIN_AB',[0,a,a])
		self.cmd('INT_RESET_A')

		t_int=int(self._runtime*25e6/256)
		self.cmd('INT_T_A',[t_int>>16&0xFF,t_int>>8&0xFF,t_int&0xFF])
		self.cmd('LAGS_512_A')
		self.cmd('TRIG_INT_A')

		self._t0=time()

		self._sent=True

	def get_data(self, i=0):
		"""Runs the ACS
		Use the index to access different data (e.g., cold/hot/ant/ref/calib)
		"""
		assert self._initialized, "Must first initialize the ACS"
		assert i < self._copies_of_vectors and i > -1, "Bad index"
		assert self._sent, "Cannot download without first running the machine"

		while (time()-self._t0<(self._runtime+.2)): sleep(.1)

		m=np.ndarray(shape=1,dtype='>i4',buffer=self.cmd('FIFO_COUNT_A'))[0]&0xffffff
		out=self.cmd('READOUT_A',[0 for n in range((1*24+0*32+m*32)//8)])
		assert len(out)>4, "Failed to attain data from the machine"

		v=np.ndarray(shape=(-1,),dtype='>i4',buffer=out)
		self._testarray[i] = v
		
#		count=v[0]&0xffffff
		self._raw_reply=v+0

		v=v*1.
		CorrTime=v[1]
		Ihigh,Qhigh,Ilow,Qlow,Ierr,Qerr=v[3:9]/CorrTime
		II,QI,IQ,QQ=v[17::4]/CorrTime,v[18::4]/CorrTime,v[19::4]/CorrTime,v[20::4]/CorrTime

		yqq=qc_kk(II,QI,IQ,QQ,Ihigh,Qhigh,Ilow,Qlow,Ierr,Qerr)

#		erfcinv=lambda x: erfinv(1-x)
#		tval=lambda x: 2**.5*erfcinv(2*x)
#		rel_pwr=lambda Xhi,Xlo: 1.819745692478292/(tval(Xhi)+tval(Xlo))**2
#
#		relPwrQ=rel_pwr(Qhigh/CorrTime,Qlow/CorrTime)
#		relPwrI=rel_pwr(Ihigh/CorrTime,Ilow/CorrTime)
#		qc_power=(relPwrQ*relPwrI)**.5

		K=10.**(-self.dB/10.)
		
#		self._data[int(i)]=qc_power*np.absolute(np.fft.hfft(II+QQ+1j*(IQ-QI)))*K
		self._data[int(i)]=K*yqq
		self._sent=False

	def set_housekeeping(self, hk):
		""" Sets the housekeeping data dictionary.  hk must be dictionary """
		assert self._initialized, "Can set housekeeping when initialized"
		
		hk['Instrument'][self.name] = {}
		hk['Instrument'][self.name]['Frequency [MHz]'] = self.frequency
		hk['Instrument'][self.name]['Channels [#]'] = self._channels
		hk['Instrument'][self.name]['Integration [s]'] = self._runtime


	def save_data(self, basename="/home/dabrowski/data/test/ACS", file=None,
			binary=True):
		"""Saves data to file at basename+file
		If file is None, the current time is used to create the filename
		Saves with numpy binary format if binary is true or as ascii otherwise
		"""
		assert self._initialized, "No data exists for an uninitialized ACS"

		now=datetime.datetime.now()
		if file is None:
			filename=self._hostname + now.strftime("-%Y%m%d%H%M%S-%f")
		else:
			filename=str(file)

		if binary: np.save(basename+filename, self._data)
		else: np.savetxt(basename+filename, self._data)

		return filename
