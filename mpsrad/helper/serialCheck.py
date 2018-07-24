import serial


def serialcheck():
	"""Function to check if we use pyserial and not serial
	"""
	try : 
		a=serial.Serial
		del(a)
	except :
		raise RuntimeError('Please install pyserial, not serial')
	
