#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Tue Apr 17 15:22:00 2018

@author: dabrowski
"""

from .pt100 import pt100
import serial
from time import time,sleep,localtime

ref=pt100()
ref.init()

ard=serial.Serial('/dev/ttyUSB2',9600,timeout=2)

#%%
t0=time()
hhmm=localtime()[3:5]

while 1:
	t,line,t_ref=time(),'',0

	ard.flushInput()
	while ard.in_waiting==0 and t<2: sleep(.1)
	line=ard.readline().replace('\r\n','')

	t_ref=ref.get_temperature('C')
	tmp="%0.2f %0.2f %s\n"%(t-t0,t_ref,line)
	print (tmp)

	with open('%2d_%2d.txt'%hhmm, "a") as fh: fh.write(tmp)
	while time()-t<10: pass
