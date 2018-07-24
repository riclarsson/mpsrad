from . import gui as guiIRAM

"""Here are the different functions to call all the GUI modules
"""

def start():
	"""Start function for IRAM  interface
	"""
	app,window=guiIRAM.begin()
	window.show()
	app.exec_()
