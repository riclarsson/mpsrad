#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File for dealing with UPS
"""

import subprocess
from mpsrad.helper.epower import epower4


class APCUPS:
    def __init__(self, shutdown=False, epower4_hosts=[]):
        self._exists = False
        self._initialized = False
        self._ep_hosts = epower4_hosts
        self._shutdown_command = shutdown

    def init(self):
        assert not self._initialized
        try:
            t = subprocess.check_output(['apcaccess']).decode('ascii')
            self._exists = True if 'BCHARGE' in t else False
        except:
            self._exists = False

        self._epowers = [epower4(n) for n in self._ep_hosts]
        for i in self._epowers: i.init()

        self._initialized = True

    def run(self):
        assert self._initialized
        if not self._exists:
            return (-1, 200)
        t = subprocess.check_output(['apcaccess']).decode('ascii').split('\n')

        a = b = None
        for i in t:
            if 'BCHARGE' in i:
                a = int(float(i.split(':')[1].split('P')[0]))
            elif 'STATUS' in i:
                b = 1 if 'ONLINE' in i else 0
        if a is None or b is None:
            return (-1, 200)
        else:
            return (b, a)

    def close(self):
        assert self._initialized
        self._initialized = False
        if self._shutdown_command and self._exists:
            for i in self._epowers: i.off()
            subprocess.call(['shutdown', 'now'])
