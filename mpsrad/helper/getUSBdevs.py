# -*- coding: utf-8 -*-
"""
Identify USB Arduino controlers (chopper and wobbler) device paths

Last modification: 14.06.2018
Author: Borys Dabrowski, dabrowski@mps.mpg.de
"""
from os import listdir
from time import time,sleep
import serial

def getUSBdevs():
	paths=['/dev/'+n for n in listdir('/dev/') if 'ttyUSB' in n]

	out={}
	for path in paths:
		s=serial.Serial(path,115200,timeout=2)
		s.flushInput()
		s.flushOutput()
		while s.in_waiting==0:
			s.write(b'G\n')
			t0=time()
			while s.in_waiting==0 and time()-t0<5: sleep(.1)

		answ=s.readline().decode()
		answ=answ[:answ.find(' ')]
		if len(answ): out[answ]=path

		s.close()

	return out

def displayUSBdevs():
	print('Identification in progress...')
	print(getUSBdevs())
	print('Done!')
