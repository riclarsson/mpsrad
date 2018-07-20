# -*- coding: utf-8 -*-
"""
Last modification: 27.06.2018

Author: Borys Dabrowski
"""
# =============================================================================
import os
from guidata.qt.QtGui import QIcon

class myIcons():
	"""Icons collection
	"""
	def __init__(self,icondir=None):
		if icondir is None:
			icondir=os.path.dirname(__file__)+"/icons/"

		icons=[f for f in os.listdir(icondir) if f.find('.png')>-1]
		self._icons={f.replace('.png',''):QIcon(icondir+f) for f in icons}

	# get icon by name
	def getIcon(self,name):
		return self._icons[name]

	# get icons names
	def getNames(self):
		return self._icons.keys()
	
	# does icon exist
	def isIcon(self,name):
		return (name in self.getNames())
