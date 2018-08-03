# -*- coding: utf-8 -*-
"""
Spectrometers plots widget

Last modification: 24.07.2018

Author: Borys Dabrowski
"""
# =============================================================================

# Imports and definitions =====================================================
from guidata.qt.QtGui import QSplitter,QPen,QTabWidget,QWidget,QVBoxLayout
from guidata.dataset.datatypes import DataSet
from guidata.dataset.dataitems import FloatItem,IntItem
from guidata.dataset.qtwidgets import DataSetEditGroupBox
from guidata.qt.QtCore import Qt

from guiqwt.curve import CurvePlot,CurveItem
from guiqwt.baseplot import BasePlot
from guiqwt.builder import make

import numpy as np
from scipy.signal import savgol_filter

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

#	def wheelEvent(self,evnt):
#		if self.isActive(): print(evnt)
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

# Spectrometer plots panel ====================================================
class SpectrometerPanel(QSplitter):
	"""Modified CurvePlot class (with mouse zoom and pan)

	.. note:: For more information about the QSplitter's methods and attributes used here, please refer to the `QSplitter documentation <http://pyqt.sourceforge.net/Docs/PyQt4/qsplitter.html>`_
	"""
	def __init__(self,parent,spec=None,
		plots=[
				[
					{'name':'Raw spectra','curves':['Cold','Hot','Antenna']},
					{'name':'System noise','curves':['Noise']}],
				[
					{'name':'Calibrated','curves':['Calibrated']},
					{'name':'Integrated','curves':['Integrated']}]
			]):
		QSplitter.__init__(self,parent)
		self.parent=parent
		self.spec=spec
		self.name=self.spec.name if self.spec else 'Spectrometer'

		self.plots=[p for c in plots for r in c for p in r['curves']]

		self.Pc=self.Ph=self.Pa=self.Ta=self.Ti=self.Tr=None
		self._mean={'count':0,'mean':0}
		self.chopper_pos=None

		self.active=None
		
		xlim=[0,40] if spec is None else spec.frequency
		self.axisLimits=xlim+[0,400]

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
		if isinstance(self.spec._channels,list): ch=self.spec._channels[0]
		else: ch=self.spec._channels
		idx=range(0,ch)
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
		self.sp=[SpectrometerPanel(self,spec=n) for n in self.spec]\
			if self.spec else [SpectrometerPanel(self)]

		for sp in self.sp:
			vBoxlayout=QVBoxLayout()
			vBoxlayout.addWidget(sp)
			tab=QWidget()
			tab.setLayout(vBoxlayout)
			self.addTab(tab,sp.name)

	def removeTabs(self):
		for n in enumerate(self.sp): self.removeTab(n[0])

	def refreshTabs(self,Tc=14,Th=300,order=['C0','A0','H0','A1'],m_count=0):
		for n in self.sp: n.refreshTab(Tc,Th,order,m_count)
# =============================================================================
