# -*- coding: utf-8 -*-
"""
Housekeeping and control widgets for IRAM radiometer

Last modification: 19.07.2018

Author: Borys Dabrowski
"""
# =============================================================================

from guidata.dataset.datatypes import DataSet,BeginGroup,EndGroup
from guidata.dataset.dataitems import FloatItem,IntItem,ChoiceItem,DirectoryItem
from guidata.dataset.qtwidgets import DataSetShowGroupBox,DataSetEditGroupBox
from guiqwt.config import _

import os

from mpsrad.frontend.dbr import dbr

# Housekeeping widget =========================================================
class HKwidget(DataSetShowGroupBox):
	"""Create the different widget useful for the housekeeping values

	.. note:: For more information about the guidata.dataset.qtwidgets module used here, please refer to its `documentation <https://pythonhosted.org/guidata/_modules/guidata/dataset/qtwidgets.html>`_
	"""
	class HKset(DataSet):
		_bd=BeginGroup("DACs").set_pos(col=0)
		GunnBias=FloatItem("GunnBias",default=1.,unit="").set_prop("display",format="%4.2f")
		LoopGain=FloatItem("LoopGain",default=1.,unit="").set_prop("display",format="%4.2f")
		HmxBias=FloatItem("HmxBias",default=1.,unit="").set_prop("display",format="%4.2f")
		_ed=EndGroup("DACs")

		_ba=BeginGroup("ADCs").set_pos(col=1)
		OffsetVolt=FloatItem("Offset Volt.",default=1.,unit="V").set_prop("display",format="%4.2f")
		PLLIFLevel=FloatItem("PLL IF Level",default=1.,unit="V").set_prop("display",format="%4.2f")
		HmxCurrent=FloatItem("HmxCurrent",default=1.,unit="mA").set_prop("display",format="%4.2f")
		_ea=EndGroup("ADCs")
	
		_bc1=BeginGroup("Cryostat").set_pos(col=2)
		Band2=FloatItem("Band2",default=1.,unit="<sup>o</sup>K").set_prop("display",format="%4.2f")
		Band3=FloatItem("Band3",default=1.,unit="<sup>o</sup>K").set_prop("display",format="%4.2f")
		ColdLoad=FloatItem("ColdLoad",default=1.,unit="<sup>o</sup>K").set_prop("display",format="%4.2f")
		_ec1=EndGroup("Cryostat")
		_bc2=BeginGroup("Cryostat").set_pos(col=3)
		T_04K=FloatItem("T_04K",default=1.,unit="<sup>o</sup>K").set_prop("display",format="%4.2f")
		T_15K=FloatItem("T_15K",default=1.,unit="<sup>o</sup>K").set_prop("display",format="%4.2f")
		T_77K=FloatItem("T_77K",default=1.,unit="<sup>o</sup>K").set_prop("display",format="%4.2f")
		_ec2=EndGroup("Cryostat")

		_be=BeginGroup("Environment").set_pos(col=4)
		RoomTemp=FloatItem("Room",default=1.,unit="<sup>o</sup>K").set_prop("display",format="%4.2f")
		OutsideTemp=FloatItem("Outside",default=1.,unit="<sup>o</sup>K").set_prop("display",format="%4.2f")
		Humidity=FloatItem("Humidity",default=1.,unit="%").set_prop("display",format="%4.2f")
		_ee=EndGroup("Environment")

	def __init__(self,*args,**kwargs):
		DataSetShowGroupBox.__init__(self,_("Housekeeping"),self.HKset)

	def updateHK(self,status,controlValues):
#		status=self.dbr.get_status()
#		c=self.Controlvalues
		c=controlValues
		band=[2,3][c.dataset.Frequency>dbr.band2limits[1]]
		c.setTitle("Control panel, Band %i"%band)

		val=lambda name: [n['value'] for n in status if n['name']==name][0]

		self.dataset.ColdLoad=val('cryo.ColdLd.val')
		self.dataset.Band2=val('cryo.Band2.val')
		self.dataset.Band3=val('cryo.Band3.val')
		self.dataset.T_77K=val('cryo.T_77K.val')
		self.dataset.T_15K=val('cryo.T_15K.val')
		self.dataset.T_04K=val('cryo.T_04K.val')

		self.dataset.GunnBias=val('B%i.dac_GUNN_BIAS.act.val'%band)
		self.dataset.LoopGain=val('B%i.dac_LOOP_GAIN.act.val'%band)
		self.dataset.HmxBias=val('B%i.dac_HMX_BIAS.act.val'%band)
		self.dataset.OffsetVolt=val('B%i.adc_OFFSET_VOLT.act.val'%band)
		self.dataset.PLLIFLevel=val('B%i.adc_PLL_IF_LEVEL.act.val'%band)
		self.dataset.HmxCurrent=val('B%i.adc_HMX_CURRENT.act.val'%band)
		
		try:
			hkvals=self.measurements._housekeeping[-1]
			if hkvals[1]!=0: self.dataset.RoomTemp=hkvals[1]	# room temperature K
			if hkvals[2]!=0: self.dataset.OutsideTemp=hkvals[2]	# outside temperature K
			if hkvals[3]!=0: self.dataset.Humidity=hkvals[3]	# humidity %

			if hkvals[4]!=0: c.dataset.Chopper=chr(int(hkvals[4]))
		except: pass

		c.set()
		self.get()
# =============================================================================

# Control widget ==============================================================
class Controlwidget(DataSetEditGroupBox):
	"""
	.. note:: For more information about the guidata.dataset.qtwidgets module used here, please refer to its `documentation <https://pythonhosted.org/guidata/_modules/guidata/dataset/qtwidgets.html>`_
	"""
	class Controlset(DataSet):
		Directory=DirectoryItem("Directory",default=os.path.abspath("../../../data/"))
	
		_bt=BeginGroup("Frequency and time").set_pos(col=0)
		Frequency=FloatItem("Frequency",default=142.175,unit="GHz").set_prop("display",format="%3.1f")
		IntegrationTime=FloatItem("Integration time",default=5.,unit="s").set_prop("display",format="%3.1f")
		BlankTime=IntItem("Blank time",default=5,unit="ms")
		_et=EndGroup("Frequency and time")
	
		_bs=BeginGroup("Sweep").set_pos(col=1)
		Sweep=ChoiceItem("Sweep",["Off","On"],default=False)
		FrequencyStep=FloatItem("Frequency step",default=.2,unit="GHz").set_prop("display",format="%3.1f")
		Offset=FloatItem("Offset",default=6.,unit="GHz").set_prop("display",format="%3.1f")
		SweepStep=FloatItem("Sweep step",default=10.,unit="GHz").set_prop("display",format="%3.1f")
		_es=EndGroup("Sweep")
	
		_bo=BeginGroup("Other").set_pos(col=2)
		Chopper=ChoiceItem("Chopper",[('C',"Cold"),('H',"Hot"),('A',"Antenna"),('R',"Reference")],default='C')
		Antenna=IntItem("Antenna offset",default=1000,unit="")
		NSpec=IntItem("Spectra per file",default=7000,unit="")
		Format=ChoiceItem("File format",[('e',"e"),('a',"a")],default='a')
		_eo=EndGroup("Other")

	def __init__(self,*args,**kwargs):
		DataSetEditGroupBox.__init__(self,_("Control panel"),self.Controlset,show_button=False)

	def getControls(self):
		self.set()
		return self.dataset
# =============================================================================
