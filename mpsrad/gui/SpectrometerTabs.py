# -*- coding: utf-8 -*-
"""
Spectrometers plots widget

Last modification: 07.08.2018

Author: Borys Dabrowski
"""
# =============================================================================

# Imports and definitions =====================================================
from guidata.qt.QtGui import QSplitter,QPen,QTabWidget,QWidget,QVBoxLayout,QColor
from guidata.dataset.datatypes import DataSet
from guidata.dataset.dataitems import FloatItem,IntItem
from guidata.dataset.qtwidgets import DataSetEditGroupBox
from guidata.qt.QtCore import Qt

from guiqwt.curve import CurvePlot,CurveItem
from guiqwt.baseplot import BasePlot
from guiqwt.builder import make

import numpy as np
from scipy.signal import savgol_filter

from matplotlib.pyplot import get_cmap

# Modified CurvePlot class (added mouse zoom and pan) =========================
class cPlot(CurvePlot):
	"""Curves plot configuration

	.. note:: For more information about the CurvePlot's methods and attributes used here, please refer to the `CurvePlot documentation <https://pythonhosted.org/guiqwt/reference/curve.html#guiqwt.curve.CurvePlot>`_
	"""
	def __init__(self,axis=None,updateWidgets=None,*args,**kwargs):
		CurvePlot.__init__(self,*args,**kwargs)
		self.axis=axis
		self.tmp_axis=None
		self.updateWidgets=updateWidgets

	def autoX(self):
		try: return self.parent().parent().parent().parent.autoX()
		except: return False

	def autoY(self):
		try: return self.parent().parent().parent().parent.autoY()
		except: return False

	def setDefaultAxis(self,axis=None):
		if axis is None: self.axis=self.getAxis()
		else: self.axis=axis
		self.setAxis()

	def getAxis(self):
		axis=list(self.get_axis_limits(BasePlot.X_BOTTOM)+self.get_axis_limits(BasePlot.Y_LEFT))
		return axis

	def setAxis(self,axis=None):
		if axis is None:
			axis=self.axis
			self.set_axis_limits(BasePlot.X_BOTTOM,axis[0],axis[1])
			self.set_axis_limits(BasePlot.Y_LEFT,axis[2],axis[3])
		else:
			if not self.autoX(): self.set_axis_limits(BasePlot.X_BOTTOM,axis[0],axis[1])
			if not self.autoY(): self.set_axis_limits(BasePlot.Y_LEFT,axis[2],axis[3])
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
			axis=[a+d for a,d in zip(axis,[-dX,-dX,dY,dY])]
		if self.button==2:		# zoom
			dX,dY=np.exp(dX),np.exp(dY)
			amX,amY=(axis[1]+axis[0])/2.,(axis[2]+axis[3])/2.
			axis=[(axis[0]-amX)*dX+amX,(axis[1]-amX)*dX+amX,
				(axis[2]-amY)*dY+amY,(axis[3]-amY)*dY+amY]

		dX,dY=axis[1]-axis[0],axis[3]-axis[2]
		r=lambda x,d: round(x,np.maximum(0,int(4-np.floor(np.log10(d)))))
		axis=[r(axis[0],dX),r(axis[1],dX),r(axis[2],dY),r(axis[3],dY)]

		self.setAxis(axis)

	def mouseReleaseEvent(self,evnt):
		if self.axis is None: return
		self.parent().parent().parent().evnt=evnt

	def mouseDoubleClickEvent(self,evnt):
		if self.axis is None: return
		self.setAxis()

	def wheelEvent(self,evnt):
		if self.axis is None: return
		self.setActive()
		axis=self.tmp_axis
		dy=evnt.angleDelta().y()
		
		scrolling_speed = 7  # percent
		if dy<0:
			d = 1 - scrolling_speed / 100
		elif dy>0:
			d = 1/(1 - scrolling_speed / 100)
		else: d=1
		dy = (axis[3]-axis[2]) * (1 - d)
		rel_y = evnt.y()/self.size().height()  # FIXME: This is not center of pointer...
		axis[2] += dy * (1 - rel_y)
		axis[3] -= dy * rel_y
		self.setAxis(axis)
# =============================================================================

# Modified CurveItem (added filter and autoscale) =============================
class cItem(CurveItem):
	"""
	.. note:: For more information about the CurveItem's methods and attributes used here, please refer to the `CurveItem documentation <https://pythonhosted.org/guiqwt/reference/curve.html#guiqwt.curve.CurveItem>`_
	"""
	def __init__(self,filterfun=lambda y: y,*args,**kwargs):
		CurveItem.__init__(self,*args,**kwargs)
		self.filterfun=filterfun

	def setplot(self,x,y):
		if y is None: return
		try: yf=self.filterfun(y)
		except: yf=y

		min_y,max_y=min(yf),max(yf)
		dy=max_y-min_y
		self.set_data(x,yf)

		try:
			if self.parent.autoY():
				self.parent.set_axis_limits(0,min_y-.1*dy,max_y+.1*dy)
			if self.parent.autoX():
				self.parent.set_axis_limits(2,x[0],x[-1])
		except: pass
# =============================================================================

# Filter widget ===============================================================
class FilterWidget(DataSetEditGroupBox):
	"""
	.. note:: For more information about the guidata.dataset.qtwidgets module used here, please refer to its `documentation <https://pythonhosted.org/guidata/_modules/guidata/dataset/qtwidgets.html>`_
	"""
	class params(DataSet):
		Order=IntItem("Order",default=1).set_pos(col=0)
		Window=IntItem("Window",default=1).set_pos(col=1)

	def __init__(self):
		DataSetEditGroupBox.__init__(self,None,self.params,show_button=False)

	def filterfun(self,y):
		self.set()
		window,order=self.dataset.Window,self.dataset.Order
		window+=(window%2==0)	# must be odd
		return savgol_filter(y,window,order)
# =============================================================================

# Set axis ranges widget ======================================================
class XYlim(DataSetEditGroupBox):
	"""
	.. note:: For more information about the guidata.dataset.qtwidgets module used here, please refer to its `documentation <https://pythonhosted.org/guidata/_modules/guidata/dataset/qtwidgets.html>`_
	"""
	class minmax(DataSet):
		Xmin=FloatItem("X min",default=1.,unit="").set_prop("display",format="%3.1f").set_pos(col=0)
		Xmax=FloatItem("X max",default=1.,unit="").set_prop("display",format="%3.1f").set_pos(col=1)
		Ymin=FloatItem("Y min",default=1.,unit="").set_prop("display",format="%3.1f").set_pos(col=3)
		Ymax=FloatItem("Y max",default=1.,unit="").set_prop("display",format="%3.1f").set_pos(col=4)
#			Yauto=ButtonItem("Y",None,icon=None,default=None,check=True).set_pos(col=5)

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
# =============================================================================

# Plot panel ==================================================================
class PlotPanel(QSplitter):
	def __init__(self,parent,axisLimits=None,
		plots=[[{'name':'P1','curves':['C1','C2']}]]):
		QSplitter.__init__(self,parent)
		self.parent=parent

		self.plots=[p for c in plots for r in c for p in r['curves']]
		self.active=None
		self.axisLimits=axisLimits

		self.xylim=XYlim()
		Filter=FilterWidget()

		# Curve panels (plots)
		Hsplit=QSplitter(self)
		self.curves=None
		self.panels=[]

		for columns in plots:
			column=QSplitter(self)
			column.setOrientation(Qt.Vertical)
			column.setChildrenCollapsible(False)

			for rows in columns:
				panel=cPlot(column,title=rows['name'],xlabel="\u0394f [MHz]",ylabel="Count",
					updateWidgets=self.xylim.updateWidgets)
				panel.name=rows['name']
				panel.setDefaultAxis(self.axisLimits)
				panel.curves={p:cItem(filterfun=Filter.filterfun) for p in rows['curves']}

				if self.curves is None: self.curves=panel.curves
				else: self.curves.update(panel.curves)

				for n in panel.curves:
					p=panel.curves[n]
					p.title().setText(n)
					p.set_data([0],[0])
					p.setPen(QPen(Qt.black,1))
					p.parent=panel
					panel.add_item(p)

				column.addWidget(panel)
				self.panels.append(panel)

			Hsplit.addWidget(column)

		self.addWidget(Hsplit)

		Hsplit=QSplitter(self)
		Hsplit.addWidget(self.xylim)
		Hsplit.addWidget(Filter)
		self.addWidget(Hsplit)
		self.setOrientation(Qt.Vertical)

# Spectrometer plots panel ====================================================
class SpectrometerPanel(PlotPanel):
	"""Modified CurvePlot class (with mouse zoom and pan)

	.. note:: For more information about the QSplitter's methods and attributes used here, please refer to the `QSplitter documentation <http://pyqt.sourceforge.net/Docs/PyQt4/qsplitter.html>`_
	"""
	def __init__(self,parent,spec=None, count=0,
		plots=[
				[
					{'name':'Raw spectra','curves':['Cold','Hot','Antenna']},
					{'name':'System noise','curves':['Noise']}],
				[
					{'name':'Calibrated','curves':['Calibrated']},
					{'name':'Integrated','curves':['Integrated']}]
			]):
		try: axisLimits=spec.frequency[count]+[0,400]
		except: axisLimits=[0,40,0,400]
		PlotPanel.__init__(self,parent=parent,plots=plots,axisLimits=axisLimits)
		self.spec=spec
		self.count = count
		self.name=self.spec.name if self.spec else 'Spectrometer'

		self.Pc=self.Ph=self.Pa=self.Ta=self.Ti=self.Tr=None
		self._mean={'count':0,'mean':0}
		self.chopper_pos=None

		self.curves['Cold'].setPen(QPen(Qt.blue,1))
		self.curves['Hot'].setPen(QPen(Qt.red,1))

		self.curves['Calibrated'].parent.set_titles(ylabel=u'Temperature')
		self.curves['Integrated'].parent.set_titles(ylabel=u'Temperature')
		self.curves['Noise'].parent.set_titles(ylabel=u'Temperature')

		cPanel=self.curves['Cold'].parent
		cPanel.add_item(make.legend("BL"))
		cPanel.setActive()

	def refreshTab(self,Tc,Th,order,chopper_pos):
		d=dict(zip(order,self.spec._data))
		if isinstance(self.spec._channels,list):
			st=int(np.sum(self.spec._channels[:self.count]))
			ch=self.spec._channels[self.count] + st
		else:
			ch=self.spec._channels
			st = 0
		idx=range(st,ch)
		x=np.linspace(self.axisLimits[0],self.axisLimits[1],len(idx))

		if not d[chopper_pos][idx].any(): return

		if chopper_pos in ['A0','A1']: self.Pa=d[chopper_pos][idx]
		elif chopper_pos=='C0': self.Pc=d[chopper_pos][idx]
		elif chopper_pos=='H0': self.Ph=d[chopper_pos][idx]

		# is it time to calculate calibrated and integrated spectra?
		if (chopper_pos in ['H0','C0']) and (chopper_pos != self.chopper_pos):
			self.chopper_pos=chopper_pos

			# calibrated spectrum
			idx=(self.Ph-self.Pc)==0
			self.Ta=(self.Pa-self.Pc)/(self.Ph-self.Pc)*(Th-Tc)+Tc
			self.Ta[idx]=0

			# integrated spectrum
			sc,self.Ti=self._mean['count']+1,self._mean['mean']
				
			self.Ti=(self.Ti*(sc-1)+self.Ta)/sc
			self._mean['count'],self._mean['mean']=sc,self.Ti

			# system noise temp
			y0=self.Ph/self.Pc
			y0[y0==1]=1.0001
			self.Tr=(Th-Tc*y0)/(y0-1)

		# update curves
		self.curves['Cold'].setplot(x,self.Pc)
		self.curves['Hot'].setplot(x,self.Ph)
		self.curves['Antenna'].setplot(x,self.Pa)
		self.curves['Calibrated'].setplot(x,self.Ta)
		self.curves['Integrated'].setplot(x,self.Ti)
		self.curves['Noise'].setplot(x,self.Tr)

# Summary plots panel =========================================================
class SummaryPanel(PlotPanel):
	def __init__(self,parent,tabs=[]):
		r=range(len(tabs))
		
		# Prepare unique names in ugly manner
		self.names = [n.spec.name for n in tabs] if tabs[0].spec is not None else ['']
		test = []
		for n in r:
			if self.names.count(self.names[n]) > 1 or self.names[n] in test:
				test.append(self.names[n])
				self.names[n] += ' {}'.format(test.count(self.names[n]))
		
		plots=[[
			{'name':'Calibrated','curves':['Calibrated ' + self.names[n] for n in r]},
			{'name':'Integrated','curves':['Integrated ' + self.names[n] for n in r]},
			{'name':'System noise','curves':['Noise ' + self.names[n] for n in r]},
			]]

		df=[n.axisLimits[1]-n.axisLimits[0] for n in tabs]
		df2=max(df)/2

		axisLimits=[-df2,df2,
			min([n.axisLimits[2] for n in tabs]),
			max([n.axisLimits[3] for n in tabs])
			]

		PlotPanel.__init__(self,parent=parent,plots=plots,axisLimits=axisLimits)
		self.tabs=tabs
		cmap=get_cmap('tab10',len(tabs))
		self.colors = [QPen(QColor(x[0]*255, x[1]*255, x[2]*255),1) for x in cmap.colors]
		
		cPanel=self.curves['Calibrated ' + self.names[0]].parent
		cPanel.add_item(make.legend("BL"))
		cPanel.setActive()
		cPanel=self.curves['Integrated ' + self.names[0]].parent
		cPanel.add_item(make.legend("BL"))
		cPanel.setActive()
		cPanel=self.curves['Noise ' + self.names[0]].parent
		cPanel.add_item(make.legend("BL"))
		cPanel.setActive()

	def refreshTab(self):
		if self.curves is None: return
		for n,tab in enumerate(self.tabs):

			f0=tab.spec.f0
			if f0 is None:
				df2=(tab.axisLimits[1]-tab.axisLimits[0])/2
				x=np.linspace(-df2,df2,len(tab.Ta))
			else:
				x=np.linspace(tab.axisLimits[0]-f0,tab.axisLimits[1]-f0,len(tab.Ta))

			self.curves['Calibrated ' + self.names[n]].setplot(x,tab.Ta)	
			self.curves['Calibrated ' + self.names[n]].setPen(self.colors[n%len(self.colors)])
			self.curves['Calibrated ' + self.names[n]].parent.set_titles(ylabel=u'Temperature')


			self.curves['Integrated ' + self.names[n]].setplot(x,tab.Ti)
			self.curves['Integrated ' + self.names[n]].setPen(self.colors[n%len(self.colors)])
			self.curves['Integrated ' + self.names[n]].parent.set_titles(ylabel=u'Temperature')

			self.curves['Noise ' + self.names[n]].setplot(x,tab.Tr)
			self.curves['Noise ' + self.names[n]].setPen(self.colors[n%len(self.colors)])
			self.curves['Noise ' + self.names[n]].parent.set_titles(ylabel=u'Temperature')

# Spectrometer panels in tabs =================================================
class SpectrometerTabs(QTabWidget):
	"""Tab of the interface to display the different curves

	.. note:: For more information about the QTabWidget's methods and attributes used here, please refer to the `QTabWidget documentation <http://pyqt.sourceforge.net/Docs/PyQt4/qtabwidget.html>`_
	"""
	def __init__(self,parent,spec=[],autoX=lambda:False,autoY=lambda:False):
		QTabWidget.__init__(self)
		self.parent=parent
		self.autoX=autoX
		self.autoY=autoY
		self.sp=[]
		self.spec=spec
		self.setTabs(self.spec)

	def setTabs(self,spec=[]):
		self.removeTabs()
		self.spec=spec
		if spec != []:
			self.sp = [SpectrometerPanel(self,spec=n, count=c) for n in self.spec for c in range(len(n.frequency))]
		else:
			self.sp = [SpectrometerPanel(self)]
			
		for sp in self.sp:
			vBoxlayout=QVBoxLayout()
			vBoxlayout.addWidget(sp)
			tab=QWidget()
			tab.setLayout(vBoxlayout)
			self.addTab(tab,sp.name)

		tab=QWidget()
		vBoxlayout=QVBoxLayout()
		self.summary=SummaryPanel(self,tabs=self.sp)
		vBoxlayout.addWidget(self.summary)
		tab.setLayout(vBoxlayout)
		self.addTab(tab,'Summary')

	def removeTabs(self):
		for n in range(len(self.sp)+1): self.removeTab(n)

	def refreshTabs(self,Tc=14,Th=300,order=['C0','A0','H0','A1'],m_count=0):
		for n in self.sp: n.refreshTab(Tc,Th,order,m_count)
		self.summary.refreshTab()
# =============================================================================
