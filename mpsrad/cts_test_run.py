#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov 22 10:34:16 2017

@author: larsson
Modified: Borys Dabrowski
"""

from .wobbler import wobbler
from .chopper import chopper
from .backend import rcts104

print("Connecting Wobbler")
wob = wobbler.wobbler()
print("Connecting Chopper")
chop = chopper.chopper()
print("Connecting CTS")
cts = rcts104.rcts104(integration_time=6000)

#%%
print("Init Wobbler")
wob.init(4000)
print("Init Chopper")
chop.init()
print("Init CTS")
cts.init()

#%%
print("Setting Chopper")
chop.set_ant()
print("Moving Wobbler")
wob.move(10000)
print("Running CTS")
cts.run()
print("Waiting for Wobbler")
wob.wait()
cts.get_data(0)

print("Setting Chopper")
chop.set_cold()
print("Moving Wobbler")
wob.move(4000)
print("Running CTS")
cts.run()
print("Waiting for Wobbler")
wob.wait()
cts.get_data(1)

print("Setting Chopper")
chop.set_ant()
print("Moving Wobbler")
wob.move(10000)
print("Running CTS")
cts.run()
print("Waiting for Wobbler")
wob.wait()
cts.get_data(2)

print("Setting Chopper")
chop.set_hot()
print("Moving Wobbler")
wob.move(4000)
print("Running CTS")
cts.run()
print("Waiting for Wobbler")
wob.wait()
cts.get_data(3)

#%%
print("Saving data: " + cts.save_data())


wob.close()
chop.close()
cts.close()
