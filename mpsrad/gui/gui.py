# -*- coding: utf-8 -*-
# IRAM GUI
# Author: Borys Dabrowski, dabrowski@mps.mpg.de
# Last modification: 18.06.2018
# =============================================================================

# Imports and definitions =====================================================
from guidata.qt.QtGui import QMainWindow,QSplitter,QPen,QIcon,\
	QLabel,QToolBar,QToolButton,QStatusBar,QTabWidget,QWidget,QVBoxLayout
from guidata.qt.QtCore import Qt,QSize,QTimer
from guidata.dataset.datatypes import DataSet,BeginGroup,EndGroup
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

from mpsrad.measurements import measurements
from mpsrad.frontend.dbr import dbr
from mpsrad.housekeeping.sensors import sensors
from mpsrad.chopper.chopper import chopper
import mpsrad.files as files

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
				self.measurements.init()
				self.cmd=None

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

# Main window GUI =============================================================

# Tollbar with buttons ========================================================
class ToolBar(QToolBar):
	def __init__(self,Icons):
		QToolBar.__init__(self)
		global window

		ButtonAxis=QToolButton()
		ButtonAxis.setCheckable(True)
		ButtonAxis.setChecked(True)
		ButtonAxis.setIcon(Icons["resize"])
		ButtonAxis.setToolTip(u"Resize axes")
		ButtonAxis.released.connect(lambda *args:window.axisToggle())

		ButtonPrev=QToolButton()
		ButtonPrev.setCheckable(True)
		ButtonPrev.setChecked(False)
		ButtonPrev.setIcon(Icons["eye"])
		ButtonPrev.setToolTip(u"Initialize")
		ButtonPrev.released.connect(lambda *args:window.measureInitToggle())


		ButtonMeas=QToolButton()
		ButtonMeas.setCheckable(True)
		ButtonMeas.setChecked(False)
		ButtonMeas.setIcon(Icons["camera"])
		ButtonMeas.setToolTip(u"Measure")
		ButtonMeas.released.connect(lambda *args:window.measureStartStop())

		self.addWidget(ButtonMeas)
		self.addWidget(ButtonPrev)
		self.addWidget(ButtonAxis)
#		self.addSeparator()

# Housekeeping widget =========================================================
class HKwidget(DataSet):
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

# Control widget ==============================================================
class Controlwidget(DataSet):
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

		def isActive(self):
			return self.frameStyle()==1

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

#		def wheelEvent(self,evnt):
#			if self.isActive(): print(evnt)

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

	def __init__(self,parent,name='Panel',axisLimits=[-750,750,0,1],
		plots=[
				[
					{'name':'Cold/Hot','curves':['Cold','Hot']},
					{'name':'Antenna','curves':['Antenna 1','Antenna 2']}],
				[
					{'name':'Calibrated','curves':['Calibrated 1','Calibrated 2']},
					{'name':'Integrated','curves':['Integrated']}]
			]):
		QSplitter.__init__(self,parent)
		self.parent=parent
		self.name=name

		self.plots=[p for c in plots for r in c for p in r['curves']]

		self.active=None
		self.axisLimits=axisLimits

		self.xylim=self.XYlim()

		# Curve panels (plots)
		Hsplit=QSplitter(self)
		self.curves=None

		for columns in plots:
			column=QSplitter(self)
			column.setOrientation(Qt.Vertical)
			column.setChildrenCollapsible(False)

			for rows in columns:
				panel=self.cplot(column,title=rows['name'],xlabel=u"\u0394f [MHz]",
					ylabel="Count",updateWidgets=self.xylim.updateWidgets)
				panel.name=rows['name']
				panel.setDefaultAxis(self.axisLimits)
				panel.curves={p:CurveItem(CurveParam()) for p in rows['curves']}

				if self.curves is None: self.curves=panel.curves
				else: self.curves.update(panel.curves)

				for n in panel.curves:
					p=panel.curves[n]
					p.set_data([0],[0])
					p.setPen(QPen(Qt.black,1))
					p.parent=panel
					panel.add_item(p)

				column.addWidget(panel)

			Hsplit.addWidget(column)

		self.addWidget(Hsplit)
		self.addWidget(self.xylim)
		self.setOrientation(Qt.Vertical)

		panel.setActive()


# Spectrometer panels in tabs =================================================
class SpectrometerTabs(QTabWidget):
	def __init__(self,parent,spec_names=[]):
		QTabWidget.__init__(self)
		self.parent=parent
		self.setTabs(spec_names)

	def setTabs(self,spec_names=[]):
		self.names=spec_names
		self.sp=[SpectrometerPanel(self.parent,name=name) for name in spec_names]

		for sp in self.sp:
			vBoxlayout=QVBoxLayout()
			vBoxlayout.addWidget(sp)
			tab=QWidget()
			tab.setLayout(vBoxlayout)
			self.addTab(tab,sp.name)

			sp.curves['Cold'].setPen(QPen(Qt.blue,1))
			sp.curves['Hot'].setPen(QPen(Qt.red,1))
			sp.curves['Antenna 1'].setPen(QPen(Qt.blue,1))
			sp.curves['Antenna 2'].setPen(QPen(Qt.red,1))
			sp.curves['Calibrated 1'].setPen(QPen(Qt.blue,1))
			sp.curves['Calibrated 2'].setPen(QPen(Qt.red,1))

			sp.curves['Calibrated 2'].parent.set_titles(ylabel=u'Temperature')

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
		self.tabs=SpectrometerTabs(self,['Spectrometer'])

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
		__guidir__=os.getcwd()
		icondir=__guidir__+"mpsrad/gui//icons/"
		Hsplit.addWidget(self.toolbar)
		Hsplit.addWidget(self.controlpanel)
		self.addWidget(Hsplit)

		self.addWidget(self.statusbar)

		self.setSizes([2000,1,1,1])

# =============================================================================
class MainWindow(QMainWindow):
	def __init__(self):
		QMainWindow.__init__(self)
		self.setup()

	# =======================================================================
	def setup(self):
		icondir=os.path.dirname(__file__)+"/icons/"
		icons=[f for f in os.listdir(icondir) if f.find('.png')>-1]
		self.Icons={f[0:f.find('.png')]:QIcon(icondir+f) for f in icons}

		self.setWindowTitle('IRAM GUI')
		self.resize(QSize(1200,800))
		self.setWindowIcon(self.Icons['Jupiter'])

		self.measurements=None

		self.mainwidget=CentralWidget(self)
		self.setCentralWidget(self.mainwidget)

		self.controlpanel=self.mainwidget.controlpanel
		self.HKvalues=self.controlpanel.HKvalues
		self.Controlvalues=self.controlpanel.Controlvalues
		self.statusbar=self.mainwidget.statusbar

		self.autoYlim=True

		self.init=False
		self.running=False

		self.dbr=dbr()
		self.dbr.init()
		self.sensors=sensors()
		self.sensors.init()
		self.chopper=chopper()
		self.chopper.init()

		self.measureThread=measure(self)

		self.timer=QTimer()
		self.timer.timeout.connect(self.updateTimer)
		self.timer.start(200)

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
		form={'a':files.aform,'e':files.eform}

		self.measurements=measurements(
#			spectrometers=[FW],spectrometer_hosts=['localhost'],
#			spectrometer_tcp_ports=[25144],spectrometer_udp_ports=[16210],
#			spectrometer_channels=[[8192,8192]],
#			formatnames=c.Format,raw_formats=[form[f] for f in c.Format],
			basename=c.Directory+('' if c.Directory[-1] is '/' else '/'),
			sweep=c.Sweep,
			full_file=c.NSpec,
			freq=c.Frequency,
			integration_time=int(c.IntegrationTime*1000),
			blank_time=c.BlankTime,
			antenna_offset=c.Antenna
			)

	# =======================================================================
	def measureStartStop(self):
		if self.init: self.running=not self.running
		else: self.running=False
		
		if self.running: self.measureThread.do('run')
		else: self.measureThread.do(None)

		self.sender().setChecked(self.running)

	# Set text information on the panel =====================================
	def setActionInfo(self,txt="",icon_name=None):
		if icon_name is not None:
			self.mainwidget.ActionIcon.setPixmap(self.Icons[icon_name].pixmap(QSize(16,16)))
		self.mainwidget.ActionInfo.setText(txt)
		self.statusbar.repaint()

	# Update HK (timer callback) ============================================
	def updateHK(self,*arg):
		hk,c=self.HKvalues,self.Controlvalues

		band=[2,3][c.dataset.Frequency>dbr.band2limits[1]]
		c.setTitle("Control panel, Band %i"%band)

		status=self.dbr.get_status()
		val=lambda name: [n['value'] for n in status if n['name']==name][0]

		hk.dataset.ColdLoad=val('cryo.ColdLd.val')
		hk.dataset.Band2=val('cryo.Band2.val')
		hk.dataset.Band3=val('cryo.Band3.val')
		hk.dataset.T_77K=val('cryo.T_77K.val')
		hk.dataset.T_15K=val('cryo.T_15K.val')
		hk.dataset.T_04K=val('cryo.T_04K.val')

		hk.dataset.GunnBias=val('B%i.dac_GUNN_BIAS.act.val'%band)
		hk.dataset.LoopGain=val('B%i.dac_LOOP_GAIN.act.val'%band)
		hk.dataset.HmxBias=val('B%i.dac_HMX_BIAS.act.val'%band)
		hk.dataset.OffsetVolt=val('B%i.adc_OFFSET_VOLT.act.val'%band)
		hk.dataset.PLLIFLevel=val('B%i.adc_PLL_IF_LEVEL.act.val'%band)
		hk.dataset.HmxCurrent=val('B%i.adc_HMX_CURRENT.act.val'%band)
		
		try:
			hkvals=self.measurements._housekeeping[-1]
			if hkvals[1]!=0: hk.dataset.RoomTemp=hkvals[1]	# room temperature K
			if hkvals[2]!=0: hk.dataset.OutsideTemp=hkvals[2]	# outside temperature K
			if hkvals[3]!=0: hk.dataset.Humidity=hkvals[3]	# humidity %

			if hkvals[4]!=0: c.dataset.Chopper=chr(int(hkvals[4]))
#			c.get()
		except: pass

		c.set()
		hk.get()

	# Timer callback function ===============================================
	def updateTimer(self):
		self.timer.stop()
		self.time=localtime()
		self.updateHK()

		if self.init: self.setActionInfo("Initialized","preview")
		else: self.setActionInfo("Stopped","stop1")

		if self.measurements is not None:
			names=[n.name for n in self.measurements.spec]
			tabs=self.mainwidget.tabs
			if tabs.names!=names:
				tabs.removeTabs()
				tabs.setTabs(names)

		if self.running:
			self.setActionInfo("Running","preview")

			try:
				order=self.measurements.get_order()
				order=[order[k]+str(order[0:k].count(w)) for k,w in enumerate(order)]

				for tab,spec in zip(self.mainwidget.tabs.sp,se
					Ta1=(Pa1-Pc)/(Ph-Pc)*(Th-Tc)+Tc
					Ta2=(Pa2-Pc)/(Ph-Pc)*(Th-Tc)+Tc
					Ta1[idx],Ta2[idx]=0,0lf.measurements.spec):
					d=dict(zip(order,spec._data))
					if isinstance(spec._channels,list): ch=spec._channels[0]
					else: ch=spec._channels
					idx=range(16,ch)

					Tc,Th=21.,295.
					Pc,Ph,Pa1,Pa2=d['C0'][idx],d['H0'][idx],d['A0'][idx],d['A1'][idx]
					idx=(Ph-Pc)==0
					Ta1=(Pa1-Pc)/(Ph-Pc)*(Th-Tc)+Tc
					Ta2=(Pa2-Pc)/(Ph-Pc)*(Th-Tc)+Tc
					Ta1[idx],Ta2[idx]=0,0

					def setplot(name,x,y,min_y=0,max_y=None):
						if max_y is None: max_y=max(y)
						curve=tab.curves[name]
						curve.set_data(x,y)

						if self.autoYlim:
							curve.parent.set_axis_limits(0,min_y,max_y)
							curve.parent.set_axis_limits(2,x[0],x[-1])

					# update curves
					x=np.linspace(0,1500,len(Pc))
					setplot('Cold',x,Pc)
					setplot('Hot',x,Ph)
					setplot('Antenna 1',x,Pa1)
					setplot('Antenna 2',x,Pa2)
					setplot('Calibrated 1',x,Ta1)
					setplot('Calibrated 2',x,Ta2,max_y=300,min_y=200)
#						min_y=min(min(Ta1),min(Ta2)) if self.autoYlim else 0)

					y0=Ph/Pc
					y0[y0==1]=1.0001
					Tr=(Th-Tc*y0)/(y0-1)
					setplot('Integrated',x,Tr)

			except: pass

		else: self.setActionInfo("Stopped","stop1")

		self.timer.start()

# Show GUI =====================================================================
from guidata import qapplication

window=''

def begin():
	app=qapplication()
	global window
	window=MainWindow()
	print('ok')
	return(app,window)


def start():
	app,window=begin()
	window.show()
	app.exec_()

# ==============================================================================

if __name__='__main__':
	start()
