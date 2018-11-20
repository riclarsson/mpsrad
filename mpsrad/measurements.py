#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Dec  4 20:07:33 2017

Author: Richard Larsson

Run the measurements once all devices are initialized
"""

from mpsrad.wobbler import IRAM, WVR
from mpsrad.chopper import chopper
from mpsrad.backend import rcts104
#from mpsrad.backend import pc104
#from mpsrad.backend import acs
from mpsrad.backend import FW
from mpsrad.backend import swicts
from mpsrad.wiltron68169B import wiltron68169B
from mpsrad.housekeeping.Agilent import Agilent34970A
from mpsrad.housekeeping.sensors import sensors
from mpsrad.frontend.dbr import dbr
from . import files
from . import dummy_hardware
#from . import settings
#from mpsrad.helper import APCUPS

import time
import datetime
import numpy as np


class measurements:
	"""Run the measurements once all devices are initialized"""
	def __init__(self, sweep=False, freq=214, freq_step=0.2, if_offset=6,
		sweep_step=10, full_file=10*56*5*4, repeat=True, wait=1,
		freq_range=(214, 270),
		chopper_device="/dev/ttyUSB1", wobbler_address=b'0',
		wiltron68169B_address=5,
		wobbler_device="/dev/ttyUSB0", antenna_offset=1000,
		dbr_port=1080, dbr_server="dbr",
		integration_time=5000,
		blank_time=5,
		measurement_type="WVR",
		mode="antenna", basename='../data/',
		raw_formats=[files.dform, files.dform],
		formatnames=['d', 'd'],
		spectrometer_channels=[[4096], [4096]],
		spectrometers=[rcts104, rcts104],
		spectrometer_freqs=[[[1330, 1370]], [[1330, 1370]]],
		spectrometer_hosts=["waspam6", "waspam4"],
		spectrometer_names=["40 MHz CTS V", "40 MHz CTS H",],
		spectrometer_tcp_ports=[1788, 1788],
		spectrometer_udp_ports=[None, None]):

		""" Initialize the machine

		Parameters:
			sweep (boolean):
				**INFO**
			freq (int):
				Set the frequency of the device
			freq_step (float):
				Set the frequency step 
			if_offset (int):
				**INFO**
			full_file (int):
				Must be a multiple of 4
			repeat (boolean):
				**INFO**
			wait (int):
				**INFO**
			freq_range (tuple):
				Range of frequencies available
			wobbler_device (str):
				wobbler device's path
			wobbler_address (str):
				wobbler's address
			wiltron68169B_address (int):
				wiltron68169B's address
			chopper_device (str):
				chopper device's path
			antenna_offset (int):
				**INFO**
			dbr_port (int):
				Port to connect with the dbr
			dbr_server (str):
				Name of the dbr's server
			integration_time (int):
				**INFO**
			blank_time (int):
				**INFO**
			mode (str):
				**INFO**
			basename (str):
				**INFO**
			raw_formats (list):
				list of format for the files
			formatnames (list):
				list of format name for files
			spectrometer_channels (list):
				list of channels for the spectrometer
			spectrometers (list):
				list of spectrometer
			spectrometer_hosts (list):
				list of host names
			spectrometer_tcp_ports (list):
				list of tcp port
			spectrometer_udp_ports (list):
				list of udp ports
		"""
		assert not (full_file % 4), "Must have full series in file"
		assert wait >= 0.0, "Cannot have negative waiting time"

		self.measurement_type=measurement_type

		# Sets the wobbler interactions
		if self.measurement_type=='WVR':
			self.wob=WVR.wobbler(device=wobbler_device,address=wobbler_address)
		else:
			self.wob=IRAM.wobbler(device=wobbler_device,address=wobbler_address)
		# Sets the chopper interactions
		self.chop=chopper.chopper(device=chopper_device,offset=antenna_offset)
		if mode == 'antenna':
			self.order=[self.chop.set_cold, self.chop.set_ant,
				self.chop.set_hot, self.chop.set_ant]
		elif mode == 'reference':
			self.order=[self.chop.set_cold, self.chop.set_ref,
				self.chop.set_hot, self.chop.set_ref]
		elif mode == 'mixed':
			self.order=[self.chop.set_cold, self.chop.set_ant,
				self.chop.set_ref, self.chop.set_hot]
		else:
			raise RuntimeError(("'antenna', 'reference', and 'mixed' are the "
				"optional modes.  Not "+str(mode)+", "
				"which is what you choose"))

		# Sets the spectrometer interactions
		self.spec=[]
		for i in range(len(spectrometer_channels)):
			self.spec.append(spectrometers[i](
				integration_time=integration_time,
				data_storage_containers=4,
				channels=spectrometer_channels[i],
				host=spectrometer_hosts[i],
				tcp_port=spectrometer_tcp_ports[i],
				udp_port=spectrometer_udp_ports[i],
				blank_time=blank_time,
				frequency=spectrometer_freqs[i],
				name=spectrometer_names[i]))
		self._spectrometers_count=len(self.spec)
		assert self._spectrometers_count, "Must have at least one spectrometer"

		if self.measurement_type=='IRAM':
			# Sets the LO interactions
			self.lo=wiltron68169B(address=wiltron68169B_address)
			self.dbr=dbr(port=dbr_port, server=dbr_server)
		else:
			self.multimeter=Agilent34970A()

		# Sets the file interactions
		self.raw=[]
		for i in range(self._spectrometers_count):
			self.raw.append(files.raw(format=raw_formats[i]))

#		self.temperature=pt100()
		if self.measurement_type=='IRAM':
			self.temperature=sensors()

		# Constants
		self._sweep=sweep
		self._freq=freq
		self._freq_step=freq_step
		self._full_file=full_file
		self._sweep_step=sweep_step
		self._repeat=repeat
		self._wait=wait
		self._freq_range=freq_range
		self._basename=basename
		self._formatnames=formatnames
		self._if=float(if_offset)
		self._integration_time=float(integration_time)

		# Counter
		self._i=0
		
#		self._ups = APCUPS()

		self._initialized=False
		
		self.housekeeping = {"Instrument": {},
				"Environment": {"Room [K]": 3000.,
						"Cold Load [K]": 0.12,
						"Hot Load [K]": 500.,
						"Outdoors [K]": 2345.,
						"Humidity [%]": 1234.0}}

	def init(self, wobbler_position=4000):
		"""Tries to initiate all devices.  Close all if any error

		Parameters:
			wobbler_position (int):
				Initial version of the wobbler
		"""
		assert not self._initialized, "Cannot reinitialize measurement series"
		try:

			if self.measurement_type=='IRAM':
				print("Init LO")
				try: self.lo.init()  # Does nothing but confirms connection
				except: pass

				print("Init DBR")
				try: self.dbr.init()  # Does nothing but confirms connection
				except:
					self._dum_dbr=dummy_hardware.dummy_hardware('DBR')
					self._dum_dbr.init()

				print("Init thermometer")
				try: self.temperature.init()  # Does nothing but confirms connection
				except:
					self._dum_HK=dummy_hardware.dummy_hardware('HOUSEKEEPING')
					self._dum_HK.init()
			else:
				print("Init multimeter")
				self.multimeter.init()  # Does nothing but confirms connection

			print("Init wobbler")
			self.wob.init(wobbler_position)  # Must set start position

			print("Init chopper")
			try: self.chop.init()  # Can set nothing
			except: 
				self._dum_chop=dummy_hardware.dummy_hardware('CHOPPER')
				self._dum_chop.init()
			try:
				for s in self.spec:
					print("Init spectrometer:", s.name)
					s.init()  # Can set nothing
			except:
				self._dum_spec=dummy_hardware.dummy_hardware('SPECTROMETER')
				self._dum_spec.init()
				
#			self._ups.init()

			print("All machines are initialized!")
			self._initialized=True
		except KeyboardInterrupt:
			self.close()
			print("Exiting")
			exit(0)
		except:
			self.close()
			raise RuntimeError("Unexpected runtime error in init of machines")

		try:
			print("Setting wobbler motion pattern...")
			try:
				self._wobbler_position=\
				self.wob.get_recommended_movements(int(self._integration_time)
												/ 1000.0)
				print("Wobbler motion pattern is: "+str(self._wobbler_position))
			except:
				print("ERROR IN SETTING THE MOTION PATTERN")
				time.sleep(0.5)
				print("NOT CONNECTED TO WOBBLER")
			
			if self.measurement_type=='IRAM':
				print("Set frequency")
				self.set_frequency(self._freq)

			print("Set filename")
			self.set_filenames()
		except KeyboardInterrupt:
			self.close()
			print("Exiting")
			exit(0)
		except:
			self.close()
			raise RuntimeError("Unexpected runtime error in of files or freq")

	def run(self):
		"""Run the measurements and append data.  If any failure, close all

		Sets housekeeping to 16 numbers as:
		   - 0 : Cold-load temperature
		   - 1 : 0,  # SHOULD BE SET TO HOT-LOAD TEMPERATURE
		   - 2 : 0,  # COULD BE SET TO 2M AIR TEMPERATURE
		   - 3 : 0,  # COULD BE SET TO 2M AIR RH
		   - 4 : 0,  # COULD BE SET TO GROUND MAGNETOMETER
		   - 5 : Integration time in miliseconds
		   - 6 : B2 temperature
		   - 7 : B3 temperature
		   - 8 : 77K-plate temperature
		   - 9 : 15K-plate temperature
		   - 10 : 4K-plate temperature
		   - 11 : B2 requested LO
		   - 12 : B3 requested LO
		   - 13 : Reference LO
		   - 14 : Requested frequency
		   - 15 : Requested intermediate frequency
		"""
		assert self._initialized, "Cannot run uninitialized measurement series"
		try:
			self._times=[]
			self._housekeeping=[]
			for i in range(4):
				try:
					# print("setting pointing")
					self.order[i]()
				except:
					function=self.order[i].__name__
					self._dum_chop.run_issue(3,function)
			
				# print("adding time")
				self._times.append(int(time.time()))
				
#				ups_active, ups_power = self._ups.run()
#				UPS_ERROR = 50
#				if ups_active == 1:
#					pass  # UPS is active and all is fine
#				elif ups_active == 0:
#					if ups_power < UPS_ERROR:  # Shutdown at 50% power
#						self.close()
#						time.sleep(3)
#						self._ups.close()
#					else:
#						print('UPS is on Battery.', ups_power,
#						      '% power remaining.  Will shutdown when',
#						      'less than', UPS_ERROR, '% remains')
#						pass  # UPS is inactive but power is still high
#				else:
#					pass  # The trick is, that there is no UPS

				# This is where housekeeping data should go...
#				print("generating housekeeping")

				if self.measurement_type=='IRAM':
					try:
						debug_msg='housekeeping'
						self._housekeeping.append(np.zeros((16)))

						debug_msg='HK_cryo'
						self._housekeeping[-1][0]=float(self.dbr.get_value('cryo.ColdLd.val'))

						debug_msg='HK_temps'
						sensors=self.temperature.get_values()
						self._housekeeping[-1][1]=self.temperature.C2K(sensors['Temp0'])
						self._housekeeping[-1][2]=self.temperature.C2K(sensors['Temp1'])
						self._housekeeping[-1][3]=sensors['Humidity']

						debug_msg='HK_chopper_pos'
	#					self._housekeeping[-1][4]=ord(self.get_order()[i])
						self._housekeeping[-1][4]=self.chop.get_pos()[0]

						debug_msg='HK_dbr'
						self._housekeeping[-1][6]=float(self.dbr.get_value('cryo.Band2.val'))
						self._housekeeping[-1][7]=float(self.dbr.get_value('cryo.Band3.val'))
						self._housekeeping[-1][8]=float(self.dbr.get_value('cryo.T_77K.val'))
						self._housekeeping[-1][9]=float(self.dbr.get_value('cryo.T_15K.val'))
						self._housekeeping[-1][10]=float(self.dbr.get_value('cryo.T_04K.val'))
						self._housekeeping[-1][11]=float(self.dbr.get_value('B2.flo.req'))
						self._housekeeping[-1][12]=float(self.dbr.get_value('B3.flo.req'))
						self._housekeeping[-1][13]=float(self._ref)
						self._housekeeping[-1][14]=float(self._freq)
						self._housekeeping[-1][15]=float(self._if)
					except:
						self._dum_HK.run_issue(3)
				else:
					debug_msg='HK_Agilent'
					self._housekeeping.append(np.zeros((16)))
					self._housekeeping[-1][1:]=self.multimeter.getSensors()


				try:
					debug_msg='wobbler_move'
#					print("moving wobbler")
					time.sleep(0.5)
					self.wob.move(self._wobbler_position[i])
				except:
					self._dum_wob.run_issue(3,'MOVE')
				
				debug_msg='spec_run'
#				print("telling to gather data")

				for s in self.spec: s.run()
				
				debug_msg='get_data'
				for s in self.spec:
#					print(s.name)
					s.get_data(i)

				try:
					debug_msg='wobbler_wait'
					self.wob.wait()
				except: 
					self._dum_wob.run_issue(3,'WAIT')
		except KeyboardInterrupt:
			self.close()
			print("Exiting")
#			exit(0)
		except:
			self.close()
			print(debug_msg)
			raise RuntimeError("Unexpected runtime error in run")

	def get_order(self):
		"""
		Return:
			**INFO**
		"""
		return [l.__name__.replace('set_','')[0].upper() for l in self.order]


	def save(self):
		"""Save the CAHA series to the provided files
		
		Measurements must be initialized already.
		"""
		assert self._initialized, ("Cannot save uninitialized measurement "
								"series")
		try:
			for i in range(4):
				# Need to take into account multiple spectrometers sometime...
				print('saving spectra '+str(self._i*4+i))
				for j in range(self._spectrometers_count):
					if self._formatnames[j]=='s':
						self.raw[j].append_to_swictsfile(self._files[j], self._times[i],
							self._housekeeping[i],self.spec[j]._data[i])
					elif 'test' in self._formatnames[j]:
						self.raw[j].append_to_testfile(self._files[j], self._times[i],
							self._housekeeping[i],self.spec[j]._data[i][2:-2], self.spec[j]._testarray[i])
					else:
						self.raw[j].append_to_file(self._files[j], self._times[i],
							self._housekeeping[i],self.spec[j]._data[i][2:-2])
					
		except KeyboardInterrupt:
			self.close()
			print("Exiting")
			exit(0)
		except:
			self.close()
			raise RuntimeError("Unexpected runtime error in save")

	def update(self):
		"""Keep track of counts to either change frequency or filename
		
		Measurements must be initialized already.
		"""
		assert self._initialized, ("Cannot update uninitialized measurement "
			"series")
		try:
			self._i+=1
			if self._sweep and not self._i % self._sweep_step:
				self.update_freq()
			if not self._i*4 % self._full_file:
				self.set_filenames()
		except KeyboardInterrupt:
			self.close()
			print("Exiting")
			exit(0)
		except:
			self.close()
			raise RuntimeError("Unexpected runtime error in update")

	def update_freq(self):
		"""Update the frequency to the next choosen level.
		
		Measurements must be initialized already.
		"""
		assert self._initialized, ("Cannot update frequency of uninitialized "
			"measurement series")
		try:
			self._freq+=self._freq_step
			if self._freq > self._freq_range[1]:  # Upwards stepping
				self._freq=self._freq_range[0]
			elif self._freq < self._freq_range[0]:  # Downwards stepping
				self._freq=self._freq_range[1]

			self.set_frequency(self._freq)
			time.sleep(self._wait)
		except KeyboardInterrupt:
			self.close()
			print("Exiting")
			exit(0)
		except:
			self.close()
			raise RuntimeError("Unexpected runtime error in update")

	def set_filenames(self):
		"""Set the names of the files to write to
		
		Measurements must be initialized already.
		"""
		assert self._initialized, ("Cannot set filename of uninitialized "
			"measurement series")
		try:
			self._files=[]
			t=datetime.datetime.now().isoformat().split('.')[0]
			for i in range(self._spectrometers_count):
				self._files.append(self._basename+self._formatnames[i] +
					t+'.'+str(i)+'.raw')
			for f in self._files:
				print("Printing to "+f)
		except KeyboardInterrupt:
			self.close()
			print("Exiting")
			exit(0)
		except:
			self.close()
			raise RuntimeError("Unexpected runtime error in set_filename")

	def set_frequency(self, freq):
		"""Set the frequency of the measurement.  Keeps track of IF

		Parameters: 
			freq (float):
				Frequency of the measurement
		
		Measurements must be initialized already.
		"""
		assert self._initialized, ("Cannot set frequenct of uninitialized "
			"measurement series")
		try:
			self._freq=freq
			self._ref=self.dbr.get_reference_frequency(freq, self._if)
			if self._ref < 0:
				self.close()
				raise RuntimeError("Frequency out-of-bounds")
			else:
				print("Setting frequency to "+str(freq)+" GHz")
				self.dbr.set_frequency(freq, self._if)
				self.lo.set_frequency(self._ref)
		except KeyboardInterrupt:
			self.close()
			print("Exiting")
			exit(0)
		except:
			self.close()
			raise RuntimeError("Unexpected runtime error in set_frequency")

	def close(self):
		"""Tries to close all devices upon error with any of them...
		"""
		ndevices=5+len(self.spec)
		n=0
		try:
			self.wob.close()
			n+=1
			print('Closed wobbler connection')
		except:
			pass
		try:
			self.chop.close()
			n+=1
			print('Closed chopper connection')
		except:
			pass
		try:
			i=1
			for s in self.spec:
				s.close()
				print('Closed connection with spectrometer '+str(i))
				i+=1
				n+=1
		except:
			pass
		try:
			self.multimeter.close()
			n+=1
			print('Closed multimeter connection')
		except:
			pass
		try:
			if self.lo._initialized is False:
				ndevices -= 1
			self.lo.close()
			n+=1
			print('Closed LO connection')
		except:
			pass
		try:
			if self.dbr._initialized is False:
				ndevices -= 1
			self.dbr.close()
			n+=1
			print('Closed DBR connection')
		except:
			pass
		try:
			self.temperature.close()
			n+=1
			print('Closed temperature sensor connection')
		except:
			pass
		print('Closed '+str(n)+'/'+str(ndevices)+' devices')
