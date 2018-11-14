# -*- coding: utf-8 -*-
"""
Spectrometers plots widget

Last modification: 08.11.2018

Author: Borys Dabrowski
"""
# =============================================================================

# Imports and definitions =====================================================
from guidata.qt.QtGui import QSplitter,QPen,QTabWidget,QWidget,QVBoxLayout,QColor
from guidata.dataset.datatypes import DataSet,BeginGroup,EndGroup #,BeginTabGroup,EndTabGroup
from guidata.dataset.dataitems import FloatItem,IntItem,StringItem,TextItem,ChoiceItem
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

#	def setDefaultAxisToCurveLimits(self):
#		xmin=xmax=ymin=ymax=np.nan
#		for n in self.curves:
#			(x,y)=self.curves[n].get_data()
#			if len(x)<2: return
#
#			xmin0,xmax0=np.nanmin(x),np.nanmax(x)
#			ymin0,ymax0=np.nanmin(y),np.nanmax(y)
#
#			xmin,xmax=np.nanmin([xmin,xmin0]),np.nanmax([xmax,xmax0])
#			ymin,ymax=np.nanmin([ymin,ymin0]),np.nanmax([ymax,ymax0])
#
#		self.setDefaultAxis(axis=[xmin,xmax,ymin,ymax])

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
		self.x=self.y=None

	def setplot(self,x,y,finite=True):
		self.x=x
		self.y=y
		if y is None: return
		try: yf=self.filterfun(y)
		except: yf=y

		min_y,max_y=min(yf),max(yf)
		dy=max_y-min_y
		self.setData(x,yf,finite=finite)

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

		self.Pc=self.Ph=self.Pa=self.Ta=self.Ti=self.Tri=self.Tr=None
		self._mean={'count':0,'mean':0,'noise':0}
		self.chopper_pos=None

		self.curves['Cold'].setPen(QPen(Qt.blue,1))
		self.curves['Hot'].setPen(QPen(Qt.red,1))

		self.curves['Calibrated'].parent.set_titles(ylabel=u'Temperature')
		self.curves['Integrated'].parent.set_titles(ylabel=u'Temperature')
		self.curves['Noise'].parent.set_titles(ylabel=u'Temperature')

		cPanel=self.curves['Cold'].parent
		cPanel.add_item(make.legend("BL"))
		cPanel.setActive()

	# Get vector of x values
	def getx(self):
		if self.spec is None: return None
		f0=self.spec.f0
		if f0 is None:
			df2=(self.axisLimits[1]-self.axisLimits[0])/2
			x=np.linspace(-df2,df2,len(self.Ta))
		else:
			x=np.linspace(self.axisLimits[0]-f0,self.axisLimits[1]-f0,len(self.Ta))
		return x

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

			# system noise temp
			y0=self.Ph/self.Pc
			y0[y0==1]=1.0001
			self.Tr=(Th-Tc*y0)/(y0-1)

			# integrated spectrum
			sc,self.Ti,self.Tri=self._mean['count']+1,self._mean['mean'],self._mean['noise']

			self.Ti=(self.Ti*(sc-1)+self.Ta)/sc
			self.Tri=(self.Tri*(sc-1)+self.Tr)/sc
			self.int_count=sc

			self._mean['count'],self._mean['mean'],self._mean['noise']=sc,self.Ti,self.Tri

		# update curves
		self.curves['Cold'].setplot(x,self.Pc)
		self.curves['Hot'].setplot(x,self.Ph)
		self.curves['Antenna'].setplot(x,self.Pa)
		self.curves['Calibrated'].setplot(x,self.Ta)
		self.curves['Integrated'].setplot(x,self.Ti)
		self.curves['Noise'].setplot(x,self.Tr)

# Summary plots panel =========================================================
class SummaryPanel(PlotPanel):
	def __init__(self,parent):
		tabs=parent.sp
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
			x=tab.getx()

			self.curves['Calibrated ' + self.names[n]].setplot(x,tab.Ta)
			self.curves['Calibrated ' + self.names[n]].setPen(self.colors[n%len(self.colors)])
			self.curves['Calibrated ' + self.names[n]].parent.set_titles(ylabel=u'Temperature')


			self.curves['Integrated ' + self.names[n]].setplot(x,tab.Ti)
			self.curves['Integrated ' + self.names[n]].setPen(self.colors[n%len(self.colors)])
			self.curves['Integrated ' + self.names[n]].parent.set_titles(ylabel=u'Temperature')

			self.curves['Noise ' + self.names[n]].setplot(x,tab.Tr)
			self.curves['Noise ' + self.names[n]].setPen(self.colors[n%len(self.colors)])
			self.curves['Noise ' + self.names[n]].parent.set_titles(ylabel=u'Temperature')

# Math panel ==================================================================
class MathPanel(PlotPanel):
	class cSet(DataSet):
		_bg1=BeginGroup("Source 1").set_pos(0)
		tab1=ChoiceItem("Tab",['a'])
		data1=ChoiceItem("Data",['a'])
		_eg1=EndGroup("")

		_bg2=BeginGroup("Source 2").set_pos(1)
		tab2=ChoiceItem("Tab",['a'])
		data2=ChoiceItem("Data",['a'])
		_eg2=EndGroup("")

		_bg3=BeginGroup("Operation").set_pos(2)
		function=ChoiceItem("Function",[('y1-y2','y1-y2'),('y1+y2','y1+y2'),
								('y1/y2','y1/y2'),('custom','f(x,y1,y2)')])
		custom=StringItem("f(x,y1,y2):")
		_eg3=EndGroup("")

		text=TextItem("").set_pos(3)


	def __init__(self,parent):
		plots=\
			[[
				{'name':'Source 1','curves':['in1']},
				{'name':'Source 2','curves':['in2']}],
			[
				{'name':'Result','curves':['out']},
			]]

		self.tabs=parent.sp

		df=[n.axisLimits[1]-n.axisLimits[0] for n in self.tabs]
		df2=max(df)/2

		axisLimits=[-df2,df2,
			min([n.axisLimits[2] for n in self.tabs]),
			max([n.axisLimits[3] for n in self.tabs])
			]

		PlotPanel.__init__(self,parent=parent,plots=plots,axisLimits=axisLimits)

		self._cBox=DataSetEditGroupBox("Control",self.cSet,show_button=False)
		self.addWidget(self._cBox)

		tabchoices=[(m,n.name,None) for m,n in enumerate(self.tabs)]
		curvechoices=[(n,n,None) for n in self.tabs[0].curves.keys()]

		self.cSet._items[1].set_prop('data', choices=tabchoices)
		self._cBox.dataset.tab1=0
		self.cSet._items[2].set_prop('data', choices=curvechoices)
		self._cBox.dataset.data1=curvechoices[0][0]
		self.cSet._items[5].set_prop('data', choices=tabchoices)
		self._cBox.dataset.tab2=0
		self.cSet._items[6].set_prop('data', choices=curvechoices)
		self._cBox.dataset.data2=curvechoices[0][0]
		self._cBox.get()

	def refreshTab(self):
		if self.curves is None: return
		self._cBox.set()
		d=self._cBox.dataset
		tab1,tab2=self.tabs[d.tab1],self.tabs[d.tab2]

		x1,y1=tab1.getx(),tab1.curves[d.data1].y
		x2,y2=tab2.getx(),tab2.curves[d.data2].y

		if x1 is None or x2 is None: return

		x_min=min(min(x1),min(x2))
		x_max=max(max(x1),max(x2))
		dx1=x1[1]-x1[0] if len(x1)>1 else 1e9
		dx2=x2[1]-x2[0] if len(x2)>1 else 1e9
		dx=min(dx1,dx2)

		x=np.arange(x_min,x_max,dx)
		y1=np.interp(x,x1,y1,left=0,right=0)
		y2=np.interp(x,x2,y2,left=0,right=0)

		fun=self._cBox.dataset.function
		if fun=='custom': fun=self._cBox.dataset.custom

		try: y=eval(fun)
		except: y=x*0.

		self.curves['in1'].setplot(x,y1)
		self.curves['in2'].setplot(x,y2)
		self.curves['out'].setplot(x,y)

# Retrieval panel =============================================================
class RetrievalPanel(PlotPanel):
	def __init__(self,parent):
		plots=\
			[[
				{'name':'Average Signal and Retrieved Signal','curves':['Data','Retrieval']},
				{'name':'Residual Signal','curves':['Residual']}],
			[
#				{'name':'Averaging kernel for OEM retrieval','curves':['Averaging']},
				{'name':'Measurement response to OEM retrieval','curves':['Response']}],
			[
				{'name':'Altitude vs. O3 VMR','curves':['Prior','OEM Retrieval']}],
			]

		PlotPanel.__init__(self,parent=parent,plots=plots) #,axisLimits=axisLimits)

		self.curves['Prior'].setPen(QPen(Qt.blue,1))
		self.curves['OEM Retrieval'].setPen(QPen(Qt.red,1))
		self.curves['Data'].setPen(QPen(Qt.blue,1))
		self.curves['Retrieval'].setPen(QPen(Qt.red,1))

		pDaRe=self.curves['Data'].parent
		pResi=self.curves['Residual'].parent
#		pAver=self.curves['Averaging'].parent
		pResp=self.curves['Response'].parent
		pPOEM=self.curves['Prior'].parent

		pPOEM.set_titles(ylabel='Altitude [m]',xlabel='O3 [ppmv]')
		pDaRe.set_titles(ylabel='Brightness Temperature [K]',xlabel='Frequency [GHz]')
		pResi.set_titles(ylabel='Residual [K]',xlabel='Frequency [GHz]')
#		pAver.set_titles(ylabel='Altitude [m]',xlabel='')
		pResp.set_titles(ylabel='Altitude [m]',xlabel='')

		pDaRe.add_item(make.legend("TR"))
		pDaRe.setActive()

		pPOEM.add_item(make.legend("TR"))
		pPOEM.setActive()

		pDaRe.setDefaultAxis(axis=[142.1,142.2,100.,200.])
		pResi.setDefaultAxis(axis=[142.1,142.2,-.5,.5])
#		pAver.setDefaultAxis(axis=[xmin,xmax,0.,1e5])
		pResp.setDefaultAxis(axis=[-.1,2.,0.,1e5])
		pPOEM.setDefaultAxis(axis=[-.1,12.,0.,1e5])

	def refreshTab(self,oem):
		Altitude=oem.arts.z_field.value.flatten()
		averaging_kernel=oem.arts.dxdy.value @ oem.arts.jacobian.value
		measurement_response=averaging_kernel @ np.ones(averaging_kernel.shape[1])

		self.curves['Data'].setplot(oem.fit_freq,oem.average_signal)
		self.curves['Retrieval'].setplot(oem.arts.f_grid.value/1e9,oem.arts.yf.value)

		self.curves['Prior'].setplot(10**oem.arts.xa.value[:-1]*1e6,Altitude)
		self.curves['OEM Retrieval'].setplot(10**oem.arts.x.value[:-1]*1e6,Altitude)

		self.curves['Residual'].setplot(oem.fit_freq,oem.average_signal-oem.arts.yf.value)

#		a=np.hstack([np.hstack([Altitude,np.nan]) for kernel in averaging_kernel.T])
#		k=np.hstack([np.hstack([kernel[:-1],np.nan]) for kernel in averaging_kernel.T])
#
#		self.curves['Averaging'].setplot(k,a,finite=False)

		self.curves['Response'].setplot(measurement_response[:-1],Altitude)

#		for n in self.curves: self.curves[n].parent.setDefaultAxisToCurveLimits()
















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

		# Spectrometer tabs
		for sp in self.sp:
			vBoxlayout=QVBoxLayout()
			vBoxlayout.addWidget(sp)
			tab=QWidget()
			tab.setLayout(vBoxlayout)
			self.addTab(tab,sp.name)

		# Summary tab
		tab=QWidget()
		vBoxlayout=QVBoxLayout()
		self.summary=SummaryPanel(self)
		vBoxlayout.addWidget(self.summary)
		tab.setLayout(vBoxlayout)
		self.addTab(tab,'Summary')

		# Math tab
		tab=QWidget()
		vBoxlayout=QVBoxLayout()
		self.math=MathPanel(self)
		vBoxlayout.addWidget(self.math)
		tab.setLayout(vBoxlayout)
		self.addTab(tab,'Math')

		# Retrieval tab
		tab=QWidget()
		vBoxlayout=QVBoxLayout()
		self.retrieval=RetrievalPanel(self)
		vBoxlayout.addWidget(self.retrieval)
		tab.setLayout(vBoxlayout)
		self.addTab(tab,'Retrieval')

	def removeTabs(self):
		for n in range(self.count()-1,-1,-1): self.removeTab(n)

	def refreshTabs(self,Tc=14,Th=300,order=['C0','A0','H0','A1'],m_count=0):
		for n in self.sp: n.refreshTab(Tc,Th,order,m_count)
		self.summary.refreshTab()
		self.math.refreshTab()
# =============================================================================
