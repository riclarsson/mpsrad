#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Last modification: 29.03.2018

Author: Borys Dabrowski

Code to measure resistance and convert it in temperature.
"""

import socket,time

class pt100:
    """ Interactions with PT-100 functionality
    """

    def __init__(self, address=22,host='192.168.5.10', tcp_port=1234,
            timeout=5, name="pt100-python"):
        """PT-100 interface

        Communication and temperature readouts from a PT-100

        Parameters:
            address (int):
                Address of the machine
            host (str):
                Name of the host, IP or DNS
            tcp_port (int):
                Port to communicate with the PT-100 over
            timeout (float, int):
                Time allowed to wait for data before moving on, if no data is
                received during this time, nothing special happens
            name (any):
                Name of this machine (unused, kept as housekeeping)

        Example:
            >>> s = pt100()
            >>> s.init()
            >>> print(round(s.get_temperature(), 2), 'K')
            295.23 K
            >>> s.close()

        """
        self._initialized = False
        self._address = address

        # Host information
        self._tcp_port = tcp_port
        self._host = host
        self._timeout = timeout

        # Housekeeping
        self.name = name

    def ohm2celsius(self, R_PT100):
        """Converts PT-100 Ohm to degrees Celsius

        Solves the following expression

        .. math::
            T = c_0 - (100 - R_{PT100})(c_1 - (100 - R_{PT100})(c_2 - \
            (100 - R_{PT100})(c_3 - c_4(100 - R_{PT100}))))

        where the :math:`c_n`-coefficients are determined (see code for values)

        Parameters:
            R_PT100 (float):
                Resistance measured in the PT-100

        Returns (float):
            Temperature in Celsius

        Example:
            >>> s = pt100()
            >>> print(round(s.ohm2celsius(110), 2))
            25.69
        """
        R0 = 100.0
        c = [-1.138628e-03, 2.559038e+00, 9.988525e-04, -1.061679e-06,
             2.585121e-08]

        temp = c[4]
        for n in [3, 2, 1, 0]:
            temp = temp * (R_PT100 - R0) + c[n]
        return temp

    def init(self):
        """Initializes the machine by trying out the connections.

        The PT-100 cannot be initialized before running this command
        """
        assert not self._initialized, "Cannot init initialized machine"

        # Open socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self._host, self._tcp_port))
        s.setblocking(0)    # make socket non blocking

        # Set address
        s.sendall(b'++addr '+str(self._address).encode('ascii')+'\r\n')

        # Send setup
        s.sendall(b'++clr\r\n')
        time.sleep(2)
        s.sendall(b'F3 R2 N5 Z1 T4 M35 \r\n')
        time.sleep(2)
        s.sendall(b'F3 R2 N5 Z1 T4 M35 \r\n')

        # Close socket
        s.close()

        self._initialized = True

    def _get_resistance(self):
        assert self._initialized, "Cannot run uninitialized machine"

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self._host, self._tcp_port))
        s.setblocking(0)    # make socket non blocking

        # Set address
        s.sendall(b'++addr '+str(self._address).encode('ascii')+'\r\n')

        # Trigger measurement, ask for results
        s.sendall(b'T3\r\n')

        # Set instrument to talk
        s.sendall(b'++read eoi\r\n')

        # Get the answer
        t0, ready = time.time(), False
        while time.time() - t0 < self._timeout and not ready:
            try:
                answ = s.recv(1024)
                time.sleep(.5)
                try:
                    answ = answ + s.recv(1024)
                except:
                    pass
                ready = True
            except:
                pass
            time.sleep(.1)

        # Close socket
        s.close()

        if ready:
            return float(answ.replace('\r\n', ''))
        else:
            return -1

    def get_temperature(self, unit='K'):
        """Returns the temperature using ohm2celsius after reading the PT-100

        The pt100 has to be initialized before running this command

        Parameters:
            unit (str):
                 "K" adds 273.15 to returned result, other inputs does not

        Returns (float):
            Temperature as read from the resistor

        Example:
            >>> print(pt100.get_temperature())
            295.7
            >>> print(pt100.get_temperature('anything'))
            22.55
        """
        assert self._initialized, "Cannot run uninitialized machine"

        res = -1
        while res < 0:
            res = self._get_resistance()
            if res < 0:
                time.sleep(.5)

        # Convert resistance to temperature
        temp = self.ohm2celsius(res)
        if unit == 'K':
            return temp+273.15
        else:
            return temp

    def close(self):
        """Closes the machine

        Must be initialized already, and will set itself in an uninitialized
        state
        """
        assert self._initialized, "Cannot close uninitialized machine"
        self._initialized = False
