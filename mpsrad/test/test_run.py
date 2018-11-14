#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov 22 10:34:16 2017

@author: larsson
"""
try:
	import mps
	measurements = mps.measurements
	FW = mps.FW.FW
except:
	from mpsrad.measurements import measurements
	from mpsrad.backend.FW import FW


m=measurements(sweep=False,full_file=7000,freq=142.175,
	integration_time=5000,
	blank_time=5,
	basename='../../data/',
#	spectrometers=[FW],
#	spectrometer_hosts=['localhost'],
#	spectrometer_tcp_ports=[25144],
#	spectrometer_udp_ports=[16210],
#	spectrometer_channels=[[8192, 8192]],
#	raw_formats=[measurements.files.aform],
#	formatnames=['a']
	)
m.init()


for i in range(70000):
	m.run()
	m.save()
	m.update()

m.close()


