import sys
import subprocess
import re
import setuptools

from codecs import open
from os.path import (abspath, dirname, join)

import builtins

builtins.__MPSRAD_SETUP__ = True

exec(open('mpsrad/version.py').read())

setuptools.setup(
	name = "mpsrad",
	version=__version__,

	author = "Borys Dabrowski",
	author_email = "dabrowski@mps.mpg.de",

	keywords = "atmospheric science",
	description = "MPS software to control radiometer",
	

	packages = setuptools.find_packages(),

	classifiers = [
		"Development Status :: Beta ",

		"Natural Language :: English",
		"Programming Language :: Python : : 3",
		
		"Intended Audience :: Science/Research",
		"Topic :: Scientific/Engineering ::Atmospheric Science",
		"license :: OSI Approved :: MIT License",
	],




	install_requires = [
		"datetime",
		"PyQt5",
		"files",
		"msgpack",
		"guidata",
		"PythonQwt",
		"pillow",
		"scipy",
		"numpy",
		"guiqwt",
		"matplotlib",		
		#"os",
		#"re",
		"pyserial",
		#"serial",
		#"socket",
		#"struct",
		#"threading",
		#"time",
	],

)
