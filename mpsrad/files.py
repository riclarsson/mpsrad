#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov 23 16:03:11 2017

Author: Richard Larsson

"""


import struct
import numpy as np
import scipy as sp
import scipy.io
import netCDF4 as nc
try:
    import matplotlib.pyplot as plt
    import matplotlib.animation as animation
except:
    pass
import time
import datetime
import os
import sys


eform = '>i16f7504f100f28f28f'

dform = '>i16f4096f100f28f28f'

aform = '>i16f16388f128f28f28f'

xfftsform = '>i16f65540f128f28f28f'

xform = '>i16f1023f128f28f28f'

xtest2form = '>i16f1023f2065i128f28f28f'

sform = '>i16f10000f'


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
    elif type == 's':
        return sform
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
        self._noise = []
        self._signal = []

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
            noise_array = ((th*c-tc*h)/(h-c))
            noise = noise_array.reshape(n, d//n).mean(axis=1)
            data[0] = tc
            data[1] = th

            # Store
            if sweep:
                if not count % sweep_count:
                    count = 1
                    continue
            self._noise.append(noise_array)
            self._signal.append(signal)
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
    def __init__(self, format=eform):
        """
        Parameters:
            format (str):
                set the format of the file. Either eform or aform
        """
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

    def append_to_swictsfile(self, filename, time, housekeeping, data):
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

        if os.path.exists(filename):
            a = open(filename, 'ab')
        else:
            a = open(filename, 'wb')
        a.write(p)
        a.close()

class raw_nc:
    """ Class for saving raw data to netcdf format

        The first call to "save" will create an appendable
        file with all the data that is sent into the file.

        Subsequent calls appends to the file.

        Input:
            filename: name of new file to save data within
    """
    def __init__(self, filename, size=None):
        self.filename = filename
        self.new = True
        self.size = size
        self.pos = 0

    def __repr__(self):
        return self.filename
    __str__ = __repr__

    def save(self, data, source=None, recordslen=1):
        """ Save dict of data to file

        If this is the first call to "save", the dimensions of
        all the tables are first created and then the data is
        written to the list by the name of the variable.

        Otherwise, the data is appended at the end of the file.

        Note that the input data must be the same form as the
        first save.

        NaN inputs are turned into standard np.nan_to_num

        Input:
            data: dict of data to be stored

            source: attribute added to netcdf if not None

        """
        assert self.size is not None, "Need to initialize size"

        t0 = time.time()
        now = datetime.datetime.fromtimestamp(t0).strftime("%Y-%m-%d %H:%M:%S")

        while (time.time() - t0) < 5:
            try:
                f = nc.Dataset(self.filename, 'w' if self.new else 'a')
                break
            except:
                time.sleep(0.1)  # Sleeps for half the time that read-access sleeps for

        try:
            if source is not None:
                f.source = source
        except:
            raise RuntimeError("Tried reading file {} for 5 seconds but cannot open it".format(self.filename))

        if self.new:
            f.createDimension('records', self.size)
            f.createDimension('spectras', recordslen)

            dims = []
            input = []
            for key in data:
                if len(data[key]) not in dims:
                    dims.append(len(data[key]))
                    if len(data[key]) == 1:
                        f.createDimension('one', 1)
                    elif len(data[key]) == 2:
                        f.createDimension('two', 2)
                    elif key == 'record':
                        f.createDimension('channels', len(data[key])//recordslen)
                    else:
                        f.createDimension('n' + key, len(data[key]))

                if len(data[key]) == 1:
                    input.append(f.createVariable(key, type(data[key][0]), ('records', 'one')))
                elif len(data[key]) == 2:
                    input.append(f.createVariable(key, type(data[key][0]), ('records', 'two')))
                elif key == 'record':
                    input.append(f.createVariable(key, type(data[key][0]), ('records', 'spectras', 'channels')))
                else:
                    input.append(f.createVariable(key, type(data[key][0]), ('records', 'n'+key)))

            f.start_time = now

        for key in data:
            var = f.variables[key]

            if key == 'record':
                var[self.pos] = np.reshape(np.nan_to_num(data[key]), (recordslen, len(data[key])//recordslen))
            else:
                var[self.pos] = np.nan_to_num(data[key])

        f.end_time = now

        f.pos = self.pos
        f.close()

        self.pos += 1
        self.new = False

    def save_full(self, data, source=None):
        now = datetime.datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d %H:%M:%S")

        f = nc.Dataset(self.filename, 'w')

        if source is not None:
            f.source = source

        n = self.size
        for key in data:
            if data[key].shape[0] != n:
                raise RuntimeError("Bad sizes, size input {} does not match size of \"{}\", which is {}".format(n, key, data[key].shape[0]))

        f.createDimension('records', n)
        dims = []
        input = []

        for key in data:
            if data[key].shape[-1] not in dims:
                dims.append(data[key].shape[-1])

                if data[key].shape[-1] == 1:
                    f.createDimension('one', 1)
                elif data[key].shape[-1] == 2:
                    f.createDimension('two', 2)
                elif key == 'record':
                    f.createDimension('channels', data[key].shape[-1])
                    if len(data['record'].shape) == 3:
                        f.createDimension('spectras', data[key].shape[-2])
                    else:
                        f.createDimension('spectras', 1)
                else:
                    f.createDimension('n' + key, data[key].shape[-1])

            if data[key].shape[-1] == 1:
                input.append(f.createVariable(key, type(data[key][0, 0]), ('records', 'one')))
            elif data[key].shape[-1] == 2:
                input.append(f.createVariable(key, type(data[key][0, 0]), ('records', 'two')))
            elif key == 'record':
                input.append(f.createVariable(key, type(data[key][0, 0]), ('records', 'spectras', 'channels')))
            else:
                input.append(f.createVariable(key, type(data[key][0, 0]), ('records', 'n'+key)))

            input[-1][:] = np.nan_to_num(data[key])

        f.start_time = datetime.datetime.fromtimestamp(data['time'][0, 0]).strftime("%Y-%m-%d %H:%M:%S")
        f.end_time = datetime.datetime.fromtimestamp(data['time'][-1, 0]).strftime("%Y-%m-%d %H:%M:%S")

        f.close()

        self.new = False

    def append_attribute(self, attr, attr_value):
        t0 = time.time()
        while (time.time() - t0) < 5:
            try:
                data = nc.Dataset(self.filename, 'r+')
                data.__setattr__(attr, attr_value)
                data.close()
                return 0
            except:
                time.sleep(0.1)
        raise RuntimeError("Cannot comply with command")

    def __len__(self):
        t0 = time.time()
        while (time.time() - t0) < 10:
            try:
                data = nc.Dataset(self.filename, 'r')
                n = data.dimensions['records'].size
                data.close()
                return n
            except:
                time.sleep(0.2)
        raise RuntimeError("Cannot comply with command")

    def __repr__(self):
        t0 = time.time()
        while (time.time() - t0) < 10:
            try:
                data = nc.Dataset(self.filename, 'r')
                s = str(data)
                data.close()
                return s
            except:
                time.sleep(0.2)
        raise RuntimeError("Cannot comply with command")

    __str__ = __repr__

    def get_variable(self, var, pos1=None, pos2=None):
        t0 = time.time()
        while (time.time() - t0) < 10:
            try:
                data = nc.Dataset(self.filename, 'r')
                if pos1 is not None:
                    if pos2 is not None:
                        x = data.variables[var][pos1, pos2].data
                    else:
                        x = data.variables[var][pos1].data
                elif pos2 is not None:
                    x = data.variables[var][:, pos2].data
                else:
                    x = data.variables[var][:].data
                data.close()
                return x
            except:
                time.sleep(0.2)
        raise RuntimeError("Cannot comply with command")

    def has_variable(self, var):
        t0 = time.time()
        while (time.time() - t0) < 10:
            try:
                data = nc.Dataset(self.filename, 'r')
                x = var in data.variables
                data.close()
                return x
            except:
                time.sleep(0.2)
        raise RuntimeError("Cannot comply with command")

    def variables(self):
        t0 = time.time()
        while (time.time() - t0) < 10:
            try:
                data = nc.Dataset(self.filename, 'r')
                x = list(data.variables.keys())
                data.close()
                return x
            except:
                time.sleep(0.2)
        raise RuntimeError("Cannot comply with command")

    def variable_dimensions(self, var):
        t0 = time.time()
        while (time.time() - t0) < 10:
            try:
                data = nc.Dataset(self.filename, 'r')
                x = data.variables[var].dimensions
                data.close()
                return x
            except:
                time.sleep(0.2)
        raise RuntimeError("Cannot comply with command")

    def variable_dtype(self, var):
        t0 = time.time()
        while (time.time() - t0) < 10:
            try:
                data = nc.Dataset(self.filename, 'r')
                x = data.variables[var].dtype
                data.close()
                return x
            except:
                time.sleep(0.2)
        raise RuntimeError("Cannot comply with command")

    def get_dimension(self, dim):
        t0 = time.time()
        while (time.time() - t0) < 10:
            try:
                data = nc.Dataset(self.filename, 'r')
                d = data.dimensions[dim].size
                data.close()
                return d
            except:
                time.sleep(0.2)
        raise RuntimeError("Cannot comply with command")

    def has_dimension(self, dim):
        t0 = time.time()
        while (time.time() - t0) < 10:
            try:
                data = nc.Dataset(self.filename, 'r')
                d = dim in data.dimensions
                data.close()
                return d
            except:
                time.sleep(0.2)
        raise RuntimeError("Cannot comply with command")

    def dimensions(self):
        t0 = time.time()
        while (time.time() - t0) < 10:
            try:
                data = nc.Dataset(self.filename, 'r')
                d = list(data.dimensions.keys())
                data.close()
                return d
            except:
                time.sleep(0.2)
        raise RuntimeError("Cannot comply with command")

    def get_attribute(self, attr):
        t0 = time.time()
        while (time.time() - t0) < 10:
            try:
                data = nc.Dataset(self.filename, 'r')
                a = data.__getattribute__(attr)
                data.close()
                return a
            except:
                time.sleep(0.2)
        raise RuntimeError("Cannot comply with command")

    def has_attribute(self, attr):
        t0 = time.time()
        while (time.time() - t0) < 10:
            try:
                data = nc.Dataset(self.filename, 'r')
                a = attr in dir(data)
                data.close()
                return a
            except:
                time.sleep(0.2)
        raise RuntimeError("Cannot comply with command")

    def get_pos(self):
        return self.get_attribute('pos') if self.has_attribute('pos') else (self.get_dimension("records") - 1)


def raw2nc(record, datapos, fname_in, fname_out):
    """ Converts a raw file to a netcdf file

        Takes a file of standard raw-form, which is a single 32bit
        integer representing the time followed by X number of 32bit
        floating point numbers.  Converts said file to a netcdf form
        data, where time is stored as a double instead (for future
        compatibilities).

        Input:
            record (string):
                Input for binary data accepted by struct.Struct to
                get the size of one record.  Will fail if the number
                of bits in the input file is not a multiple of the number
                of bits represented by the record.  Note that big endian
                means that ">" must be added at the front of the
               record-string

            datapos (dict):
                dict of named positions for the data in the record.
                The form of this input should be {"DATA": [POS_START-1,
                POS_END-1], ...}.  It is encouraged to name the main
                channels "record", the cold load "cold_load", and
                the hot load as "hot_load".  If "time" is in the list
                it is ignored.  Note that the "-1" above means that
                the first position after the time is indexed as 0.

            fname_in (string):
                file name of the input standard raw file.  Is saved
                to the attributes of the netcdf file

            fname_out (string):
                file name of the output netcdf file.  Cannot be the
                same as fname_in

    """
    assert fname_in != fname_out, "Cannot overwrite file"

    self_struct = struct.Struct(record)
    size = self_struct.size

    s = os.stat(fname_in).st_size

    if s % size:
        raise RuntimeError("Bad size from {} for {}.  Sizes: {} and {}, leaves {} unused bits".format(record, fname_in, s, size, s % size))

    raws = []
    times = []
    nbits = 0
    with open(fname_in, 'rb') as file:
        while True and s > 0:
            try:
                times.append(np.frombuffer(file.read(4), '>i4' if record[0] == '>' else 'i4')[0])
                raws.append(np.float32(np.frombuffer(file.read(size-4), '>f4' if record[0] == '>' else 'f4')))
                nbits += size
                if nbits >= s:
                    break
            except:
                raise RuntimeError("Error in reading file. Wrong bitcount")

    fout = raw_nc(fname_out, len(times))

    data = {"time": np.reshape(np.float64(times), (len(times), 1))}
    raws = np.stack(raws, axis=0)

    for key in datapos:
        if key == 'time':
            pass
        else:
            data[key] = np.array(raws[:, datapos[key][0]:datapos[key][1]], np.float32)

    fout.save_full(data, fname_in)


def nc2raw(datapos, fname_in, fname_out):
    """ Takes a netcdf file and writes a standard raw-form file

        Creates a buffer for every 'records' in the input netcdf
        file.  This buffer is printed with each variable in big
        endian mode to the output raw-form file.

        Input:
            datapos (list):
                An ordered list of strings and integers to create the
                raw data.  If the list-variable is a string, the values
                from the netcdf input file is written in full to the buffer.
                If the list-variable is an integer, 4 times as many zeroes
                are written to the buffer (i.e., representing a 32 bit
                value)

            fname_in (string):
                Filename of the netcdf file

            fname_out (string):
                Filename of the output raw-form file.  Cannot be same
                as fname_in
    """
    assert fname_in != fname_out, "Cannot overwrite file"

    endianness_map = {
    '>': 'big',
    '<': 'little',
    '=': sys.byteorder,
    '|': 'not applicable',
    }

    f = nc.Dataset(fname_in, "r")
    a = open(fname_out, "wb")

    n = f.variables['time'].shape[0]
    for i in range(n):
        buffer = np.array([int(f.variables['time'][i, 0])], '>i4').tobytes()
        for x in datapos:
           if isinstance(x, str):
               if x == 'time':
                   continue
               var = f.variables[x][i, :].flatten()
               if endianness_map[var.dtype.byteorder] == 'little':
                   var = var.byteswap()
               buffer += var.tobytes()
           else:
               buffer += np.zeros((int(x)), '>i4').tobytes()
        a.write(buffer)

    a.close()
    f.close()
