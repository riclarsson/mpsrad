# -*- coding: utf-8 -*-
# IRAM GUI
# Author: Borys Dabrowski, dabrowski@mps.mpg.de
# Last modification: 09.05.2018
from guidata.dataset.datatypes import DataSet,BeginGroup,EndGroup
# =============================================================================

# Imports and definitions =====================================================
from guidata.qt.QtGui import QMainWindow,QSplitter,QPen,QIcon,QFileDialog,\
	QLabel,QToolBar,QToolButton,QStatusBar,QTabWidget,QWidget,QVBoxLayout
from guidata.qt.QtCore import Qt,QSize,QTimer
from guidata.dataset.dataitems import FloatItem,IntItem,ChoiceItem,DirectoryItem
from guidata.dataset.qtwidgets import DataSetShowGroupBox,DataSetEditGroupBox
from guiqwt.config import _
from guiqwt.curve import CurvePlot,CurveItem
from guiqwt.styles import CurveParam
from guiqwt.baseplot import BasePlot

from time import localtime,sleep,time
from threading import Thread

import numpy as np
import os

from measurements import measurements
import files
from FW import FW

# Measurements as separate thread =============================================
class measure(Thread):
	def __init__(self,parent):
		Thread.__init__(self)
		self.parent=parent
		self.close_flag=False
		self.cmd=None
		self.measurements=None
		self.now=time()
		self.start()

	def close(self):
		self.close_flag=True

	def do(self,cmd):
		self.cmd=cmd

	def busy(self):
		return self.cmd is not None

	def run(self):
		while not self.close_flag:
			sleep(.01)
			# init measurements
			if self.cmd is 'init':
				if self.measurements is None:
					self.parent.setMeasurement()
					self.measurements=self.parent.measurements
#				self.measurements.init()
				self.cmd=None

				tabs=self.parent.mainwidget.tabs
				tabs.removeTabs()
				tabs.setTabs([n.name for n in self.parent.measurements.spec])

			# run measurements (main loop)
			elif self.cmd is 'run':
					self.measurements.run()
					self.measurements.save()
					self.measurements.update()

			# stop measurements
			elif self.cmd is 'stop': self.cmd=None

			# stop measurements and close all devices
			elif self.cmd is 'close':
				if self.measurements._initialized: self.measurements.close()
				self.measurements=None
				self.parent.measurements=None
				self.cmd=None

			# tests
			elif self.cmd is 'test':
				print(localtime())
				self.cmd=None
			elif self.cmd is 'periodic':
				if time()-self.now>1:
					self.now=time()
					print(localtime().tm_sec)
			else: pass

		if self.measurements is not None:
			if self.measurements._initialized: self.measurements.close()

#	def setMeasurement(self):
#		self.parent.Controlvalues.set()
#		c=self.parent.Controlvalues.dataset
#		fnames=['e','a'][c.Format]
#		form=lambda fnames: files.aform if fnames is 'a' else files.eform
#
#		self.measurements=measurements(
##			spectrometers=[FW],spectrometer_hosts=['localhost'],
##			spectrometer_tcp_ports=[25144],spectrometer_udp_ports=[16210],
##			spectrometer_channels=[[8192, 8192]],
#			formatnames=fnames,raw_formats=[form(f) for f in fnames],
#			basename=c.Directory,
#			sweep=c.Sweep,
#			full_file=c.NSpec,
#			freq=c.Frequency,
#			integration_time=int(c.IntegrationTime*1000),
#			blank_time=c.BlankTime,
#			)

# Main window GUI =============================================================

# Tollbar with buttons ========================================================
class ToolBar(QToolBar):
	def __init__(self,Icons):
		QToolBar.__init__(self)

		ButtonAxis=QToolButton()
		ButtonAxis.setCheckable(True)
		ButtonAxis.setChecked(True)
		ButtonAxis.setIcon(Icons["resize"])
		ButtonAxis.setToolTip(u"Resize Y axes")
		ButtonAxis.released.connect(lambda *args:window.axisToggle())

#		ButtonSave=QToolButton()
#		ButtonSave.setIcon(Icons["save2"])
#		ButtonSave.setToolTip(u"Save data to file")
#		ButtonSave.released.connect(lambda *args:window.saveData())
#
#		ButtonCool=QToolButton()
#		ButtonCool.setCheckable(True)
#		ButtonCool.setChecked(False)
#		ButtonCool.setIcon(Icons["cool1"])
#		ButtonCool.setToolTip(u"Switch on/off cooling")
##		ButtonCool.released.connect(TecOnOff)
#
#		ButtonTemp=QToolButton()
#		ButtonTemp.setIcon(Icons["therm5"])
#		ButtonTemp.setToolTip(u"Set cooling temperature")
##		ButtonTemp.released.connect(setTemp)
#
#		ButtonDark=QToolButton()
#		ButtonDark.setIcon(Icons["dark"])
#		ButtonDark.setToolTip(u"Set dark spectrum")
##		ButtonDark.released.connect(lambda *args:window.SIR2.setDark())
#
#		ButtonRefs=QToolButton()
#		ButtonRefs.setIcon(Icons["bright"])
#		ButtonRefs.setToolTip(u"Set reference spectrum")
##		ButtonRefs.released.connect(lambda *args:window.SIR2.setRef())

		ButtonPrev=QToolButton()
		ButtonPrev.setCheckable(True)
		ButtonPrev.setChecked(False)
		ButtonPrev.setIcon(Icons["eye"])
		ButtonPrev.setToolTip(u"Initialize")
		ButtonPrev.released.connect(lambda *args:window.measureInitToggle())

#		ButtonSnum=QToolButton()
#		ButtonSnum.setIcon(Icons["stack1"])
#		ButtonSnum.setToolTip(u"Set number of spectra to take")
##		ButtonSnum.released.connect(setNspec)
#
#		ButtonTime=QToolButton()
#		ButtonTime.setIcon(Icons["shutter1"])
#		ButtonTime.setToolTip(u"Set exposure time")
##		ButtonTime.released.connect(setExpTime)

		ButtonMeas=QToolButton()
		ButtonMeas.setCheckable(True)
		ButtonMeas.setChecked(False)
		ButtonMeas.setIcon(Icons["camera"])
		ButtonMeas.setToolTip(u"Measure")
		ButtonMeas.released.connect(lambda *args:window.measureStartStop())


		self.addWidget(ButtonMeas)
#		self.addWidget(ButtonSave)
#		self.addSeparator()
		self.addWidget(ButtonPrev)
		self.addWidget(ButtonAxis)
#		self.addWidget(ButtonDark)
#		self.addWidget(ButtonRefs)
#		self.addSeparator()
#		self.addWidget(ButtonTime)
#		self.addWidget(ButtonSnum)
#		self.addSeparator()
#		self.addWidget(ButtonTemp)
#		self.addWidget(ButtonCool)
#		self.addSeparator()

# Housekeeping widget =========================================================
class HKwidget(DataSet):
	_bd=BeginGroup("DACs").set_pos(col=0)
	GunnBias=FloatItem("GunnBias",default=1.,unit="").set_prop("display",format="%3.1f")
	LoopGain=FloatItem("LoopGain",default=1.,unit="").set_prop("display",format="%3.1f")
	HmxBias=FloatItem("HmxBias",default=1.,unit="").set_prop("display",format="%3.1f")
	_ed=EndGroup("DACs")

	_ba=BeginGroup("ADCs").set_pos(col=1)
	OffsetVolt=FloatItem("Offset Volt.",default=1.,unit="V").set_prop("display",format="%4.1f")
	PLLIFLevel=FloatItem("PLL IF Level",default=1.,unit="V").set_prop("display",format="%4.1f")
	HmxCurrent=FloatItem("HmxCurrent",default=1.,unit="mA").set_prop("display",format="%4.1f")
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

# Control widget ==============================================================
class Controlwidget(DataSet):
	Directory=DirectoryItem("Directory",default=os.path.abspath("../data/"))

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
	Chopper=ChoiceItem("Chopper",["Cold","Hot","Antenna","Reference"],default=0)
	Antenna=IntItem("Antenna offset",default=1000,unit="")
	NSpec=IntItem("Spectra per file",default=7000,unit="")
	Format=ChoiceItem("File format",["e","a"],default=0)
	_eo=EndGroup("Other")

# Control panel (HK + control) ================================================
class ControlPanel(QSplitter):
	def __init__(self,parent):
		QSplitter.__init__(self,parent)
		self.parent=parent
		self.Controlvalues=DataSetEditGroupBox(_("Control panel"),Controlwidget,show_button=False)
		self.addWidget(self.Controlvalues)
		self.HKvalues=DataSetShowGroupBox(_("Housekeeping"),HKwidget)
		self.addWidget(self.HKvalues)
		self.setSizes([2000,1])

# Spectrometer plots panel ====================================================
class SpectrometerPanel(QSplitter):
	# Modified CurvePlot class (with mouse zoom and pan)
	class cplot(CurvePlot):
		def __init__(self,axis=None,updateWidgets=None,*args,**kwargs):
			CurvePlot.__init__(self,*args,**kwargs)
			self.axis=axis
			self.tmp_axis=None
			self.updateWidgets=updateWidgets
		def setDefaultAxis(self,axis=None):
			if axis is None: self.axis=self.getAxis()
			else: self.axis=axis
			self.setAxis()
		def getAxis(self):
			axis=list(self.get_axis_limits(BasePlot.X_BOTTOM)+self.get_axis_limits(BasePlot.Y_LEFT))
			return axis
		def setAxis(self,axis=None):
			if axis is None: axis=self.axis
			self.set_axis_limits(BasePlot.X_BOTTOM,axis[0],axis[1])
			self.set_axis_limits(BasePlot.Y_LEFT,axis[2],axis[3])
			self.setWidget()
		def setActive(self):
			self.tmp_axis=self.getAxis()
			for n in self.getCurvePanels(): n.setFrameStyle(False)
			self.setFrameStyle(True)
			self.setWidget()
		def setWidget(self):
			if self.updateWidgets is None: return
			self.updateWidgets(self.getAxis(),setAxis=self.setAxis)
		def getCurvePanels(self):
			return [k for n in self.parent().parent().children() if isinstance(n,QSplitter)
						for k in n.children() if isinstance(k,CurvePlot)]
		def mousePressEvent(self,evnt):
			if self.axis is None: return
			self.setActive()
			self.button=evnt.button()
			self.XY0=[evnt.x(),evnt.y()]
		def mouseMoveEvent(self,evnt):
			if self.axis is None: return
			axis=self.tmp_axis
			w,h=float(self.size().width()),float(self.size().height())
			dX,dY=(evnt.x()-self.XY0[0])/w,(evnt.y()-self.XY0[1])/h

			if self.button==1:		# drag
				dX,dY=dX*(axis[1]-axis[0]),dY*(axis[3]-axis[2])
				self.setAxis([a+d for a,d in zip(axis,[-dX,-dX,dY,dY])])
			if self.button==2:		# zoom
				dX,dY=np.exp(dX),np.exp(dY)
				amX,amY=(axis[1]+axis[0])/2.,(axis[2]+axis[3])/2.
				a=[(axis[0]-amX)*dX+amX,(axis[1]-amX)*dX+amX,
					(axis[2]-amY)*dY+amY,(axis[3]-amY)*dY+amY]
				self.setAxis(a)
		def mouseReleaseEvent(self,evnt):
			if self.axis is None: return
			self.parent().parent().parent().evnt=evnt
		def mouseDoubleClickEvent(self,evnt):
			if self.axis is None: return
			self.setAxis()

	# Set axis ranges widget
	class XYlim(DataSetEditGroupBox):
		class minmax(DataSet):
			Xmin=FloatItem("X min",default=1.,unit="").set_prop("display",format="%3.1f").set_pos(col=0)
			Xmax=FloatItem("X max",default=1.,unit="").set_prop("display",format="%3.1f").set_pos(col=1)
			Ymin=FloatItem("Y min",default=1.,unit="").set_prop("display",format="%3.1f").set_pos(col=2)
			Ymax=FloatItem("Y max",default=1.,unit="").set_prop("display",format="%3.1f").set_pos(col=3)
		def __init__(self):
			DataSetEditGroupBox.__init__(self,None,self.minmax,show_button=False)
			self.setAxis=None
		def updateWidgets(self,axis=None,setAxis=None):
			if axis is None: return
			self.setAxis=setAxis
			self.dataset.Xmin,self.dataset.Xmax,self.dataset.Ymin,self.dataset.Ymax=axis
			self.get()
		def keyReleaseEvent(self,evnt):
			if self.setAxis is None: return
			self.set()
			axis=[self.dataset.Xmin,self.dataset.Xmax,self.dataset.Ymin,self.dataset.Ymax]
			if axis[0]<axis[1] and axis[2]<axis[3]: self.setAxis(axis)

	def __init__(self,parent,name='Panel',plots=[[['Cold',1],['Hot',1]],[['Antenna',2],['Reference',1]]]):
		QSplitter.__init__(self,parent)
		self.parent=parent
		self.name=name
		self.plots=[i[0] for o in plots for i in o]	# make the name's list flat

		self.active=None
		self.evnt=None

		self.xylim=self.XYlim()

		# Curve panels (plots)
		Hsplit=QSplitter(self)
		plotColumns=[QSplitter(self) for n in plots]

		for rows,c in zip(plots,plotColumns):
			c.setOrientation(Qt.Vertical)
			c.setChildrenCollapsible(False)

			c.cwidgets=[self.cplot(c,xlabel=u"\u0394f [MHz]",ylabel="Count",
					updateWidgets=self.xylim.updateWidgets) for i in rows]
			c.plots=[[CurveItem(CurveParam()) for j in range(i[1])] for i in rows]

			for m,cw in enumerate(c.cwidgets):
				cw.set_title(rows[m][0])
				for p in c.plots[m]:
					p.set_data([0],[0])
					p.parent=cw
					cw.add_item(p)
#				cw.set_axis_limits(BasePlot.Y_LEFT,0,1)
#				cw.set_axis_limits(BasePlot.X_BOTTOM,-750,750)
				cw.setDefaultAxis([-750,750,0,1])
				c.addWidget(cw)

			Hsplit.addWidget(c)

		self.addWidget(Hsplit)
		self.addWidget(self.xylim)
		self.setOrientation(Qt.Vertical)

		self.curvePanels=dict(zip(self.plots,sum([c.cwidgets for c in plotColumns],[])))
		self.curves=dict(zip(self.plots,[i for o in plotColumns for i in o.plots]))

		for nm in self.plots:
			for p in self.curves[nm]: p.setPen(QPen(Qt.blue,1))

		plotColumns[0].cwidgets[0].setActive()

# Spectrometer panels in tabs =================================================
class SpectrometerTabs(QTabWidget):
	def __init__(self,parent,spec_names):
		QTabWidget.__init__(self)
		self.parent=parent
		self.setTabs(spec_names)

	def setTabs(self,spec_names):
		self.sp=[SpectrometerPanel(self.parent,name=name) for name in spec_names]
		for sp in self.sp:
			vBoxlayout=QVBoxLayout()
			vBoxlayout.addWidget(sp)
			tab=QWidget()
			tab.setLayout(vBoxlayout)
			self.addTab(tab,sp.name)

			sp.curves['Antenna'][0].setPen(QPen(Qt.black,1))
			sp.curves['Antenna'][1].setPen(QPen(Qt.red,1))

	def removeTabs(self):
		for n in range(len(self.sp)): self.removeTab(n)

# =============================================================================
class CentralWidget(QSplitter):
	def __init__(self,parent):
		QSplitter.__init__(self,parent)
		self.parent=parent
		self.setContentsMargins(10,10,10,10)
		self.setOrientation(Qt.Vertical)

#		# Spectrometers in tabs
		self.tabs=SpectrometerTabs(self,['AFFTS'])

		# Toolbar
		self.toolbar=ToolBar(parent.Icons)
		self.toolbar.setOrientation(Qt.Vertical)

		# Control panel (housekeeping)
		self.controlpanel=ControlPanel(self)

		# Status bar
		self.statusbar=QStatusBar()
		self.ActionIcon=QLabel(u"")
		self.ActionInfo=QLabel(u"")
		self.statusbar.addPermanentWidget(self.ActionIcon)
		self.statusbar.addPermanentWidget(self.ActionInfo,1)
		self.addWidget(self.tabs)

		Hsplit=QSplitter()
		Hsplit.setOrientation(Qt.Horizontal)
		Hsplit.addWidget(self.toolbar)
		Hsplit.addWidget(self.controlpanel)
		self.addWidget(Hsplit)

		self.addWidget(self.statusbar)

		self.setSizes([2000,1,1,1])

# =============================================================================
class MainWindow(QMainWindow):
	def __init__(self,TestGUI=True):
		QMainWindow.__init__(self)
		self.setup(TestGUI)

	# =======================================================================
	def setup(self,TestGUI):
		icondir=os.path.dirname(os.path.abspath("__file__"))+"/icons/"
		icons=[f for f in os.listdir(icondir) if f.find('.png')>-1]
		self.Icons={f[0:f.find('.png')]:QIcon(icondir+f) for f in icons}

		self.setWindowTitle('IRAM GUI')
		self.resize(QSize(1200,800))
		self.setWindowIcon(self.Icons['Jupiter'])

#		self.measurements=measurements(sweep=False)
		self.measurements=None

		self.mainwidget=CentralWidget(self)
		self.setCentralWidget(self.mainwidget)

		self.controlpanel=self.mainwidget.controlpanel
		self.HKvalues=self.controlpanel.HKvalues
		self.Controlvalues=self.controlpanel.Controlvalues
		self.statusbar=self.mainwidget.statusbar

		self.autoYlim=True

		self.TestGUI=TestGUI

		self.init=False
		self.running=False


		self.measureThread=measure(self)

		self.timer=QTimer()
		self.timer.timeout.connect(self.updateTimer)
		self.timer.start(100)

		self.time=localtime()

		self.closeEvent=self.closeApp

	# =======================================================================
	def closeApp(self,*arg):
		self.timer.stop()
		self.measureThread.close()

	def axisToggle(self):
		self.autoYlim=not self.autoYlim

	def resizeAxes(self):
		return self.autoYlim

	# =======================================================================
	def measureInitToggle(self):
		if self.running: self.init=True
		else: self.init=not self.init

		if not self.running and self.init: self.measureThread.do('init')
		else: self.measureThread.do('close')

		self.sender().setChecked(self.init)
		self.controlpanel.Controlvalues.setDisabled(self.init)

	# configure measurement object ==========================================
	def setMeasurement(self):
		self.Controlvalues.set()
		c=self.Controlvalues.dataset
		fnames=['e','a'][c.Format]
		form=lambda fnames: files.aform if fnames is 'a' else files.eform

		self.measurements=measurements(
#			spectrometers=[FW],spectrometer_hosts=['localhost'],
#			spectrometer_tcp_ports=[25144],spectrometer_udp_ports=[16210],
#			spectrometer_channels=[[8192, 8192]],
			formatnames=fnames,raw_formats=[form(f) for f in fnames],
			basename=c.Directory+('' if c.Directory[-1] is '/' else '/'),
			sweep=c.Sweep,
			full_file=c.NSpec,
			freq=c.Frequency,
			integration_time=int(c.IntegrationTime*1000),
			blank_time=c.BlankTime,
			)

	# =======================================================================
	def measureStartStop(self):
		if self.init: self.running=not self.running
		else: self.running=False
		self.sender().setChecked(self.running)

	# Save data dialog ======================================================
	def saveData(self,*arg):
		fname=QFileDialog.getSaveFileName(None,u"Save spectra",u"untitled.mat",u"MAT file (*.mat)")
		if len(fname)==0: return
#		self.SIR2.saveData(fname)

	# Set text information on the panel =====================================
	def setActionInfo(self,txt="",icon_name=None):
		if icon_name is not None:
			self.mainwidget.ActionIcon.setPixmap(self.Icons[icon_name].pixmap(QSize(16,16)))
		self.mainwidget.ActionInfo.setText(txt)
		self.statusbar.repaint()

	# Update HK (timer callback) ============================================
	def updateHK(self,*arg):
		hk=self.HKvalues

		hk.dataset.Band2=np.random.rand()
		hk.dataset.Band3=np.random.rand()
		hk.dataset.ColdLoad=np.random.rand()

		hk.get()

	# Timer callback function ===============================================
	def updateTimer(self):
		self.timer.stop()
		self.time=localtime()
		self.updateHK()

		if self.init: self.setActionInfo("Initialized","preview")
		else: self.setActionInfo("Stopped","stop1")

		if self.running:
			self.setActionInfo("Running","preview")
			x=np.array(range(100))*15-750.
			c=self.mainwidget.tabs.sp[0].curves
			for n in c:
				for m in c[n]: m.set_data(x,np.random.rand(100))
		else: self.setActionInfo("Stopped","stop1")

		self.timer.start()
# =============================================================================

if __name__=='__main__':
	# Show GUI ==============================================================
	TestGUI=True		# GUI in test mode
#	TestGUI=False		# GUI in measurement mode

	from guidata import qapplication
	app=qapplication()
	window=MainWindow(TestGUI=TestGUI)
	window.show()
	app.exec_()
