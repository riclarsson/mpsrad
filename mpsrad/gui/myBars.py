# -*- coding: utf-8 -*-
"""
Active status bar widget and toolbar widget with buttons

Last modification: 29.06.2018

Author: Borys Dabrowski
"""
# =============================================================================

# Imports and definitions =====================================================
from guidata.qt.QtGui import QLabel,QStatusBar,QToolBar,QToolButton
from guidata.qt.QtCore import QSize

import sys,io
# =============================================================================

# Modified status bar class ===================================================
class StatusBar(QStatusBar):
	"""Configuration of the status bar

	For more information about the QStatusBar' methods and attributes used here, please refer to the `QStatusBar documentation <http://pyqt.sourceforge.net/Docs/PyQt4/qstatusbar.html>`_
	"""
	def __init__(self,getIcon,*args,**kwargs):
		QStatusBar.__init__(self,*args,**kwargs)

		self.ActionIcon=QLabel(u"")
		self.ActionInfo=QLabel(u"")
		self.ActionInfo.setFixedWidth(200)
		self.StreamInfo=QLabel(u"")
		self.addPermanentWidget(self.ActionIcon)
		self.addPermanentWidget(self.ActionInfo)
		openIcon=QLabel(u"")
		openIcon.setPixmap(getIcon("arrow").pixmap(QSize(16,16)))
		self.addPermanentWidget(openIcon)
		self.addPermanentWidget(self.StreamInfo,1)

		self.getIcon=getIcon

		self._stdout=sys.stdout
		self._txtStream=io.StringIO()
		sys.stdout=self._txtStream

	def close(self):
		sys.stdout=self._stdout
		self._txtStream.close()
		QStatusBar.close(self)

	# set text information on the panel
	def setInfo(self,txt="",icon_name=None):
		if icon_name is not None:
			self.ActionIcon.setPixmap(self.getIcon(icon_name).pixmap(QSize(16,16)))
		self.ActionInfo.setText(txt)
		self.repaint()

	# display stream in the panel
	def refreshInfo(self):
		self._txtStream.seek(0)
		val=self._txtStream.getvalue()

		if len(val)==0: return
		self._txtStream.truncate(0)
		self._stdout.write(val)

		self.StreamInfo.setText(val.split('\n')[-2])
		self.repaint()
# =============================================================================

# Toolbar and buttons =========================================================
class ToolBar(QToolBar):
	"""Create the toolbar of the interface

	For more information about the QToolBar's methods and attributes used here, please refer to the `QtoolBar documentation <http://pyqt.sourceforge.net/Docs/PyQt4/qtoolbar.html>`_
	"""
	def __init__(self,getIcon,measureInitToggle,measureStartStop):
		QToolBar.__init__(self)

		self.resizeX=False
		self.resizeY=False

		ButtonAxisX=QToolButton()
		ButtonAxisX.setCheckable(True)
		ButtonAxisX.setChecked(True)
		ButtonAxisX.setIcon(getIcon("resizeX"))
		ButtonAxisX.setToolTip(u"Resize X axis")
		ButtonAxisX.released.connect(self.toggleX)

		ButtonAxisY=QToolButton()
		ButtonAxisY.setCheckable(True)
		ButtonAxisY.setChecked(True)
		ButtonAxisY.setIcon(getIcon("resizeY"))
		ButtonAxisY.setToolTip(u"Resize Y axis")
		ButtonAxisY.released.connect(self.toggleY)

		ButtonPrev=QToolButton()
		ButtonPrev.setCheckable(True)
		ButtonPrev.setChecked(False)
		ButtonPrev.setIcon(getIcon("init2"))
		ButtonPrev.setToolTip(u"Initialize")
		ButtonPrev.released.connect(measureInitToggle)

		ButtonMeas=QToolButton()
		ButtonMeas.setCheckable(True)
		ButtonMeas.setChecked(False)
		ButtonMeas.setIcon(getIcon("play"))
		ButtonMeas.setToolTip(u"Measure")
		ButtonMeas.released.connect(measureStartStop)

		self.addWidget(ButtonMeas)
		self.addWidget(ButtonPrev)
		self.addSeparator()
		self.addWidget(ButtonAxisX)
		self.addWidget(ButtonAxisY)

	def toggleX(self,*args):
		self.resizeX= not self.resizeX
	def toggleY(self,*args):
		self.resizeY= not self.resizeY

	def getX(self):
		return self.resizeX
	def getY(self):
		return self.resizeY
# =============================================================================
