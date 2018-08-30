#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov 23 16:03:11 2017

Author: Richard Larsson

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

dform = '>i16f4092f100f28f28f'

aform = '>i16f16384f128f28f28f'

xform = '>i16f1018f128f28f28f'

xtest2form = '>i16f1019f2065i128f28f28f'

def formatting(type='e'):
    if type == 'e':
        return eform
    elif type == 'd':
        return dform
    elif type == 'a':
        return aform
    elif type == 'x':
        return xform
    elif type == 'xtest2':
        return xtest2form
    else:
        return None


class _files:
    def load(self, filename):
        self._filename = filename
        raw = []
        time = []

        s = os.stat(filename).st_size
        nbits = 0
        # Read everything
        with open(filename, 'rb') as file:
            while True:
                try:
                    time.append(np.frombuffer(file.read(4), '>i')[0])
                    raw.append(np.frombuffer(file.read(self._size-4), '>f'))
                    nbits += self._size
                    if nbits == s:
                        break
                except:
                    raise RuntimeError("Error in reading file. Wrong bitcount")
        assert len(raw) > 3, "No full data in: " + filename

        self._raw = raw
        self._rawtime = time

    def load_list(self, filenames):
        assert isinstance(filenames, (list, np.array)), "Not list of files"
        self._filename = filenames[0]

        self._raw = []
        self._rawtime = []

        tmp = _files()
        tmp._size = self._size
        for f in filenames:
            print('loading', f)
            tmp.load(f)
            self._raw.extend(tmp._raw)
            self._rawtime.extend(tmp._rawtime)

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
        """
        Parameters:
            format (str):
                set the format of the file. Either eform or aform
            t_cold (int):
                **INFO**
            t_hot (int):
                **INFO**
        """
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

    def calibrate(self, sweep_count=None, with_hkp=False):
        """
        Parameters:
            sweep_count (None type):
                **INFO**
            with_hkp (boulean):
                **INFO**
        """
        # Delete mismatching data
        while len(self._raw) % 2:
            del self._raw[-1]

        if sweep_count:
            sweep = True
        else:
            sweep = False

        # Storage variables
        self._data = []
        self._time = []

        # Calibration loop
        i = 0  # raw-counter
        count = 1  # calibrated counter
        d = self._format[self._data_field]  # Number of data
        n = self._format[self._noise_field]  # Number of noise
        s = self._format[:self._data_field].sum()  # Start of data
        e = s + d  # End of data
        while i < len(self._raw):
            # Set the current hot or cold load measurement power
            if self._hot:
                h = self._raw[i][s:e]
                if not with_hkp:
                    th = self._th
                elif self._raw[i][1] > 0:
                    th = self._raw[i][0]
                else:
                    th = self._th
            else:
                c = self._raw[i][s:e]
                if not with_hkp:
                    tc = self._tc
                elif self._raw[i][0] > 0:
                    tc = self._raw[i][0]
                else:
                    tc = self._tc

            # Set the current measurement power
            i += 1
            self._hot = not self._hot
            data = np.array(self._raw[i][:s])
            data_end = self._raw[i][(e+n):]
            m = self._raw[i][s:e]
            i += 1

            # Read ahead to use the first data record
            if count == 1:
                if self._hot:
                    h = self._raw[i][s:e]

                    if not with_hkp:
                        th = self._th
                    elif self._raw[i][1] > 0:
                        th = self._raw[i][0]
                    else:
                        th = self._th
                else:
                    c = self._raw[i][s:e]
                    if not with_hkp:
                        tc = self._tc
                    elif self._raw[i][0] > 0:
                        tc = self._raw[i][0]
                    else:
                        tc = self._tc

            signal = tc + (m-c)*(th-tc)/(h-c)
            noise = ((th*c-tc*h)/(h-c)).reshape(n, d//n).mean(axis=1)
            data[0] = tc
            data[1] = th

            # Store
            if sweep:
                if not count % sweep_count:
                    count = 1
                    continue
            self._data.append(np.append(np.append(np.append(data, signal),
                                                  noise), data_end))
            self._time.append(self._rawtime[i-1])

            count += 1

    def save(self, filename=None):
        """
        Parameters:
            filename (str or None type):
                Name of the file
        """ 
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
    """**INFO**"""
    def __init__(self, format=eform, error_range=(50, 250)):
        """
        Parameters:
            format (str):
                set the format of the file. Either eform or aform
            error_range (tuple):
                **INFO**
        """
        assert format[0] == '>', "Must use big-endian to read and store data"
        assert format[1] == 'i', "Must use index time-stamp as first variable"

        self._struct = struct.Struct(format)
        self._size = self._struct.size
        self._data_field = 1
        self._get_format(format)
        self._error_range = error_range

    def average_single(self, number_of_spectra=100, number_of_xbin=2,
                       running_average=False):
        """
        Parameters:
            number_of_spectra (int):
                **INFO**
            number_of_xbin (int):
                **INFO**
            running_average (boolean):
                **INFO**
        """
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

            if running_average or j == 0:
                self._time.append([t])
                self._data.append(d)

            if j >= number_of_spectra and running_average:
                self._time[i - number_of_spectra].append(t)
                if j == 0:
                    continue
            elif j == number_of_spectra:
                self._time[-1].append(t)
                j = 0
                continue

            # Average results up
            if running_average:
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

    def average_sweep(self, number_of_xbin=2):
        """
        Parameters:
            number_of_xbin (int):
                **INFO**
        """
        # Storage variables
        self._data = []
        self._time = []
        self._f0 = []

        # Calibration loop
        d = self._format[self._data_field]  # Number of data
        s = self._format[:self._data_field].sum()  # Start of data
        e = s + d  # End of data

        # WARNING: change this to true number...
        f0 = 15

        # Counter
        cf = self._raw[0][f0]
        j = 0
        start = True
        count = []
        for i in range(len(self._rawtime)):
            t = self._rawtime[i]
            d = self._raw[i][s:e]
            f = self._raw[i][f0]
            if any(d < self._error_range[0]) or any(d > self._error_range[1]):
                continue  # Will cause error if all the last data is bad...

            if j == 0:
                self._time.append([t])
                self._data.append(d)
                t_old = t * 1
                j = 1
                start = False
            elif not f == cf or start:
                self._time[-1].append(t_old)
                self._data.append(d)
                self._time.append([t])
                count.append(j)
                j = 1
                t_old = t * 1
                self._f0.append(f)
                cf = f * 1
            elif i == (len(self._rawtime) - 1):
                self._data[-1] = self._data[-1] + d
                self._time[-1].append(t_old)
                j += 1
                count.append(j)
            else:
                self._data[-1] = self._data[-1] + d
                j += 1
                t_old = t * 1

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
        for i in range(len(self._data)):
            self._data[i] /= count[i]

    def mean(self, number_of_xbin=4):
        """
        Parameters:
            number_of_xbin (int):
                **INFO**
        """
        self._time = [self._rawtime[0], self._rawtime[-1]]

        # Calibration loop
        d = self._format[self._data_field]  # Number of data
        s = self._format[:self._data_field].sum()  # Start of data
        e = s + d  # End of data

        first = True
        for i in range(len(self._rawtime)):
            d = self._raw[i][s:e]
            if first:
                self._data = d
                first = not first
            else:
                self._data = self._data + d

        self._data = self._data / len(self._rawtime)

        first = True
        while self._data.shape[0] % number_of_xbin:
            if first:
                self._data = np.delete(self._data, 0)
            else:
                self._data = np.delete(self._data, -1)
            first = not first
        s = (len(self._data) // number_of_xbin, number_of_xbin)
        self._data = self._data.reshape(s).mean(axis=1)

    def save(self, filename=None):
        """
        Parameters:
            filename (str or None type):
                Name of the file where to save
        """ 
        if not filename:
            filename = self._filename

        # New file format is npy
        if '.clb' in filename[-4:]:
            filename = filename.replace('.clb', '.npy')
        elif '.npy' not in filename[-4:]:
            filename += '.npy'

        try:
            np.save(filename, [self._time, self._f0, self._data])
        except:
            np.save(filename, [self._time, self._data])

    def save_movie(self, filename, ylim=None, xlim=None, fps=60,
                   artist='Average', title='Spectral Data',
                   xbin_name='bins', xdata=None):
        """
        Parameters:
            filename (str):
                Name of the file where to save
            ylim (None type):
                **INFO**
            xlim (None type):
                **INFO**
            fps (int):
                Number of image per second
            artist (str):
                **INFO**
            title (str):
                Title of the movie
            xbin_name (str):
                **INFO**
            xdata (str):
                **INFO**
        """
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
    """**INFO**"""
    def __init__(self, formatting):
        """
        Parameters:
            format (str):
                set the format of the file. Either eform or aform
        """
        assert formatting[0] == '>', "Must use big-endian to read and store data"
        assert formatting[1] == 'i', "Must use index time-stamp as first variable"

        self._struct = struct.Struct(formatting)
        self._size = self._struct.size
        self._data_field = 1
        self._get_format(formatting)

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

    def tcold(self):
        """Averages a raw field and returns the vector to check for variations.

        Assumes four fields in CAHA order
        """

        tcold = []

        for x in self._raw:
            tcold.append(x[0])

        return tcold

    def thot(self):
        """Averages a raw field and returns the vector to check for variations.

        Assumes four fields in CAHA order
        """

        thot = []

        for x in self._raw:
            thot.append(x[1])

        return thot

    def append_to_file(self, filename, time, housekeeping, data):
        """
        Parameters:
            filename (str):
                Name of the file where to save
            time (num):
                **INFO**
            housekeeping (**INFO**):
                **INFO**
            data (**INFO**):
                **INFO**
        """
        # print("appending time")
        p = struct.pack('>I', time)

        # print("appending housekeeping")
        p += struct.pack('>'+str(self._format[0])+'f', *housekeeping)

        # print("appending data")
        p += struct.pack('>'+str(self._format[1])+'f', *data)

        # print("appending noise")
        s = self._format[-3]
        p += struct.pack('>'+str(s)+'f', *np.zeros((s)))

        # print("appending filters")
        s = self._format[-1]+self._format[-2]
        p += struct.pack('>'+str(s)+'f', *np.zeros((s)))

        if os.path.exists(filename):
            a = open(filename, 'ab')
        else:
            a = open(filename, 'wb')
        a.write(p)
        a.close()

    def append_to_testfile(self, filename, time, housekeeping, data, test):
        """
        Parameters:
            filename (str):
                Name of the file where to save
            time (num):
                **INFO**
            housekeeping (**INFO**):
                **INFO**
            data (**INFO**):
                **INFO**
        """
        # print("appending time")
        p = struct.pack('>I', time)

        # print("appending housekeeping")
        p += struct.pack('>'+str(self._format[0])+'f', *housekeeping)

        # print("appending data")
        p += struct.pack('>'+str(self._format[1])+'f', *data)

        # print("appending test")
        p += struct.pack('>'+str(self._format[2])+'i', *test)

        # print("appending noise")
        s = self._format[-3]
        p += struct.pack('>'+str(s)+'f', *np.zeros((s)))

        # print("appending filters")
        s = self._format[-1]+self._format[-2]
        p += struct.pack('>'+str(s)+'f', *np.zeros((s)))

        if os.path.exists(filename):
            a = open(filename, 'ab')
        else:
            a = open(filename, 'wb')
        a.write(p)
        a.close()
