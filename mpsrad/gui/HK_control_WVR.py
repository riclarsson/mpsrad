# -*- coding: utf-8 -*-
# Housekeeping and control widgets for water vapor radiometer
# Author: Borys Dabrowski, dabrowski@mps.mpg.de
# Last modification: 27.07.2018
# =============================================================================

from guidata.dataset.datatypes import DataSet,BeginGroup,EndGroup
from guidata.dataset.dataitems import FloatItem,IntItem,ChoiceItem,DirectoryItem
from guidata.dataset.qtwidgets import DataSetShowGroupBox,DataSetEditGroupBox
from guiqwt.config import _

import os

# Housekeeping widget =========================================================
class HKwidget(DataSetShowGroupBox):
	class HKset(DataSet):
		_bc=BeginGroup("Cryostat").set_pos(col=0)
		Cold_Load=FloatItem("Cold Load",default=1.,unit="K").set_prop("display",format="%4.2f")
		Hot_Load=FloatItem("Hot Load",default=1.,unit="K").set_prop("display",format="%4.2f")
		HEMT=FloatItem("HEMT",default=1.,unit="K").set_prop("display",format="%4.2f")
		_ec=EndGroup("Cryostat")
		_bfa=BeginGroup("CTS Filters").set_pos(col=1)
		T3_A=FloatItem("CTS1 A",default=1.,unit="K").set_prop("display",format="%4.2f")
		T3_B=FloatItem("CTS1 B",default=1.,unit="K").set_prop("display",format="%4.2f")
		T2_A=FloatItem("CTS2 A",default=1.,unit="K").set_prop("display",format="%4.2f")
		T2_B=FloatItem("CTS2 B",default=1.,unit="K").set_prop("display",format="%4.2f")
		_efa=EndGroup("CTS Filters")
		_bfb=BeginGroup("Other").set_pos(col=2)
		T6_A=FloatItem("T6 A",default=1.,unit="K").set_prop("display",format="%4.2f")
		T6_B=FloatItem("T6 B",default=1.,unit="K").set_prop("display",format="%4.2f")
		T7_A=FloatItem("T7 A",default=1.,unit="K").set_prop("display",format="%4.2f")
		T7_B=FloatItem("T7 B",default=1.,unit="K").set_prop("display",format="%4.2f")
		_efb=EndGroup("Other")

		choice=[(-2,"short circuit"),(-1,"no sensor"),(0,"Pirani"),(1,"Pirani/Cathode")]

		_bp=BeginGroup("Pressure").set_pos(col=3)
		P1_Dewar=FloatItem("P1 Dewar",default=0.,unit="mbar").set_prop("display",format="%4.2f")
		P1_Ident=ChoiceItem("P1 Ident.",choice,default=-1)
		P2_Pump=FloatItem("P2 Pump",default=0.,unit="mbar").set_prop("display",format="%4.2f")
		P2_Ident=ChoiceItem("P2 Ident.",choice,default=-1)
		_ep=EndGroup("Pressure")

	def __init__(self,*args,**kwargs):
		DataSetShowGroupBox.__init__(self,_("Housekeeping"),self.HKset)

	def updateHK(self,sensors):
		self.dataset.Cold_Load=sensors[1]
		self.dataset.Hot_Load=sensors[2]
		self.dataset.HEMT=sensors[0]
		self.dataset.T2_A=sensors[3]
		self.dataset.T2_B=sensors[9]
		self.dataset.T3_A=sensors[4]
		self.dataset.T3_B=sensors[10]
		self.dataset.T6_A=sensors[5]
		self.dataset.T6_B=sensors[11]
		self.dataset.T7_A=sensors[6]
		self.dataset.T7_B=sensors[12]
		self.dataset.P1_Dewar=sensors[7]
		self.dataset.P2_Pump =sensors[8]
		self.dataset.P1_Ident=int(sensors[13])
		self.dataset.P2_Ident=int(sensors[14])

		self.get()
# =============================================================================

# Control widget ==============================================================
class Controlwidget(DataSetEditGroupBox):
	class Controlset(DataSet):
		Directory=DirectoryItem("Directory",default=os.path.abspath("/home/dabrowski/data/"))

		_bt=BeginGroup("Configuration").set_pos(col=0)
		Frequency=FloatItem("Frequency",default=21.1,unit="GHz").set_prop("display",format="%3.1f")
		IntegrationTime=FloatItem("Integration time",default=5.,unit="s").set_prop("display",format="%3.1f")
		BlankTime=IntItem("Blank time",default=5,unit="ms")
		Antenna=IntItem("Antenna offset",default=1000,unit="")
		NSpec=IntItem("Spectra per file",default=7000,unit="")
		_et=EndGroup("Configuration")

#		_bs=BeginGroup("Sweep").set_pos(col=1)
#		Sweep=ChoiceItem("Sweep",["Off","On"],default=False)
#		FrequencyStep=FloatItem("Frequency step",default=.2,unit="GHz").set_prop("display",format="%3.1f")
#		Offset=FloatItem("Offset",default=6.,unit="GHz").set_prop("display",format="%3.1f")
#		SweepStep=FloatItem("Sweep step",default=10.,unit="GHz").set_prop("display",format="%3.1f")
#		_es=EndGroup("Sweep")

	def __init__(self,*args,**kwargs):
		DataSetEditGroupBox.__init__(self,_("Control panel"),self.Controlset,show_button=False)

	def getControls(self):
		self.set()
		return self.dataset
# =============================================================================
