# -*- coding: utf-8 -*-

"""
IRAM GUI

Last modification: 23.05.2019

Author: Borys Dabrowski
"""
# =============================================================================

# Imports and definitions =====================================================
from guidata.qt.QtGui import QMainWindow,QSplitter
from guidata.qt.QtCore import Qt,QSize,QTimer

from time import localtime

from mpsrad.gui.myIcons import myIcons
from mpsrad.gui.RetrievalTabs import oemWidget
from mpsrad.gui.SpectrometerTabs import SpectrometerTabs
from mpsrad.gui.HK_control_WVR import HKwidget,Controlwidget
from mpsrad.gui.myBars import StatusBar,ToolBar

from mpsrad.measurements import measurements
from mpsrad.measureThread import measure, measure2

from mpsrad.dummy_hardware import dummy_hardware
# =============================================================================

# Central widget (layout) =====================================================
class CentralWidget(QSplitter):
	"""Main construction of the interface

	.. note:: For more information about the QSplitter's methods and attributes used here, please refer to the `QSplitter documentation <http://pyqt.sourceforge.net/Docs/PyQt4/qsplitter.html>`_
	"""
	def __init__(self,parent):
		QSplitter.__init__(self,parent)
		self.parent=parent
		self.setContentsMargins(10,10,10,10)
		self.setOrientation(Qt.Vertical)

		# Toolbar
		toolbar=ToolBar(parent.getIcon,parent.measureInitToggle,parent.measureStartStop,parent=self)
		toolbar.setOrientation(Qt.Vertical)

		# Spectrometers in tabs
		self.tabs=SpectrometerTabs(self,autoX=toolbar.getX,autoY=toolbar.getY)

		# Control panel (housekeeping + control)
		controlpanel=QSplitter()
		self.Controlvalues=Controlwidget()
		self.HKvalues=HKwidget(controlValues=self.Controlvalues)
		controlpanel.addWidget(self.Controlvalues)
		controlpanel.addWidget(self.HKvalues)
		controlpanel.setSizes([2000,1])

		self.sBar=StatusBar(parent.getIcon)

		self.addWidget(self.tabs)

		Hsplit=QSplitter()
		Hsplit.setOrientation(Qt.Horizontal)
		Hsplit.addWidget(toolbar)
		Hsplit.addWidget(controlpanel)
		self.addWidget(Hsplit)

		self.addWidget(self.sBar)

		self.setSizes([2000,1,1,1])
# =============================================================================

# =============================================================================
class MainWindow(QMainWindow):
	"""Launch the setup and display the interface window

	.. note:: For more information about the QMainWindow's methods and attributes used here, please refer to the `QMainWindow documentation <http://pyqt.sourceforge.net/Docs/PyQt4/qmainwindow.html>`_
	"""
	def __init__(self):
		QMainWindow.__init__(self)

		icons=myIcons()
		self.getIcon=icons.getIcon

		self.setWindowTitle('WVR GUI')
		self.resize(QSize(1200,800))
		self.setWindowIcon(self.getIcon('spectrum'))

		self.measurements=None

		self.centralwidget=CentralWidget(self)
		self.oem = oemWidget(self.centralwidget.tabs, [21, 23])
		self.setCentralWidget(self.centralwidget)

		self.HKvalues=self.centralwidget.HKvalues
		self.Controlvalues=self.centralwidget.Controlvalues
		self.sBar=self.centralwidget.sBar

		self.init=False
		self.running=False

		self.oeminit=False
		self.oemrunning=False

		self.oemThread=measure2(self.oem)
		self.measureThread=measure(self)

		self.timer=QTimer()
		self.timer.timeout.connect(self.updateTimer)
		self.timer.start(200)

		self.time=localtime()

		self.closeEvent=self.closeApp

		self._Tc=0
		self._Th=0

	def closeApp(self,*arg):
		self.sBar.close()
		self.timer.stop()
		self.measureThread.close()
		self.oemThread.close()
		self.HKvalues.close()

	# configure measurement object
	def setMeasurement(self):
		c=self.Controlvalues.getControls()
#		form={'a':files.aform,'e':files.eform}

		self.measurements=measurements(
#			spectrometers=[FW],spectrometer_hosts=['localhost'],
#			spectrometer_tcp_ports=[25144],spectrometer_udp_ports=[16210],
#			spectrometer_channels=[[8192,8192]],
#			formatnames=c.Format,raw_formats=[form[f] for f in c.Format],
			basename=c.Directory+('' if c.Directory[-1] is '/' else '/'),
#			sweep=c.Sweep,
			full_file=c.NSpec,
			freq=c.Frequency,
			integration_time=int(c.IntegrationTime*1000.),
			blank_time=c.BlankTime,
			antenna_offset=c.Antenna
			)

		self.HKvalues.measurements=self.measurements

	# init/deinit measurement
	def measureInitToggle(self):
		if self.running: self.init=True
		else: self.init=not self.init

		if not self.running and self.init: self.measureThread.do('init')
		else: self.measureThread.do('close')

		self.sender().setChecked(self.init)
		self.Controlvalues.setDisabled(self.init)
#
		if self.oemrunning: self.oeminit=True
		else: self.oeminit=not self.oeminit
		if not self.oemrunning and self.oeminit: self.oemThread.do('init')
		else: self.oemThread.do('close')

	# start/stop measurement
	def measureStartStop(self):
		if self.init: self.running=not self.running
		else: self.running=False

		if self.running: self.measureThread.do('run')
		else: self.measureThread.do(None)

		self.sender().setChecked(self.running)

		if self.oeminit: self.oemrunning=not self.oemrunning
		else: self.oemrunning=False
		if self.oemrunning: self.oemThread.do('run')
		else: self.oemThread.do(None)

	# timer callback function
	def updateTimer(self):
		self.timer.stop()
		self.time=localtime()

		#self.HKvalues.updateHK()
		if (self.measurements is not None) and ('multimeter' in self.measurements.__dict__):
			sensors=self.measurements.multimeter.getSensors()
			self.HKvalues.updateHK(sensors)
		elif self.measurements is not None:
			sensors=self.measurements.multimeter.getSensors()
			self.HKvalues.updateHK(sensors)

		if self.init: self.sBar.setInfo("Initialized","preview")
		else: self.sBar.setInfo("Stopped","stop1")

		if self.measurements is not None:
			spec,tabs=self.measurements.spec,self.centralwidget.tabs
			if tabs.spec!=spec:
				tabs.removeTabs()
				tabs.setTabs(spec)

		if self.running:
			self.sBar.setInfo("Running","preview")

			try:
				order=self.measurements.get_order()
				order=[order[k]+str(order[0:k].count(w)) for k,w in enumerate(order)]
				if len(self.measurements._housekeeping)>0:
					chopper_pos=order[len(self.measurements._housekeeping)-1]
#					Tc,Th=self.measurements.multimeter.getSensors()[1:3]

					Tc=self.measurements._housekeeping[-1][2]
					Th=self.measurements._housekeeping[-1][3]
					if Tc!=0: self._Tc=Tc
					if Th!=0: self._Th=Th
					Tc = self._Tc
					Th = self._Th

#					Tc,Th=21.,295.
					Tc=63.9
					Th=119.2

					self.centralwidget.tabs.refreshTabs(Tc,Th,order,chopper_pos)
			except: pass

		else: self.sBar.setInfo("Stopped","stop1")

		self.sBar.refreshInfo()

		self.timer.start()

# Show GUI ==============================================================
from guidata import qapplication
#
window=''

def begin():
	app=qapplication()
	global window
	window=MainWindow()
	window.showMaximized()
	print('ok')
	return(app,window)
#
## =============================================================================
#if __name__=='__main__':
#	start()

if __name__=='__main__':  # NOTE: No interaction with "window" possible, so no reset-button
	# Show GUI ==============================================================
#	from guidata import qapplication
	app=qapplication()
	window=MainWindow()
	window.show()
	window.showMaximized()
	app.exec_()
