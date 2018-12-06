#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Aug 30 15:26:37 2018

@author: dabrowski
"""

import time
import numpy as np
from mpsrad.retrieval.oem_retrieval import oem_retrieval

class oemWidget:
    def __init__(self, spectrometer_tabs, window):
        self.tabs = spectrometer_tabs
        self.window = window
        self.f0 = None
        self.Retrieval = oem_retrieval()

        self.meas_resp=[]*len(self.tabs.sp)
        self.vmr = []*len(self.tabs.sp)
        self.apriori_vmr = None
        self.noise_mod_signal = []*len(self.tabs.sp)
        self.yf = []*len(self.tabs.sp)
        self.altitude = None
        self.oem_diag = []*len(self.tabs.sp)
        self.measurement_noise = [0]*len(self.tabs.sp)
        self.measurement_sigma = [0]*len(self.tabs.sp)
        self.count=0
        self.physical_sigma = [True]*len(self.tabs.sp)
        self.measurement_freq = []*len(self.tabs.sp)

        self._initialized=False
        self.measurements=self

    def init(self):
        assert not self._initialized, "Cannot be initialized first"
        self.altitude = None
        self.apriori_vmr = None
        time.sleep(10)
        self.meas_resp=[0]*len(self.tabs.sp)
        self.vmr = [0]*len(self.tabs.sp)
        self.noise_mod_signal = [0]*len(self.tabs.sp)
        self.yf = [0]*len(self.tabs.sp)
        self.oem_diag = [0]*len(self.tabs.sp)
        self.measurement_noise = [0]*len(self.tabs.sp)
        self.measurement_sigma = [0]*len(self.tabs.sp)
        self.physical_sigma = [True]*len(self.tabs.sp)
        self.measurement_freq = []*len(self.tabs.sp)

        self._initialized = True

    def setMeasurement(self, F0=22.2353368):
        self.f0 = F0

    def refresh_oem(self, i):
        assert self._initialized, "Must initialize first"

        if self.f0 is None:
            time.sleep(5)
            return

        signal = np.copy(self.tabs.sp[i].Ti)
        noise = np.copy(self.tabs.sp[i].Tri)
        freq = np.linspace(self.tabs.sp[i].axisLimits[0],
                           self.tabs.sp[i].axisLimits[1], noise.size) / 1e3
        freq += self.f0 - freq.mean()

        self.Retrieval.load_data(data_type='numpy', signal=[signal],
                                 noise=[noise],freq=freq)
        self.Retrieval.process_data(lims=self.window, central_freq=self.f0)

        # Input booleans for filtering and shifting of the retrieval
        DoFilter = False
        DoShift  = True
        if self.physical_sigma[i]:
            n = self.tabs.sp[i].int_count
            sigma = 2*noise[25:-25].mean()/np.sqrt(5 * n * (freq[1] - freq[0])*1e9)
            self.Retrieval.mean_retrieval(filtered=DoFilter,
                                          shift_freq=DoShift, sigma=sigma,
                                          central_freq=self.f0)

        skip_logic=False
        if self.Retrieval.arts.oem_diagnostics.value[4] == 20.0:
            self.physical_sigma[i] = False
        if not self.physical_sigma[i] and self.measurement_sigma[i] > 0:
            raise Warning('Max iterations reached: Retrying retrieval with residual-based sigma.')
            self.Retrieval.mean_retrieval(filtered=DoFilter,shift_freq=DoShift,sigma=self.measurement_sigma[i],
                                          central_freq=self.f0)
        elif not self.physical_sigma[i]:
            raise Warning('Max iterations reached: Retrying retrieval with noise-generated sigma.')
            self.Retrieval.mean_retrieval(filtered=DoFilter,shift_freq=DoShift,
                                          central_freq=self.f0)
            skip_logic = True
        if self.Retrieval.arts.oem_diagnostics.value[4] == 20.0 and not skip_logic:  # nb., not elif
            raise Warning('Max iterations reached: Retrying retrieval with noise-generated sigma.')
            self.Retrieval.mean_retrieval(filtered=DoFilter,shift_freq=DoShift,
                                          central_freq=self.f0)
        if self.Retrieval.arts.oem_diagnostics.value[4] == 20:
            raise Warning('Could not converge even with noise-generated sigma!')

#        self.Retrieval.plot_oem(basename='/home/dabrowski/Spec_Plots/spec{}_'.format(i))





        self.tabs.retrieval.refreshTab(self.Retrieval)





        self.vmr[i] = 10**self.Retrieval.arts.x.value[:-1]
        if self.apriori_vmr is not None: self.apriori_vmr = 10**self.Retrieval.arts.xa.value[:-1]
        if self.altitude is not None: self.altitude = self.Retrieval.arts.z_field.value.flatten()
        self.noise_mod_signal[i] = np.copy(self.Retrieval.average_signal)
        self.yf[i] = np.copy(self.Retrieval.arts.yf.value)
        self.oem_diag[i] = np.copy(self.Retrieval.arts.oem_diagnostics.value)
        self.measurement_noise[i] = self.Retrieval.average_signal-self.yf[i]
        self.measurement_sigma[i] = self.measurement_noise[i].std()
        self.measurement_freq[i] = self.Retrieval.fit_freq

        averaging_kernel = (self.Retrieval.arts.dxdy.value @
                           self.Retrieval.arts.jacobian.value)
        measurement_response = averaging_kernel @ np.ones(averaging_kernel.shape[1])

        self.meas_resp[i] = measurement_response

    def setF0(self, F0):
        self.f0 = F0

    def run(self):
        # Safety size check
        if len(self.tabs.sp) != len(self.meas_resp): self.meas_resp = [0] * len(self.tabs.sp)
        if len(self.tabs.sp) != len(self.vmr): self.vmr = [0] * len(self.tabs.sp)
        if len(self.tabs.sp) != len(self.noise_mod_signal): self.noise_mod_signal = [0] * len(self.tabs.sp)
        if len(self.tabs.sp) != len(self.yf): self.yf = [0] * len(self.tabs.sp)
        if len(self.tabs.sp) != len(self.oem_diag): self.oem_diag = [0] * len(self.tabs.sp)
        if len(self.tabs.sp) != len(self.measurement_sigma): self.measurement_sigma = [0] * len(self.tabs.sp)
        if len(self.tabs.sp) != len(self.measurement_noise): self.measurement_noise = [0] * len(self.tabs.sp)
        if len(self.tabs.sp) != len(self.physical_sigma): self.physical_sigma = [True] * len(self.tabs.sp)
        if len(self.tabs.sp) != len(self.measurement_freq): self.measurement_freq = [0] * len(self.tabs.sp)

        assert self._initialized, "Must initialize first"
        try:
            self.refresh_oem(self.count)
            self._error=None
        except Exception as e:
            print("OEM error or still waiting:", e)
            self._error=e
            time.sleep(3)

    def save(self):
        pass

    def update(self):
        assert self._initialized, "Must initialize first"
        self.count += 1
        self.count %= len(self.tabs.sp)

    def close(self):
        assert self._initialized, "Must initialize first"
        print("Closed OEM")
        self._initialized=False
