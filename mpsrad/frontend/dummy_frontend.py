
"""
Author: Yann Goument

Emulates the DBR's function in case of dysfunction
"""
#============================================================================================

# imports and definitions #==================================================================


import datetime
import socket
import re
import time
import sys
import numpy as np




#============================================================================================


class dummy_dbr:

	def __init__(self, server='dbr', port=1080):
		self._s = str(server)
		self._p = str(port)
		self._initialized = False

	
	def issue (self):
		assert not self._initialized
		print('ServerProxy not reached...')
		print('Switch on the dummy dbr')

		time.sleep(1)
		self._initialized = True

	def getStatus(self):
		assert self,_initialized
		status=[]

		name_list=["B2.adc_HMX_CURRENT.act.val", "B2.adc_OFFSET_VOLT.act.val", "B2.adc_PLL_IF_LEVEL.act.val", "B2.dac_GUNN_BIAS.act.val", "B2.dac_HMX_BIAS.act.val", "B2.dac_LOOP_GAIN.act.val", 				"B2.hemt_H_LSB.s0.idm.val", "B2.hemt_H_LSB.s0.vdm.val", "B2.hemt_H_LSB.s0.vgm.val", "B2.hemt_H_LSB.s1.idm.val", "B2.hemt_H_LSB.s1.vdm.val", "B2.hemt_H_LSB.s1.vgm.val", "B2.hemt_H_LSB.s2.idm.val", "B2.hemt_H_LSB.s2.vdm.val", "B2.hemt_H_LSB.s2.vgm.val", "B2.hemt_H_USB.s0.idm.val", "B2.hemt_H_USB.s0.vdm.val", "B2.hemt_H_USB.s0.vgm.val",	"B2.hemt_H_USB.s1.idm.val", "B2.hemt_H_USB.s1.vdm.val", "B2.hemt_H_USB.s1.vgm.val", "B2.hemt_H_USB.s2.idm.val", "B2.hemt_H_USB.s2.vdm.val", "B2.hemt_H_USB.s2.vgm.val", "B2.junc_H1.curr.act.val", "B2.junc_H1.volt.act.val", "B2.junc_H2.curr.act.val", "B2.junc_H2.volt.act.val", "B2.motor_LO_FREQ.act.val", "B2.motor_LO_HMX_POWER.act.val", "B2.motor_LO_POWER1.act.val", "B2.motor_LO_POWER2.act.val",  "B2.motor_LO_POWER_GUNN.act.val", "B3.adc_HMX_CURRENT.act.val", "B3.adc_OFFSET_VOLT.act.val", "B3.adc_PLL_IF_LEVEL.act.val", "B3.dac_GUNN_BIAS.act.val", "B3.dac_HMX_BIAS.act.val", "B3.dac_LOOP_GAIN.act.val", "B3.hemt_V_LSB.s0.idm.val", "B3.hemt_V_LSB.s0.vdm.val", "B3.hemt_V_LSB.s0.vgm.val", "B3.hemt_V_LSB.s1.idm.val", "B3.hemt_V_LSB.s1.vdm.val", "B3.hemt_V_LSB.s1.vgm.val", "B3.hemt_V_LSB.s2.idm.val", "B3.hemt_V_LSB.s2.vdm.val", "B3.hemt_V_USB.s2.vgm.val", "B3.hemt_V_USB.s0.idm.val", "B3.hemt_V_USB.s0.vdm.val", "B3.hemt_V_USB.s0.vgm.val", "B3.hemt_V_USB.s1.idm.val", "B3.hemt_V_USB.s1.vdm.val", "B3.hemt_V_USB.s1.vgm.val", "B3.hemt_V_USB.s2.idm.val", "B3.hemt_V_USB.s2.vdm.val", "B3.hemt_V_USB.s2.vgm.val", "B3.junc_V1.curr.act.val", "B3.junc_V1.volt.act.val", "B3.junc_V2.curr.act.val", "B3.junc_V2.volt.act.val", "B3.motor_LO_FREQ.act.val", "B3.motor_LO_HMX_POWER.act.val", "B3.motor_LO_POWER1.act.val", "B3.motor_LO_POWER2.act.val", "B3.motor_LO_POWER_GUNN.act.val", "cryo.Ambnt.val", "cryo.Band1.val", "cryo.Band2.val", "cryo.Band3.val", "cryo.Band4.val", "cryo.ColdLd.val", "cryo.T_04K.val", "cryo.T_15K.val", "cryo.T_77K.val", "table.temperature.val", "B2.dac_GUNN_BIAS.req.req", "B2.dac_HMX_BIAS.req.req", "B2.dac_LOOP_GAIN.req.req", "B2.flo.req", "B2.junc_H1.curr.req.req", "B2.junc_H1.volt.req.req", "B2.junc_H2.curr.req.req", "B2.junc_H2.volt.req.req", "B2.motor_LO_FREQ.req.req", "B2.motor_LO_HMX_POWER.req.req", "B2.motor_LO_POWER1.req.req", "B2.motor_LO_POWER2.req.req", "B2.motor_LO_POWER_GUNN.req.req", "B3.dac_GUNN_BIAS.req.req", "B3.dac_HMX_BIAS.req.req", "B3.dac_LOOP_GAIN.req.req", "B3.flo.req", "B3.junc_V1.curr.req.req", "B3.junc_V1.volt.req.req", "B3.junc_V2.curr.req.req", "B3.junc_V2.volt.req.req", "B3.motor_LO_FREQ.req.req", "B3.motor_LO_HMX_POWER.req.req", "B3.motor_LO_POWER1.req.req", "B3.motor_LO_POWER2.req.req", "B3.motor_LO_POWER_GUNN.req.req", "B2.junc_H1.prot.act.val", "B2.junc_H1.rtyp.act.val", "B2.junc_H2.prot.act.val", "B2.junc_H2.rtyp.act.val", "B2.loswi.deltaf.act.val", "B2.loswi.gunn.act.val", "B2.loswi.islocked.val", "B2.loswi.loop.act.val", "B2.loswi.sweep.act.val", "B2B3.jreg.protect.act.val", "B2B3.jreg.status.val", "B3.junc_V1.prot.act.val", "B3.junc_B1.rtyp.act.val", "B3.junc_V2.prot.act.val", "B3.junc_V2.rtyp.act.val", "B3.loswi.deltaf.act.val", "B3.loswi.gunn.act.val", "B3.loswi.islocked.val", "B3.loswi.loop.act.val", "B3.loswi.sweep.act.val", "I2C_PS1.act.val", "table.actPosition.val", "table.extendedStatus.val", "table.isInitialized.val", "table.isRunning.val", "table.negLimit.val", "table.posLimit.val", "table.shortStatus.val", "B2.deltaf.req", "B2.junc_H1.prot.req.req", "B2.junc_H1.rtyp.req.req", "B2.junc_H2.prot.req.req", "B2.junc_H2.rtyp.req.req", "B2.loswi.deltaf.req.req", "B2.loswi.gunn.req.req", "B2.loswi.loop.req.req", "B2.loswi.sweep.req.req", "B2B3.jreg.protect.req.req", "B3.deltaf.req", "B3.junc_V1.prot.req.req", "B3.junc_V1.rtyp.req.req", "B3.junc_V2.prot.req.req", "B3.junc_V2.rtyp.req.req", "B3.loswi.deltaf.req.req", "B3.loswi.gunn.req.req", "B3.loswi.loop.req.req", "B3.loswi.sweep.req.req", "I2C_BUS.req", "I2C_PS1.req.req", "chopper.reqPosition.req", "table.init.req", "table.reqPosition.req", "warmj.B3M1.req", "warmj.B3M2.req", "warmj.P4K1.req", "warmj.P4K2.req"]
		for i in range(len(name_list)) :
			status.append({'name' : name_list[i], 'value' : -1})
		return (status)

	def close(self):
		assert self._initialized
		self._initialized = False

	
		
