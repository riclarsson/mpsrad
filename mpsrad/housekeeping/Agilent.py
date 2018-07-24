# -*- coding: utf-8 -*-
"""
Reads sensors connected to Agilent 34970A multimeter

Last modification: 19.06.2018

Author: Borys Dabrowski
"""
import serial
from time import time,sleep,strftime
from threading import Thread
from scipy.interpolate import make_interp_spline
from mpsrad.helper import serialCheck

class Agilent34970A:
	"""Reads sensors connected to Agilent 34970A multimeter
	"""
	def __init__(self,device='/dev/ttyS0',baud=57600):
		"""
		Parameters:
			device (str):
				agilent device's path
			baud (int):
				transmission speed
		"""
		self._initialized=False
		self._device=device
		self._baud=baud
		self._values=[0]*20
		self._now=None
		OFF,CY7,PT100,PT1000,PKR251P,PKR251I=None,self.CY7_Temperature,\
			self.PT100_Temperature,self.PT1000_Temperature,\
			self.PKR251_Pressure,self.PKR251_Identification
		self._channels=[
			CY7,		# Channel 101: DC voltage measurement		T1 Cold Load Temperature
			CY7,		# Channel 102: DC voltage measurement		T1 Hot Load Temperature
			CY7,		# Channel 103: DC voltage measurement		T1 HEMT Temperature
			PT100,	# Channel 104: 2W resistance measurement		T2 CTS1 Filter Temp. Branch A
			PT100,	# Channel 105: 2W resistance measurement		T3 CTS2 Filter Temp. Branch A
			PT100,	# Channel 106: 2W resistance measurement		T6 CTS3 Filter Temp. Branch A
			PT100,	# Channel 107: 2W resistance measurement		T7 CTS4 Filter Temp. Branch A
			PKR251P,	# Channel 108 DC voltage measurement		P1 Pressure 1 Dewar
			PKR251P,	# Channel 109: DC voltage measurement		P2 Pressure 2 Pump
			OFF,		# Channel 110: no measurement
			OFF,		# Channel 111: DC voltage measurement		T5 Spare Voltage 1
			OFF,		# Channel 112: DC voltage measurement		T5 Spare Voltage 2
			OFF,		# Channel 113: DC voltage measurement		T5 Spare Voltage 3
			PT100,	# Channel 114: 2W resistance measurement		T2 CTS1 Filter Temp. Branch B
			PT1000,	# Channel 115: 2W resistance measurement		T3 CTS2 Filter Temp. Branch B
			PT100,	# Channel 116: 2W resistance measurement		T6 CTS3 Filter Temp. Branch B
			PT100,	# Channel 117: 2W resistance measurement		T7 CTS4 Filter Temp. Branch B
			PKR251I,	# Channel 118: DC voltage measurement		P1 Pressure 1 Identification
			PKR251I,	# Channel 119: DC voltage measurement		P2 Pressure 2 Identification
			OFF		# Channel 120: no measurement
			]

	def init(self):
		"""Set the connection with the device

		Musn't be initialized already.
		"""
		assert not self._initialized, "Cannot init initialized multimeter"
		checkserial=serialCheck.serialcheck()	#make sure to use pyserial

		# Open a serial port
		self._serial=serial.Serial(self._device,self._baud,xonxoff=True,timeout=2)
		self.configMultimeter()
		self._measureThread=measureThread(self)
		self._initialized=True

	def close(self):
		"""Close the connection with the device

		Must be initialized already
		"""
		assert self._initialized, "Cannot close uninitialized multimeter"
		self._measureThread.close()
		while self._measureThread.running: pass
		self._serial.close()
		self._initialized=False

	def read(self):
		"""read **info**
		"""
		return self._serial.readline().replace(b'\r\n',b'')

	def write(self,cmd):
		"""write **info**
		"""
		if isinstance(cmd,str): cmd=cmd.encode()
		self._serial.flushInput()
		self._serial.write(cmd+b'\n')

	def ask(self,cmd,timeout=2):
		"""
		Parameters:
			cmd (str):
				command to send
			timeout (int):
				**info**
		"""
		while self._serial.in_waiting==0:
			self.write(cmd)
			t0=time()
			while self._serial.in_waiting==0 and time()-t0<timeout: sleep(.1)

		return self.read()

	def configMultimeter(self):
		"""**info**"""
		self.write("\x03")		# reset instrument (Device Clear)
		assert b'34970A' in self.ask("*IDN?"), "Multimeter is not answering"

		self.write("SYSTEM:CPON 100")
		self.write("ROUTE:CHAN:DELAY:AUTO ON, (@101:120)")
		self.write("CALC:SCALE:STATE OFF, (@101:120)")

		self.write("SENSE:FUNCTION \"VOLTAGE:DC\", (@101)")
		self.write("SENSE:FUNCTION \"VOLTAGE:DC\", (@102)")
		self.write("SENSE:FUNCTION \"VOLTAGE:DC\", (@103)")
		self.write("SENSE:FUNCTION \"RESISTANCE\", (@104)")
		self.write("SENSE:FUNCTION \"RESISTANCE\", (@105)")
		self.write("SENSE:FUNCTION \"RESISTANCE\", (@106)")
		self.write("SENSE:FUNCTION \"RESISTANCE\", (@107)")
		self.write("SENSE:FUNCTION \"VOLTAGE:DC\", (@108)")
		self.write("SENSE:FUNCTION \"VOLTAGE:DC\", (@109)")
		self.write("SENSE:FUNCTION \"VOLTAGE:DC\", (@111)")
		self.write("SENSE:FUNCTION \"VOLTAGE:DC\", (@112)")
		self.write("SENSE:FUNCTION \"VOLTAGE:DC\", (@113)")
		self.write("SENSE:FUNCTION \"RESISTANCE\", (@114)")
		self.write("SENSE:FUNCTION \"RESISTANCE\", (@115)")
		self.write("SENSE:FUNCTION \"RESISTANCE\", (@116)")
		self.write("SENSE:FUNCTION \"RESISTANCE\", (@117)")
		self.write("SENSE:FUNCTION \"VOLTAGE:DC\", (@118)")
		self.write("SENSE:FUNCTION \"VOLTAGE:DC\", (@119)")

		self.write("SENSE:VOLTAGE:DC:NPLC 10, (@101)")
		self.write("SENSE:VOLTAGE:DC:NPLC 10, (@102)")
		self.write("SENSE:VOLTAGE:DC:NPLC 10, (@103)")
		self.write("SENSE:RESISTANCE:NPLC 10, (@104)")
		self.write("SENSE:RESISTANCE:NPLC 10, (@105)")
		self.write("SENSE:RESISTANCE:NPLC 10, (@106)")
		self.write("SENSE:RESISTANCE:NPLC 10, (@107)")
		self.write("SENSE:VOLTAGE:DC:NPLC 10, (@108)")
		self.write("SENSE:VOLTAGE:DC:NPLC 10, (@109)")
		self.write("SENSE:VOLTAGE:DC:NPLC 10, (@111)")
		self.write("SENSE:VOLTAGE:DC:NPLC 10, (@112)")
		self.write("SENSE:VOLTAGE:DC:NPLC 10, (@113)")
		self.write("SENSE:RESISTANCE:NPLC 10, (@114)")
		self.write("SENSE:RESISTANCE:NPLC 10, (@115)")
		self.write("SENSE:RESISTANCE:NPLC 10, (@116)")
		self.write("SENSE:RESISTANCE:NPLC 10, (@117)")
		self.write("SENSE:VOLTAGE:DC:NPLC 10, (@118)")
		self.write("SENSE:VOLTAGE:DC:NPLC 10, (@119)")

		self.write("ROUTE:SCAN (@101,102,103,104,105,106,107,108,109,114,115,116,117,118,119)")

	def getSensors(self):
		"""**info**"""
		ch=[n for n in self._channels if n is not None]
		return [f(v) for f,v in zip(ch,self._values)]

	# checks if valves are open (channels are closed)
	def getStatus(self):
		"""**INFO**"""
		self._measureThread._input="ROUTE:CLOSE? (@201:220)"

		# wait until executed
		while self._measureThread._input is not None: sleep(.1)
		answer=self._measureThread._output
		answer=[int(n)>0 for n in answer.split(b',')]
		return answer

	def setRelais(self,rel_nr=1,opening=True):
		"""
		Parameters:
			rel_nr (int):
				**INFO**
			opening (boolean):
				**INFO**
		"""
		# open relais, close valve
		if opening: self._measureThread._input="ROUTE:OPEN (@%d)"%(200+rel_nr)
		# close relais, open valve
		else: self._measureThread._input="ROUTE:CLOSE (@%d)"%(200+rel_nr)

		# wait until executed
		while self._measureThread._input is not None: sleep(.1)

	def closeValve(self,nr):
		"""
		Parameters:
			nr (**INFO**):
				**INFO**
		"""
		self.setRelais(nr,True)

	def openValve(self,nr):
		"""
		Parameters:
			nr (**INFO**):
				**INFO**
		"""
		self.setRelais(nr,False)

	def CY7_Temperature(self,v):
		"""
		Parameters:
			v (**INFO**):
				**INFO**
		"""
		Voltage=[
			0.09062,0.10191,0.12547,0.14985,0.17464,0.19961,0.22463,0.24963,0.27456,0.29941,
			0.32416,0.34881,0.37337,0.39783,0.42221,0.44647,0.47069,0.49484,0.51892,0.54294,
			0.56690,0.59080,0.61465,0.63841,0.66208,0.68564,0.70908,0.73238,0.75554,0.77855,
			0.80138,0.82404,0.84650,0.86873,0.89072,0.91243,0.93383,0.95487,0.97550,0.98564,
			0.99565,1.00552,1.01525,1.02482,1.03425,1.04353,1.05267,1.05629,1.05988,1.06346,
			1.06700,1.07053,1.07402,1.07748,1.08093,1.08436,1.08781,1.09131,1.09490,1.09864,
			1.10263,1.10702,1.10945,1.11212,1.11517,1.11896,1.12463,1.13598,1.15558,1.17705,
			1.19645,1.21440,1.22314,1.23184,1.24053,1.24928,1.25810,1.26702,1.27607,1.28527,
			1.29464,1.30422,1.31403,1.32412,1.33453,1.34530,1.35647,1.36809,1.38021,1.39287,
			1.40615,1.42013,1.43488,1.45048,1.46700,1.48443,1.50272,1.52166,1.54097,1.56027,
			1.57928,1.59782,1.60506,1.61220,1.61920,1.62602,1.63263,1.63905,1.64529,1.65134,
			1.65721,1.66292,1.66845,1.67376,1.67880,1.68352,1.68786,1.69177,1.69521,1.69812]

		Temperature=[	# in Kelvin
			475.0,470.0,460.0,450.0,440.0,430.0,420.0,410.0,400.0,390.0,
			380.0,370.0,360.0,350.0,340.0,330.0,320.0,310.0,300.0,290.0,
			280.0,270.0,260.0,250.0,240.0,230.0,220.0,210.0,200.0,190.0,
			180.0,170.0,160.0,150.0,140.0,130.0,120.0,110.0,100.0,95.0,
			90.0,85.0,80.0,75.0,70.0,65.0,60.0,58.0,56.0,54.0,
			52.0,50.0,48.0,46.0,44.0,42.0,40.0,38.0,36.0,34.0,
			32.0,30.0,29.0,28.0,27.0,26.0,25.0,24.0,23.0,22.0,
			21.0,20.0,19.5,19.0,18.5,18.0,17.5,17.0,16.5,16.0,
			15.5,15.0,14.5,14.0,13.5,13.0,12.5,12.0,11.5,11.0,
			10.5,10.0,9.5,9.0,8.5,8.0,7.5,7.0,6.5,6.0,
			5.5,5.0,4.8,4.6,4.4,4.2,4.0,3.8,3.6,3.4,
			3.2,3.0,2.8,2.6,2.4,2.2,2.0,1.8,1.6,1.4]

		spl=make_interp_spline(Voltage,Temperature)
		return float(spl(v/5.))

	def PT100_Temperature(self,R):
		"""
		Parameters:
			R (int or float):
				**INFO**
		"""
		if R<18.5: return -999.999;	# underrange
		if R>150.0: return 999.999	# overrange

		R0=100.
		c=[1.811049e-03,2.559214e+00,9.788229e-04,-1.693120e-06,2.682225e-08]

		temp=c[4]
		for n in reversed(c[:-1]): temp=temp*(R-R0)+n
		temp+=273.15

		return temp

	def PT1000_Temperature(self,R):
		"""
		Parameters:
			R (int or float):
				**INFO**
		"""
		return self.PT100_Temperature(R/10.)

	def PKR251_Pressure(self,v):
		"""
		Parameters:
			v (**INFO**):
				**INFO**
		
		+---------------+----------------------------------+
		| Voltage U     | Pressure p                       |
		|  [V]          |  [mbar]      [Torr]      [Pa]    |
		+===============+==================================+
		| < 0.5         | sensor error                     |
		+---------------+----------------------------------+
		| 0.5 ...  1.82 | underrange                       |
		+---------------+----------+-----------+-----------+
		|     1.82      | 5.0e-09  |  3.8e-09  | 5.0e-07   |
		+---------------+----------+-----------+-----------+
		|     2.00      | 1.0e-08  |  7.5e-09  |  1.0e-06  |
		+---------------+----------+-----------+-----------+
		|     2.60      | 1.0e-07  |  7.5e-08  | 1.0e-05   |
		+---------------+----------+-----------+-----------+
		|     3.20      | 1.0e-06  |  7.5e-07  | 1.0e-04   |
		+---------------+----------+-----------+-----------+
		|     3.80      | 1.0e-05  |  7.5e-06  | 1.0e-03   |
		+---------------+----------+-----------+-----------+
		|     4.40      | 1.0e-04  |  7.5e-05  | 1.0e-02   |
		+---------------+----------+-----------+-----------+
		|     5.00      | 1.0e-03  |  7.5e-04  | 1.0e-01   |
		+---------------+----------+-----------+-----------+
		|     5.60      | 1.0e-02  |  7.5e-03  | 1.0e-00   |
		+---------------+----------+-----------+-----------+
		|     6.20      | 1.0e-01  |  7.5e-02  | 1.0e+01   |
		+---------------+----------+-----------+-----------+
		|     6.80      | 1.0e+00  |  7.5e-01  | 1.0e+02   |
		+---------------+----------+-----------+-----------+
		|     7.40      | 1.0e+01  |  7.5e+00  | 1.0e+03   |
		+---------------+----------+-----------+-----------+
		|     8.00      | 1.0e+02  |  7.5e+01  | 1.0e+04   |
		+---------------+----------+-----------+-----------+
		|     8.60      | 1.0e+03  |  7.5e+02  | 1.0e+05   |
		+---------------+----------+-----------+-----------+
		| 8.6 ...  9.5  | overrange                        |
		+---------------+----------------------------------+
		| 9.5 ... 10.5  | sensor error (Pirani defect)     |
		+---------------+----------------------------------+
		"""

		if v<0.5: return -3.									# sensor error
		elif v>=0.5 & v<=1.82: return -1.						# underrange
		elif v>1.82 & v<8.6: return 1e-8*(10.**((v-2.)/.6))		# measurement ok
		elif v>=8.6 & v<=9.5: return -2.						# overrange
		else: return -4.										# Pirani sensor defect

	def PKR251_Identification(self,v):
		"""
		Parameters:
			v (**INFO**):
				**INFO**
		
		+---------------+-----------------------------------+
		|   Voltage U   | Identification                    |
		|     [V]       |                                   |
		+===============+===================================+
		|     < 2.4     | Combined Pirani/Cold Cathode Mode |
		+---------------+-----------------------------------+
		|     > 2.4     | Pure Pirani Operation Mode        |
		+---------------+-----------------------------------+
		|     > 14.0    | No Pressure Sensor Connected      |
		+---------------+-----------------------------------+
		"""

		if v<=.1: return -2.				#short circuit in sensor
		elif v>.1 & v<=2.4: return 1.		# combined Pirani/Cold Cathode mode
		elif v> 2.4 & v<=14.: return 0.		# pure Pirani mode
		else: return -1.					# no pressore sensor connected


class measureThread(Thread):
	"""For more information about the Thread’s methods and attributes used here, please refer to the `threading.Thread class documentation <https://docs.python.org/3/library/threading.html>`_
	"""
	def __init__(self,parent):
		
		Thread.__init__(self)
		self.parent=parent
		self.read=parent.read
		self.write=parent.write
		self.ask=parent.ask
		self.running=False
		self._initialized=True
		self._output=None
		self._input=None
		self.start()

	def close(self):
		self._initialized=False

	def run(self):
		"""**INFO**"""
		self.running=True

		while self._initialized:
			# update date and time
			self.parent._now=strftime("%d-%m-%Y %H:%M:%S")
			# measure
			results=self.ask("READ?")		# trigger the scan
			# update self.output
			if len(results): self.parent._values=[float(n) for n in results.split(b',')]

			if self._input is not None:
				if ("?" if isinstance(self._input,str) else b"?") in self._input:
					self._output=self.ask(self._input)
				else: self.write(self._input)
			self._input=None
			sleep(.2)

		self.running=False
