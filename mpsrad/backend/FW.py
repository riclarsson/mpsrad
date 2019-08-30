#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Thu Nov 16 11:24:10 2017

Author: Richard Larsson

Connection to fast fourier transform spectrometer
"""

import socket
import struct
import numpy as np
from time import sleep


class FW:
    """Connection to fast fourier transform spectrometer
    """
    def __init__(self,
            library=None,
            name='AFFTS',
            frequency=[[0,1500]],
            f0=None,
            host='localhost',
            tcp_port=25144,
            udp_port=16210,
            channels=np.array([8192,8192]),
            integration_time=1000,
            blank_time=1,
            data_storage_containers=4,
            reverse_data=False):
        """
        Parameters:
            host (str):
                Name of the host, IP or DNS
            tcp_port (str):
                First port to communicate with the FW spectrometer
            udp_port (str):
                Second port to communicate with the FW spectrometer
            channels (array of int):
                Numbers of channel to **info**
            name (any):
                Name of the mahcine (unused, kept as housekeeping)
            integration_time (int):
                **info**
            blank_time (int):
                **info**
            data_storage_containers (int):
                **info**
        """
        assert isinstance(integration_time,int),"Integration in integers"
        assert integration_time < 5001,"5000 ms integration time is maximum"

        self.name=name
        self.f0=f0

        self._bytes=np.sum(channels)*4
        self._boards=len(channels)
        self._channels=channels
        self._tcp_port=tcp_port
        self._udp_port=udp_port
        self._host=host
        self._integration_time=str(int(integration_time//2 * 1000))
        self._blank_time=str(int(blank_time * 1000))
        self._copies_of_vectors=int(data_storage_containers)
        self.frequency = frequency
        self.reverse=reverse_data

        self._initialized=False
        self._sent=False

    def init(self):
        """Connects to the machine and initialized how it will be run

        Musn't be initialized already
        """
        assert not self._initialized,"Cannot init initialized FFTS"


        self._tcp_sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self._ip=socket.gethostbyname(self._host)
        self._tcp_sock.connect((self._ip,self._tcp_port))

        self._udp_sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self._udp_addr=(self._ip,self._udp_port)
        self._udp_sock.sendto(b'AFFTS:cmdMode INTERNAL ',self._udp_addr)
        sleep(0.1)

        self._set_integration_time(self._integration_time)
        sleep(0.1)
        self._set_blank_time(self._blank_time)
        sleep(0.1)
        s=''
        for i in range(len(self._channels)):
            s += '1 '
            self._udp_sock.sendto(('AFFTS:Band'+str(i+1)+':cmdNumspecchan '
                + str(self._channels[i]) +
                ' ').encode("ascii"),self._udp_addr)
            if self.frequency[i][0]:
                raise RuntimeError("Must have 0 starting bandwidth")
            self._udp_sock.sendto(('AFFTS:Band'+str(i+1)+':cmdBandWidth '
                + str(self.frequency[i][1]) +
                ' MHz ').encode("ascii"),self._udp_addr)
            sleep(0.1)
        self._udp_sock.sendto(('AFFTS:cmdUsedsections '+s).encode("ascii"),
            self._udp_addr)
        sleep(0.1)
        self._udp_sock.sendto(b'AFFTS:configure ',self._udp_addr)
        sleep(0.3)
        self._udp_sock.sendto(b'AFFTS:calADC ',self._udp_addr)
        self._initialized=True
        self._sent=False
        self._data=[]
#            for i in range(self._copies_of_vectors):
#                self._data.append(np.array([]))
        for i in range(self._copies_of_vectors):
            self._data.append(np.zeros((self._channels[0]), dtype=np.float64))
        sleep(3.0)


    def _set_integration_time(self,time):
        t=str(time)+' '
        self._udp_sock.sendto(('AFFTS:cmdSynctime '+t).encode("ascii"),
            self._udp_addr)

    def _set_blank_time(self,time):
        t=str(time)+' '
        self._udp_sock.sendto(('AFFTS:cmdBlanktime '+t).encode("ascii"),
            self._udp_addr)

    def run(self):
        """Runs the machine and fills requested channel

        Must be initialized already and not have data not download.
        """
        assert self._initialized,"Cannot run uninitialized FFTS"
        assert not self._sent,"Cannot resend data,download first"
        self._udp_sock.sendto(b'AFFTS:dump 2 ',self._udp_addr)
        self._sent=True

    def get_data(self,i=0):
        """
        Must be initialized already and have data

        Parameter:
            i (int):
                index of **what**
        """
        assert self._initialized,"Cannot run uninitialized FFTS"
        assert i < self._copies_of_vectors and i > -1,"Bad index"
        assert self._sent,"Cannot download data before running machine"

        header=self._tcp_sock.recv(64,socket.MSG_WAITALL)
        h=struct.unpack('4s4sI8s28s4I',header)
        if h[2] > 64:
            d=self._tcp_sock.recv(h[2]-64,socket.MSG_WAITALL)
            #d=struct.unpack(str((h[2]-64)//4)+'f',d)
            #self._data[i]=np.array(d,dtype=np.float32)
            #self._time=h[4].decode('utf8').strip()

        header=self._tcp_sock.recv(64,socket.MSG_WAITALL)
        h=struct.unpack('4s4sI8s28s4I',header)
        if h[2] > 64:
            d=self._tcp_sock.recv(h[2]-64,socket.MSG_WAITALL)
            d=struct.unpack(str((h[2]-64)//4)+'f',d)
            self._data[i]=np.array(d,dtype=np.float32)
            self._time=h[4].decode('utf8').strip()
        self._sent=False

        if self.reverse:
            self._data[i] = self._data[i][::-1]

    def save_data(self,basename="/home/waspam/data/test/FW",binary=True):
        """Saves data to file at basename+filename.

        Uses last access-time to server socket as filename.

        Saves with numpy binary format if binary is true or as ascii otherwise.
        """
        assert self._initialized,"No data exists for an uninitialized FFTS"
        assert len(self._time),"Must call run() succesfully to save data"

        filename=self._time

        if binary: np.save(basename+filename,self._data)
        else: np.savetxt(basename+filename,self._data)

        self._time=''

    def set_housekeeping(self, hk):
        """ Sets the housekeeping data dictionary.  hk must be dictionary """
        assert self._initialized, "Can set housekeeping when initialized"

        hk['Instrument'][self.name] = {}
        hk['Instrument'][self.name]['Frequency [MHz]'] = self.frequency
        hk['Instrument'][self.name]['Channels [#]'] = self._channels
        hk['Instrument'][self.name]['Integration [micro-s]'] = self._integration_time

    def close(self):
        """Disconnect from both servers of the AFFTS and sends stop to AFFTS

        Must be initialized to be closed.
        """
        assert self._initialized,"Cannot close uninitialized FFTS"

        self._tcp_sock.close()
        self._udp_sock.sendto(b'AFFTS:stop ',self._udp_addr)
        self._udp_sock.close()
        self._initialized=False


class affts_commands:
    def __init__(self, host='localhost', port=16210):
        
        self._port = port
        self._host = host
        self._ip=socket.gethostbyname(self._host)
        self._sock=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._addr=(self._ip, self._port)
        self.send('cmdMode INTERNAL')
        
    def send(self, info, ZzZ=0.1):
        self._sock.sendto(b'AFFTS:' + info.encode('ascii') + b' ', self._addr)
        sleep(ZzZ)
        
    def configure(self):
        self.send('configure', 0.3)
        
    def calibrate(self):
        self.send('calADC')
        
    def set_channels(self, num_boards=2, num_channels=8192):
        assert num_boards > 0, 'must have boards'
        assert num_channels > 0, 'must have channels'
        
        s=' '
        for i in range(num_boards):
            s += '1 '
            self.send('Band{}:cmdNumspecchan {}'.format(i+1, num_channels))
        self.send('cmdUsedsections' + s)
        
    def sync_time(self, time=1000000):
        self.send('cmdSynctime {}'.format(int(time)))
        
    def blank_time(self, time=5000):
        self.send('cmdBlanktime {}'.format(int(time)))
        
    def info(self, X=0):
        self.send('info {}'.format(int(X)))
    
    def synthesizer(self):
        self.send('initsynthesizer')
