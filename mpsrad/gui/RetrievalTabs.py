#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Aug 30 15:26:37 2018

@author: dabrowski
"""

import time
import numpy as np
from mpsrad.retrieval.oem_retrieval import oem_retrieval, fft_bandpass, fft_lowpass, fft_highpass



import scipy.optimize
def sine_fit(tt, yy):
    '''Fit sin to the input time sequence, and return fitting parameters 
    "amp", "omega", "phase", "offset", "freq", "period" and "fitfunc"
    
    Code is made available under creative commons by unsym at following link:
        https://stackoverflow.com/questions/16716302/how-do-i-fit-a-sine-curve-to-my-data-with-pylab-and-numpy
    '''
    tt = np.array(tt)
    ff = np.fft.fftfreq(len(tt), (tt[1] - tt[0]))
    Fyy = abs(np.fft.fft(yy))
    guess_freq = abs(ff[np.argmax(Fyy[1:])+1])
    guess_amp = np.std(yy) * 2.**0.5
    guess_offset = np.mean(yy)
    guess = np.array([guess_amp, 2.*np.pi*guess_freq, 0., guess_offset])

    def sinfunc(t, A, w, p, c):  return A * np.sin(w*t + p) + c
    popt, pcov = scipy.optimize.curve_fit(sinfunc, tt, yy, p0=guess)
    A, w, p, c = popt
    f = w/(2.*np.pi)
    fitfunc = lambda t: A * np.sin(w*t + p) + c
    return {"amp": A, "omega": w, "phase": p, "offset": c, 
            "freq": f, "period": 1./f, "fitfunc": fitfunc, 
            "maxcov": np.max(pcov), "rawres": (guess, popt, pcov)}


def measurement_offset_calc_mask(z, x):
    dy = 0.0
    for zz in z:
        dy += zz['offset'] + zz['amp'] * np.sin(zz['omega']*x + zz['phase'])
    return dy

def measurement_offset_calc_true(z, x):
    dy = 0.0
    for zz in z:
        if round(zz['period']*1e3, 2) > 0.5:
            dy += zz['offset'] + zz['amp'] * np.sin(zz['omega']*x + zz['phase'])
        else:
            dy += zz['offset']
    return dy

def print_measurement_offset(z):
    o = 0
    i = 0
    for zz in z:
        if round(zz['period']*1e3, 2) > 0.5:
            print("Found wave with", round(zz['period']*1e3, 2), 'MHz period,', round(zz['amp']*1000, 2), 'mK amplitude, and a phase of', round(np.rad2deg(zz['phase'])), 'degrees')
        else:
            o += zz['offset']
            i += 1
    print("Found DC offset of", round(o*1000, 2), "mK in identified 'waves' of < 500 kHz")

class oemWidget:
    def __init__(self, spectrometer_tabs, window):
        self.tabs = spectrometer_tabs
        self.window = window
        self.f0 = None
        self.Retrieval = oem_retrieval()

        self.meas_resp=[]*len(self.tabs.sp)
        self.x = []*len(self.tabs.sp)
        self.xa = None
        self.noise_mod_signal = []*len(self.tabs.sp)
        self.yf = []*len(self.tabs.sp)
        self.altitude = None
        self.oem_diag = []*len(self.tabs.sp)
        self.measurement_noise = [0]*len(self.tabs.sp)
        self.measurement_noise_fit = [0]*len(self.tabs.sp)
        self.measurement_sigma = [0]*len(self.tabs.sp)
        self.count=0
        self.physical_sigma = [True]*len(self.tabs.sp)
        self.measurement_freq = []*len(self.tabs.sp)
        self.measurement_offset = []
        self._initialized=False
        self.measurements=self

    def init(self):
        assert not self._initialized, "Cannot be initialized first"
        self.altitude = None
        self.xa = None
        time.sleep(10)
        self.meas_resp=[0]*len(self.tabs.sp)
        self.x = [0]*len(self.tabs.sp)
        self.noise_mod_signal = [0]*len(self.tabs.sp)
        self.yf = [0]*len(self.tabs.sp)
        self.oem_diag = [0]*len(self.tabs.sp)
        self.measurement_noise = [0]*len(self.tabs.sp)
        self.measurement_noise_fit = [0]*len(self.tabs.sp)
        self.measurement_sigma = [0]*len(self.tabs.sp)
        self.physical_sigma = [True]*len(self.tabs.sp)
        self.measurement_freq = []*len(self.tabs.sp)
        self.measurement_offset = []

        self._initialized = True

    def setMeasurement(self, F0=22.2353368):
        self.f0 = F0

    def refresh_oem(self, i):
        time.sleep(20)
        return
        assert self._initialized, "Must initialize first"

        if self.f0 is None:
            time.sleep(5)
            return

        signal = np.copy(self.tabs.sp[i].Ti)[::-1]

        guess_of_high_alt_temp = 3.5
        pseudo_trop_temp = 273.15
        pseudo_opacity_below = - np.log((pseudo_trop_temp - np.median(signal[:len(signal)//2])) / (pseudo_trop_temp - guess_of_high_alt_temp))
        pseudo_opacity_above = - np.log((pseudo_trop_temp - np.median(signal[len(signal)//2:])) / (pseudo_trop_temp - guess_of_high_alt_temp))
        pseudo_transmission = np.exp(np.linspace(pseudo_opacity_below, pseudo_opacity_above, len(signal)))

        pseudo_signal = signal * pseudo_transmission + pseudo_trop_temp * (1.0 - pseudo_transmission)

        noise = np.copy(self.tabs.sp[i].Tri)[::-1]

        freq = np.linspace(self.tabs.sp[i].axisLimits[0],
                           self.tabs.sp[i].axisLimits[1], noise.size) / 1e3
        freq += self.f0 - freq.mean() - 444e3*1e-9

        if np.any(pseudo_signal < 1):
            self.noise_mod_signal[i] = np.array([0, 0])
            self.yf[i] = np.array([0, 0])
            self.oem_diag[i] = np.array([0, 0])
            self.measurement_noise[i] = np.array([0, 0])
            self.measurement_noise_fit[i] = np.array([0, 0])
            self.measurement_sigma[i] = np.array([0, 0])
            self.measurement_freq[i] = np.array([0, 1])
            self.meas_resp[i] = np.array([0, 0])
            self.x[i] = np.array([0, 0])
            self.xa = np.array([0, 0])
            self.altitude = np.array([0, 0])
        else:
            self.Retrieval.load_data(data_type='numpy', signal=[pseudo_signal],
                                         noise=[noise],freq=freq)
            self.Retrieval.process_data(lims=[22.22, 22.24], central_freq=self.f0)  # WARNING:  Bad values because of broken CTS?
            # Input booleans for filtering and shifting of the retrieval
            DoFilter = False
            DoShift  = False
            if self.physical_sigma[i]:
                n = self.tabs.sp[i].int_count / 2
                sigma = np.median(noise)/np.sqrt(5 * n * (freq[1] - freq[0])*1e9)
                self.Retrieval.mean_retrieval(filtered=DoFilter,
                                              shift_freq=DoShift, sigma=sigma,
                                              central_freq=self.f0)
            else:
                print("Emitting non-physical sigma")

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

            vmr_is_log10 = True
            if self.altitude is None: self.altitude = self.Retrieval.arts.z_field.value.flatten()

            if self.xa is None:
                self.xa = self.Retrieval.arts.xa.value[:-1]
                if vmr_is_log10:
                    self.xa[0:len(self.altitude)] = self.xa[0:len(self.altitude)] * 1e6

            self.x[i] = self.Retrieval.arts.x.value[:-1]
            if vmr_is_log10:
                self.x[i][0:len(self.altitude)] = self.x[i][0:len(self.altitude)] * 1e6

            self.noise_mod_signal[i] = np.copy(self.Retrieval.average_signal)
            self.yf[i] = np.copy(self.Retrieval.arts.yf.value)
            self.oem_diag[i] = np.copy(self.Retrieval.arts.oem_diagnostics.value)
            self.measurement_noise[i] = self.Retrieval.average_signal-self.yf[i]
            self.measurement_noise_fit[i] = 0
            self.measurement_sigma[i] = self.measurement_noise[i].std()
            self.measurement_freq[i] = np.copy(self.Retrieval.fit_freq)

            averaging_kernel = np.copy(self.Retrieval.arts.avk.value)
            measurement_response = averaging_kernel @ np.ones(averaging_kernel.shape[1])

            self.meas_resp[i] = measurement_response

            print("original calc done")

            self.measurement_offset[i] = []
            fmin = self.measurement_freq[i][0]
            for _ in range(20):
                try:
                    dy = measurement_offset_calc_mask(self.measurement_offset[i], self.measurement_freq[i]-fmin)
                    self.measurement_offset[i].append(sine_fit(self.measurement_freq[i]-fmin, self.measurement_noise[i]-dy))
                except:
                    break
            self.Retrieval.load_data(data_type='numpy', signal=[pseudo_signal-measurement_offset_calc_true(self.measurement_offset[i], freq-fmin)],
                                         noise=[noise],freq=freq)
            self.Retrieval.process_data(lims=[22.22, 22.24], central_freq=self.f0)  # WARNING:  Bad values because of broken CTS?
            self.Retrieval.mean_retrieval(filtered=DoFilter, shift_freq=DoShift, sigma=sigma, central_freq=self.f0)

            self.noise_mod_signal[i] = np.copy(self.Retrieval.average_signal)
            self.yf[i] = np.copy(self.Retrieval.arts.yf.value)
            self.oem_diag[i] = np.copy(self.Retrieval.arts.oem_diagnostics.value)
            self.measurement_noise[i] = self.Retrieval.average_signal-self.yf[i]
            self.measurement_noise_fit[i] = measurement_offset_calc_true(self.measurement_offset[i], self.measurement_freq[i]-fmin)
            self.measurement_sigma[i] = self.measurement_noise[i].std()
            self.measurement_freq[i] = np.copy(self.Retrieval.fit_freq)

            averaging_kernel = np.copy(self.Retrieval.arts.avk.value)
            measurement_response = averaging_kernel @ np.ones(averaging_kernel.shape[1])

            self.meas_resp[i] = measurement_response
            print_measurement_offset(self.measurement_offset[i])
            print("fitted calc done")

        self.tabs.retrieval.refreshTab(self, i)
        print('OEM plotting done 2')


    def setF0(self, F0):
        self.f0 = F0

    def run(self):
        # Safety size check
        if len(self.tabs.sp) != len(self.meas_resp): self.meas_resp = [0] * len(self.tabs.sp)
        if len(self.tabs.sp) != len(self.x): self.x = [0] * len(self.tabs.sp)
        if len(self.tabs.sp) != len(self.noise_mod_signal): self.noise_mod_signal = [0] * len(self.tabs.sp)
        if len(self.tabs.sp) != len(self.yf): self.yf = [0] * len(self.tabs.sp)
        if len(self.tabs.sp) != len(self.oem_diag): self.oem_diag = [0] * len(self.tabs.sp)
        if len(self.tabs.sp) != len(self.measurement_sigma): self.measurement_sigma = [0] * len(self.tabs.sp)
        if len(self.tabs.sp) != len(self.measurement_noise): self.measurement_noise = [0] * len(self.tabs.sp)
        if len(self.tabs.sp) != len(self.measurement_noise_fit): self.measurement_noise_fit = [0] * len(self.tabs.sp)
        if len(self.tabs.sp) != len(self.physical_sigma): self.physical_sigma = [True] * len(self.tabs.sp)
        if len(self.tabs.sp) != len(self.measurement_freq): self.measurement_freq = [0] * len(self.tabs.sp)
        if 0 == len(self.measurement_offset):
            for i in self.tabs.sp:
                self.measurement_offset.append([])

        assert self._initialized, "Must initialize first"
        try:
            self.refresh_oem(self.count)
            self._error=None
        except Exception as e:
            self._error=e
            print(e)
            time.sleep(10)

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
