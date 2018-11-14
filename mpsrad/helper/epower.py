#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File for dealing with the ePowerSwitches
"""

import serial
import time

class epower4:
    def __init__(self, host, baud=9600):
        self.host = host
        self.baud = baud
        self._last = b''
        self._initialized = False

    def init(self):
        assert not self._initialized
        try:
            self.dev.open()
        except:
            self.dev = serial.Serial(self.host, self.baud)
        self._initialized = True

    def _external_cmd(self, cmd):
        if isinstance(cmd, str): cmd = cmd.encode('ascii')
        assert cmd[-1] == ord(b'\r')

        self.dev.write(cmd)
        time.sleep(0.2)
        a = self.dev.read_all()

        if a[:-1] not in cmd[1:]:
            raise RuntimeError("Cannot communicate properly with device")
        elif b'??' in a:
            raise RuntimeError("Device does not recognize command")

        self._last = a

    def _internal_command(self, i, t):
        assert self._initialized
        assert isinstance(i, int)
        assert i > -1 and i < 5
        assert t in ['r', 't', 1, 0]

        self._external_cmd('/P0{}={}\r'.format(i, t))

    def on(self, i=0):
        self._internal_command(i, 1)

    def off(self, i=0):
        self._internal_command(i, 0)

    def toggle(self, i=0):
        self._internal_command(i, 't')

    def restart(self, i=0):
        self._internal_command(i, 'r')

    def flush_last(self):
        assert self._initialized
        while True:
            a = self.dev.read_all()
            self._last += a
            if a == b'':
                break
        print(self._last.decode('ascii'))
        self._last = b''

    def close(self):
        assert self._initialized
        self.dev.close()
        self._initialized=False
