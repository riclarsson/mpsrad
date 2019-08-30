# -*- coding: utf-8 -*-
"""
Created: 2018-08-30

Last modification: 2018-08-30

Author: Richard Larsson

Interactions with CTS functionality
"""


import socket
import struct
import datetime
import numpy as np


class pc104:
    def __init__(self,
                 name="pc104",
                 response_name="MAIN",
                 frequency=[[1330, 1370]],
                 f0=None,
                 host="pc104",
                 tcp_port=1725,
                 udp_port=None,
                 channels=[4096],
                 integration_time=1000,
                 blank_time=None,
                 data_storage_containers=4,
                 reverse_data=False):
        """
        Parameters:
            name (str):
                Name of the mahcine (unused, kept as housekeeping)
            response_name (str):
                Name the mahcine recognize as host (see its mailboxdefs)
            host (str):
                Name of the host, IP or DNS
            tcp_port (str):
                Port to the PC104
            udp_port (str):
                Unused for this spectrometer
            channels (array of int):
                Numbers of channels of the spectrometer
            integration_time (int):
                Time in miliseconds
            blank_time (int):
                Unused for this spectrometer
            data_storage_containers (int):
                Storage containers for keeping data around
        """
        self.name=name
        self.response_name=response_name  # FIXME: UNIQUE TO THIS MACHINE!
        self.frequency=frequency
        self.f0=f0

        # Lock-check
        self._initialized=False
        self._sent=False

        # Set the runtime
        self._runtime=integration_time*1e-3

        # Constants
        self._channels=channels
        self._copies_of_vectors=int(data_storage_containers)

        # Host information
        self._tcp_port=tcp_port
        self._host=host

        self.reverse=reverse_data

    def init(self):
        assert self._initialized is False, "Not allowed to reinitialize"

        # Initiate data
        self._data=[]
        for i in range(self._copies_of_vectors):
            self._data.append(np.zeros((self._channels[0],), dtype=np.float64))

        self._soc = self._client_socket()
        self._send_msg(self.response_name)
        self._send_init()
        self._send_time()

        # We are now initialized
        self._initialized=True

    def run(self):
        """Runs the CTS

        Must be initialized already

        Use the index to access different data (e.g., cold/hot/ant/ref/calib)
        """
        assert self._initialized, "Must first initialize the CTS"
        assert not self._sent, "Cannot resend running without downloading"

        self._run_machine()
        self._sent = True

    def get_data(self, i=0):
        """Runs the CTS

        Must be initialized already
        
        Use the index to access different data (e.g., cold/hot/ant/ref/calib)
        """
        assert self._initialized, "Must first initialize the CTS"
        assert i < self._copies_of_vectors and i > -1, "Bad index"
        assert self._sent, "Cannot download without first running the machine"

        self._data[int(i)] = self._recv_data()
        self._sent = False

        if self.reverse:
            self._data[int(i)] = self._data[int(i)][::-1]

    def set_housekeeping(self, hk):
        """ Sets the housekeeping data dictionary.  hk must be dictionary """
        assert self._initialized, "Can set housekeeping when initialized"

        hk['Instrument'][self.name] = {}
        hk['Instrument'][self.name]['Frequency [MHz]'] = self.frequency
        hk['Instrument'][self.name]['Channels [#]'] = self._channels
        hk['Instrument'][self.name]['Integration [s]'] = self._runtime

    def save_data(self, basename="/home/dabrowski/data/test/CTS", file=None,
            binary=True):
        """Saves data to file at basename+file.

        If file is None, the current time is used to create the filename
        Saves with numpy binary format if binary is true or as ascii otherwise
        """
        assert self._initialized, "No data exists for an uninitialized CTS"

        now=datetime.datetime.now()
        if file is None:
            filename=self._hostname + now.strftime("-%Y%m%d%H%M%S-%f")
        else:
            filename=str(file)

        if binary: np.save(basename+filename, self._data)
        else: np.savetxt(basename+filename, self._data)

        return filename

    def close(self):
        """Remove the lock of the machine"""
        assert self._initialized, "Cannot close an uninitialized CTS"
        self._soc.close()
        del self._data
        self._initialized=False

    def _client_socket(self):
        a = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        a.connect((self._host, self._tcp_port))
        return a

    def _send_msg(self, msg):
        if isinstance(msg, str): msg = msg.encode('ascii')
        assert isinstance(msg, bytes), 'Must send bytes; cannot convert input'
        num = len(msg)
        assert num < 256**4, "Max one words, i.e. <{} chars".format(256**4)

        self._last_msg = msg

        count = []
        N = 1*num
        for i in range(4):
            c = N & (256**(i+1) - 1)
            count.append(c // 256**i)
            N -= c
        assert N == 0, "Remaining error"

        ret1 = self._soc.send(bytes(count[::-1]))
        ret2 = self._soc.send(msg)

        return ret1, ret2

    def _recv_data(self):
        num = struct.unpack('>I', self._soc.recv(4))[0]

        d = b''
        while len(d) < num: d+=self._soc.recv(1024)
        self._raw_reply = d

        offset = 0

        x = struct.unpack_from('32c', d, offset)
        offset += struct.calcsize('32c')
        self.magic =b''
        for i in x: self.magic += i

        x = struct.unpack_from('32c', d, offset)
        offset += struct.calcsize('32c')
        self.name =b''
        for i in x: self.name += i

        x = struct.unpack_from('32c', d, offset)
        offset += struct.calcsize('32c')
        self.dateStr = b''
        for i in x: self.dateStr+=i

        self.index = struct.unpack_from('i', d, offset)[0]
        offset += struct.calcsize('i')

        self.clock = struct.unpack_from('i', d, offset)[0]
        offset += struct.calcsize('i')

        self.firstSampleStartTime = struct.unpack_from('d', d, offset)[0]
        offset += struct.calcsize('d')

        self.lastSampleStopTime = struct.unpack_from('d', d, offset)[0]
        offset += struct.calcsize('d')

        self.IntegrationCounter = struct.unpack_from('i', d, offset)[0]
        offset += struct.calcsize('i')

        self.SumCounter = struct.unpack_from('i', d, offset)[0]
        offset += struct.calcsize('i')

        data = np.frombuffer(d[offset:], dtype='I')

#        print(self.index, self.clock, self.firstSampleStartTime, 
#              self.lastSampleStopTime, self.IntegrationCounter,
#              self.SumCounter)

        # Renormalize to similar count regardless of integration time
        return data / self.SumCounter

    def _send_init(self):
        ret = self._send_msg("INIT\0")
        for i in range(2):  # Receive two sets of data upon init; throw it away
           self._recv_data()
        return ret

    def _send_time(self):
        ret = self._send_msg('TIME "{}"\0'.format(int(self._runtime*1000)))
        return ret

    def _run_machine(self):
        ret = self._send_msg("RUN\0")
        return ret
