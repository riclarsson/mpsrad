#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov 23 16:03:11 2017

@author: larsson
"""

import struct
import numpy as np
try:
    import matplotlib.pyplot as plt
    import matplotlib.animation as animation
except:
    pass
import datetime
import os


eform = '>i16f7500f100f28f28f'


class _files:
    def load(self, filename=None):
        if filename:
            self._filename = filename
        file = open(filename, 'rb')
        raw = []
        time = []

        # Read everything
        while True:
            try:
                time.append(np.frombuffer(file.read(4), '>i')[0])
                raw.append(np.frombuffer(file.read(self._size-4), '>f'))
            except:  # if the formatting fails or file ends (pref latter)
                break
        assert len(raw) > 3, "No full data"
        file.close()

        self._raw = raw
        self._rawtime = time

    def append(self, data):
        for d in data._data:
            self._data.append(d)
        for t in data._time:
            self._time.append(t)

    def _get_format(self, format):
        f = []
        t = ''
        for i in format:
            if i == '>':
                pass
            elif i in '1234567890':
                t += i
            else:
                if t:
                    f.append(int(t))
                else:
                    f.append(1)
                t = ''
        del f[0]
        self._format = np.array(f)


class calibration(_files):
    """Calibrates raw data"""
    def __init__(self, format=eform,
                 t_cold=21, t_hot=295):
        assert format[0] == '>', "Must use big-endian to read and store data"
        assert format[1] == 'i', "Must use index time-stamp as first variable"

        self._struct = struct.Struct(format)
        self._size = self._struct.size
        self._hot = False
        self._th = t_hot
        self._tc = t_cold
        self._data_field = 1
        self._noise_field = 2
        self._get_format(format)

        assert not self._format[self._data_field] % \
            self._format[self._noise_field], ("Noise-size not multiple of "
                                              "data-size")

    def calibrate(self):
        # Delete mismatching data
        while len(self._raw) % 2:
            del self._raw[-1]

        # Storage variables
        self._data = []
        self._time = []

        # Calibration loop
        i = 0  # raw-counter
        count = 0  # calibrated counter
        d = self._format[self._data_field]  # Number of data
        n = self._format[self._noise_field]  # Number of noise
        s = self._format[:self._data_field].sum()  # Start of data
        e = s + d  # End of data
        while i < len(self._raw):
            # Set the current hot or cold load measurement power
            if self._hot:
                h = self._raw[i][s:e]
            else:
                c = self._raw[i][s:e]

            # Set the current measurement power
            i += 1
            self._hot = not self._hot
            self._time.append(self._rawtime[i])
            data = self._raw[i][:s]
            data_end = self._raw[i][(e+n):]
            m = self._raw[i][s:e]
            i += 1

            # Read ahead to use the first data record
            if count == 0:
                if self._hot:
                    h = self._raw[i][s:e]
                else:
                    c = self._raw[i][s:e]

            # Calibrate
            signal = self._tc + (m-c)*(self._th-self._tc)/(h-c)
            noise = ((self._th*c-self._tc*h)/(h-c)).reshape(n,
                                                            d//n).mean(axis=1)

            # Store
            self._data.append(np.append(np.append(np.append(data, signal),
                                                  noise), data_end))

            count += 1

    def save(self, filename=None):
        if not filename:
            filename = self._filename

        # New file format is clb
        if '.raw' in filename[-4:]:
            filename = filename.replace('.raw', '.clb')
        elif '.clb' not in filename[-4:]:
            filename += '.clb'

        file = open(filename, 'wb')
        for i in range(len(self._time)):
            t = self._time[i]
            file.write(np.array([t], dtype='i').byteswap().tobytes())
            d = self._data[i].byteswap()
            file.write(d.tobytes())
        file.close()


class averaging(_files):
    def __init__(self, format=eform, running_average=True):
        assert format[0] == '>', "Must use big-endian to read and store data"
        assert format[1] == 'i', "Must use index time-stamp as first variable"

        self._struct = struct.Struct(format)
        self._size = self._struct.size
        self._running_average = running_average
        self._data_field = 1
        self._get_format(format)

    def average(self, number_of_spectra=100, number_of_xbin=2):
        # Storage variables
        self._data = []
        self._time = []

        # Calibration loop
        d = self._format[self._data_field]  # Number of data
        s = self._format[:self._data_field].sum()  # Start of data
        e = s + d  # End of data

        # Counter
        j = 0
        for i in range(len(self._rawtime)):
            t = self._rawtime[i]
            d = self._raw[i][s:e]

            if self._running_average or j == 0:
                self._time.append([t])
                self._data.append(d)

            if j >= number_of_spectra:
                self._time[i - number_of_spectra].append(t)
                if not self._running_average:
                    j = 0
                if j == 0:
                    continue

            # Average results up
            if self._running_average:
                for k in range(i-1, i - number_of_spectra, -1):
                    if k < 0:
                        break
                    self._data[k] = self._data[k] + d
            else:
                self._data[-1] = self._data[-1] + d

            j += 1

        # Remove running average that are not averaged
        while len(self._time[-1]) < 2:
            del self._data[-1]
            del self._time[-1]

        for i in range(len(self._data)):
            first = True
            while self._data[i].shape[0] % number_of_xbin:
                if first:
                    np.delete(self._data[i], 0)
                else:
                    np.delete(self._data[i], -1)
                first = not first
            s = (len(self._data[i]) // number_of_xbin, number_of_xbin)
            self._data[i] = self._data[i].reshape(s).mean(axis=1)

        # Actually average the data
        for d in self._data:
            d /= number_of_spectra

    def save(self, filename=None):
        if not filename:
            filename = self._filename

        # New file format is npy
        if '.clb' in filename[-4:]:
            filename = filename.replace('.clb', '.npy')
        elif '.npy' not in filename[-4:]:
            filename += '.npy'

        np.save(filename, [self._time, self._data])

    def save_movie(self, filename, ylim=None, xlim=None, fps=60,
                   artist='Average', title='Spectral Data',
                   xbin_name='bins', xdata=None):
        ffmpeg = animation.writers['ffmpeg']
        metadata = dict(title=title, artist=artist)
        writer = ffmpeg(fps=fps, metadata=metadata)
        fig = plt.figure()
        if xdata:
            l, = plt.plot(xdata, self._data[0], 'k')
        else:
            l, = plt.plot(self._data[0], 'k')
            xdata = np.array(range(len(self._data[0])))
        plt.ylabel('Brightness Temperature [K]')
        plt.xlabel('Frequency ['+xbin_name+']')

        time = datetime.datetime.fromtimestamp

        if ylim:
            plt.ylim(ylim[0], ylim[1])
        if xlim:
            plt.xlim(xlim[0], xlim[1])
            rx = np.logical_and(xlim[0] < xdata, xdata < xlim[1])

        with writer.saving(fig, filename, 100):
            for i in range(len(self._data)):
                l.set_ydata(self._data[i])
                t1 = time(self._time[i][0]).strftime('%Y-%m-%d %H:%M:%S')
                t2 = time(self._time[i][1]).strftime('%Y-%m-%d %H:%M:%S')
                plt.title(t1 + ' to ' + t2)
                if not ylim:
                    if not xlim:
                        mi = self._data[i].min()
                        ma = self._data[i].max()
                    else:
                        mi = self._data[i][rx].min()
                        ma = self._data[i][rx].max()
                    dm = 0.1 * (ma - mi)
                    plt.yticks(range(int(np.floor(mi-dm-1)),
                                     int(np.ceil(ma+dm)+1)))
                    plt.ylim(mi-dm, ma+dm)
                writer.grab_frame()


class raw(_files):
    def __init__(self, format=eform):
        assert format[0] == '>', "Must use big-endian to read and store data"
        assert format[1] == 'i', "Must use index time-stamp as first variable"

        self._struct = struct.Struct(format)
        self._size = self._struct.size
        self._data_field = 1
        self._get_format(format)

    def average_raw(self):
        """Averages a raw field and returns the vector to check for variations.

        Assumes four fields in CAHA order
        """

        out_cold = []
        out_ant1 = []
        out_hot = []
        out_ant2 = []
        out_t = self._rawtime

        i = 0
        while i < len(self._raw):
            if (i % 4 == 0):
                out_cold.append(np.mean(self._raw[i]))
            elif (i % 4 == 1):
                out_ant1.append(np.mean(self._raw[i]))
            elif (i % 4 == 2):
                out_hot.append(np.mean(self._raw[i]))
            elif (i % 4 == 3):
                out_ant2.append(np.mean(self._raw[i]))

            i += 1

        return np.array(out_cold), np.array(out_ant1), np.array(out_hot), \
            np.array(out_ant2), out_t

    def append_to_file(self, filename, time, housekeeping, data, noise,
                       filters=None):
        # print("appending time")
        p = struct.pack('>I', time)

        # print("appending housekeeping")
        p += struct.pack('>'+str(self._format[0])+'f', *housekeeping)

        # print("appending data")
        p += struct.pack('>'+str(self._format[1])+'f', *data)

        # print("appending noise")
        p += struct.pack('>'+str(self._format[2])+'f', *noise)

        # print("appending filters")
        s = self._format[-1]+self._format[-2]
        if filters:
            p += struct.pack('>'+str(s)+'f', *filters)
        else:
            p += struct.pack('>'+str(s)+'f', *np.zeros((s)))

        if os.path.exists(filename):
            a = open(filename, 'ab')
        else:
            a = open(filename, 'wb')
        a.write(p)
        a.close()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        save_file = None
        next_save = False
        c = calibration()
        c.load(sys.argv[1])
        c.calibrate()
        for i in range(2, len(sys.argv)):
            if next_save:
                save_file = sys.argv[i]
                next_save = False
            elif sys.argv[i] == '-o':
                next_save = True
            elif '-' == sys.argv[i][0]:
                assert False, "Cannot understand command"
            else:
                _c = calibration()
                _c.load(sys.argv[i])
                _c.calibrate()
                c.append(_c)
        if save_file:
            c.save(save_file)
        else:
            c.save()
