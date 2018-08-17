""" Settings for the radiometers all go here """

from mpsrad.backend import rcts104
from mpsrad import files

sweep=False
freq=214
freq_step=0.2
if_offset=6
sweep_step=10
full_file=10*56*5*4
repeat=True
wait=1
freq_range=(214, 270)
wobbler_device='/dev/ttyUSB1'
wobbler_address=b'0'
measurement_type='WVR'
wiltron68169B_address=5
chopper_device='/dev/ttyUSB0'
antenna_offset=1000
dbr_port=1080
dbr_server="dbr"
integration_time=5000
blank_time=5
mode="antenna"
basename='../data/'
raw_formats=[files.dform, files.dform]
formatnames=[ 'd', 'd']
spectrometer_channels=[[4096], [4096]]
spectrometers=[rcts104, rcts104]
spectrometer_freqs=[[[1330, 1370]], [[1330, 1370]]]
spectrometer_hosts=['waspam6', 'waspam3']
spectrometer_names=['40 MHz CTS - H', '40 MHz CTS - V']
spectrometer_tcp_ports=[1788, 1788]
spectrometer_udp_ports=[None, None]

