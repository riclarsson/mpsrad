#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 17 08:16:15 2019

@author: larsson
"""


import os
import datetime
import netCDF4 as nc
import numpy as np
from mpsrad.files import raw_nc


def calibrate(self, pc, ph, pm, tc, th, noise=False):
    """ Returns calibrated spectra

        If noise is True returns calibration noise temperature
        instead.

        Input:
            pc: power or count of cold load

            ph: power or count of hot load

            pm: power or count of measurement, the target of the
                calibration

            tc: temperature of the cold load

            th: temperature of the hot load

            noise: returns noise temperature if True or calibrated
                   spectra elsewise
    """

    if (pc is None) or (pm is None) or (ph is None) or (tc is None) or (th is None):
        return None
    elif noise:
        return (th*pc - tc*ph) / (ph-pc)
    else:
        return tc + (pm-pc) * (th-tc) / (ph-pc)


class trp_corr:
    def __init__(self, trp_target, trp_temp=273.15, method="median"):
        self.target = trp_target
        self.T0 = trp_temp
        self.method = method

    def __call__(self, spec):
        if self.method == "median":
            return self.by_median(spec)
        else:
            assert False, "Cannot understand method"

    def by_median(self, spec):
        spec0 = np.median(spec)
        div = self.T0 - self.target

        pt = np.exp(- np.log((self.T0 - spec0) / div))

        if not np.isnan(pt) and not np.isinf(pt) and not np.isnan(spec0) and not np.isinf(spec0):
            return spec * pt + self.T0 * (1.0 - pt), spec0, pt
        else:
            return spec, -1, -1


def bindata(x, f, f0, steps=6, do_x=True):
    """Bin the input data

    Input:
        x: data vector (can be None)

        f: freq vector

        f0: line center

        steps: number of steps before doubling step-size

        do_x:  Set False if x is expected to be None

    Output:
        xbin: Binned data vector (if do_x)

        fbin: Binned freq vector
    """
    n = len(f)
    if do_x:
        assert n == len(x)

    if f0 in f:
        f0bin = np.where(f == f0)[0][0]
    else:
        less = f < f0
        more = f > f0
        if any(less) and any(more):
            f0bin = np.where(more)[0][0]
        elif any(less):
            f0bin = n
        else:
            f0bin = 0

    center = [True]
    fbin = [f0bin+5*steps]
    dn = 2
    while fbin[-1] < n:
        i = 0
        while i < steps and fbin[-1] < n:
            i += 1
            fbin.append(fbin[-1] + dn)
            center.append(False)
        dn *= 2
    fbin[-1] = n

    center.append(True)
    fbin.append(f0bin-5*steps)
    dn = -2
    while fbin[-1] > 0:
        i = 0
        while i < steps and fbin[-1] > 0:
            i += 1
            fbin.append(fbin[-1] + dn)
            center.append(False)
        dn *= 2
    fbin[-1] = 0

    INDS = np.argsort(fbin)
    fbin = np.array(fbin, dtype=int)[INDS]
    center = np.array(center, dtype=bool)[INDS]

    xred = []
    fred = []
    for i in range(1, len(fbin)):
        if (center[i] == center[i-1]) and center[i]:
            for j in range(fbin[i-1], fbin[i]):
                fred.append(f[j])
                if do_x:
                    xred.append(x[j])
        else:
            fred.append(f[fbin[i-1]:fbin[i]].mean())
            if do_x:
                xred.append(x[fbin[i-1]:fbin[i]].mean())
    fred = np.array(fred)
    xred = np.array(xred)
    INDS = np.argsort(fred)

    if do_x:
        return xred[INDS], fred[INDS]
    else:
        return fred[INDS]


class clb_nc:
    def __init__(self, rawfile, version=0.1):
        self.rawfile_name = rawfile
        self.version=version
        self.rawfile = raw_nc(rawfile)

    def pc(self, ind):
        """ Selects the cold load power closest to the index """
        n = self.rawfile.get_pos()
        if ind in range(0, n, 4) and ind+0 <= n:
            return self.rawfile.get_variable("record", ind)
        elif ind in range(1, n, 4) and ind-1 <= n:
            return self.rawfile.get_variable("record", ind-1)
        elif ind in range(2, n, 4) and ind-2 <= n:
            return self.rawfile.get_variable("record", ind-2)
        elif ind in range(3, n, 4) and ind+1 <= n:
            return self.rawfile.get_variable("record", ind+1)
        else:
            return None

    def ph(self, ind):
        """ Selects the hoy load power closest to the index """
        n = self.rawfile.get_pos()
        if ind in range(0, n, 4) and ind <= n:
            return self.rawfile.get_variable("record", ind+2)
        elif ind in range(1, n, 4) and ind-1 <= n:
            return self.rawfile.get_variable("record", ind+1)
        elif ind in range(2, n, 4) and ind-2 <= n:
            return self.rawfile.get_variable("record", ind)
        elif ind in range(3, n, 4) and ind+1 <= n:
            return self.rawfile.get_variable("record", ind-1)
        else:
            return None

    def pm(self, ind):
        """ Selects the measurement power closest to the index """
        n = self.rawfile.get_pos()
        if ind in range(0, n, 2) and ind+1 <= n:
            return self.rawfile.get_variable("record", ind+1)
        elif ind in range(1, n, 2) and ind+0 <= n:
            return self.rawfile.get_variable("record", ind)
        else:
            return None

    def measurement_variable(self, var, ind):
        n = self.rawfile.get_pos()
        if ind in range(0, n, 2) and ind+1 <= n:
            return self.rawfile.get_variable(var, ind+1)
        elif ind in range(1, n, 2) and ind+0 <= n:
            return self.rawfile.get_variable(var, ind)
        else:
            return None

    def tc(self, ind):
        """ Selects the cold load temperature closest to the index and adjusts it by any available offsets """
        n = self.rawfile.get_pos()
        if ind in range(0, n, 4) and ind+0 <= n:
            tc = self.rawfile.get_variable("cold_load", ind, 0)
        elif ind in range(1, n, 4) and ind-1 <= n:
            tc = self.rawfile.get_variable("cold_load", ind-1, 0)
        elif ind in range(2, n, 4) and ind-2 <= n:
            tc = self.rawfile.get_variable("cold_load", ind-2, 0)
        elif ind in range(3, n, 4) and ind+1 <= n:
            tc = self.rawfile.get_variable("cold_load", ind+1, 0)
        else:
            tc = None

        if self.rawfile.has_attribute('cold_load_offset') and tc is not None:
            tc += self.rawfile.get_attribute('cold_load_offset')

        return tc

    def th(self, ind):
        """ Selects the hot load temperature closest to the index and adjusts it by any available offsets """
        n = self.rawfile.get_pos()
        if ind in range(0, n, 4) and ind <= n:
            th = self.rawfile.get_variable("hot_load", ind+2, 0)
        elif ind in range(1, n, 4) and ind-1 <= n:
            th = self.rawfile.get_variable("hot_load", ind+1, 0)
        elif ind in range(2, n, 4) and ind-2 <= n:
            th = self.rawfile.get_variable("hot_load", ind, 0)
        elif ind in range(3, n, 4) and ind+1 <= n:
            th = self.rawfile.get_variable("hot_load", ind-1, 0)
        else:
            th = None

        if self.rawfile.has_attribute('hot_load_offset') and th is not None:
            th += self.rawfile.get_attribute('hot_load_offset')

        return th

    def save_full_clb(self, clbfile):
        """ Saves the calibration to a new calibrated file

            If there is a nextrawfile given, it is used to
            append a final value to the measurement for the
            overlap time
        """
        assert self.rawfile.filename != clbfile, "Bad filenames"
        data = nc.Dataset(clbfile, 'w')

        n = self.rawfile.get_pos()
        if n + 1 == self.rawfile.get_dimension('records'):
            data.createDimension("records", self.rawfile.get_dimension('records')//2)
        else:
            data.createDimension("records", n//2)

        # Add all old dimensions
        for dim in self.rawfile.dimensions():
            if dim != "records":
                data.createDimension(dim, self.rawfile.get_dimension(dim))

        # Add all old variables
        output = {}
        for var in self.rawfile.variables():
            typs = self.rawfile.variable_dtype(var)
            dims = self.rawfile.variable_dimensions(var)
            data.createVariable(var, typs, dims)

            output[var] = []

        # Generate data
        for k in range(data.dimensions['records'].size):
            ind = 2*k + 1  # C[A]H[A], selecting A gives every 2k+1 variable is important
            pc = self.pc(ind)
            ph = self.ph(ind)
            pm = self.pm(ind)
            th = self.th(ind)
            tc = self.tc(ind)
            cal = calibrate(self, pc, ph, pm, tc, th, noise=False)

            if cal is None:
                raise RuntimeError("Bad netcdf conversion")

            # for all variables but record, keep a copy
            for var in self.rawfile.variables():
                if var == 'record':
                    output[var].append(cal)
                else:
                    output[var].append(self.measurement_variable(var, ind))

        # Write variables to file
        for var in self.rawfile.variables():
            data.variables[var][:] = np.array(output[var])

        # Set the standard attributes
        data.version = self.version
        data.source = self.rawfile.get_attribute('source') if self.rawfile.has_attribute('source') else "UNDEFINED"
        data.end_time = self.rawfile.get_attribute('end_time') if self.rawfile.has_attribute('end_time') else "UNDEFINED"
        data.start_time = self.rawfile.get_attribute('start_time') if self.rawfile.has_attribute('start_time') else "UNDEFINED"
        data.hot_load_offset = self.rawfile.get_attribute('hot_load_offset') if self.rawfile.has_attribute('hot_load_offset') else 0.0
        data.cold_load_offset = self.rawfile.get_attribute('cold_load_offset') if self.rawfile.has_attribute('cold_load_offset') else 0.0

        data.close()

    def save_full_red(self, redfile, tropospheric_correction, reduction_method):
        """ Saves the calibration to a new reduced file """
        assert self.rawfile.filename != redfile, "Bad filenames"

        start_ind = reduction_method.get('start_ind', 0)
        end_ind = reduction_method.get('end_ind', -1)

        # Reduced frequencies
        f_orig = reduction_method['freq']
        assert len(f_orig) == self.rawfile.get_dimension('channels'), "Mismatch frequency grid to channels grid"
        f_red = bindata(None, f_orig[start_ind:end_ind], reduction_method['freq0'], reduction_method['steps'], do_x=False)

        data = nc.Dataset(redfile, 'w')

        n = self.rawfile.get_pos()
        if n + 1 == self.rawfile.get_dimension('records'):
            data.createDimension("records", self.rawfile.get_dimension('records')//2 - 1)
        else:
            data.createDimension("records", n//2)

        # Add all old dimensions
        for dim in self.rawfile.dimensions():
            if dim != "records":
                data.createDimension(dim, self.rawfile.get_dimension(dim))

        # Reduced frequency grid
        data.createDimension("reduced_channels", len(f_red))

        # Add all old variables
        output = {}
        for var in self.rawfile.variables():
            typs = self.rawfile.variable_dtype(var)
            dims = self.rawfile.variable_dimensions(var)
            if var == 'record':
                data.createVariable("f_orig", f_orig.dtype, ("channels"))
                output['f_orig'] = f_orig

                data.createVariable("f_red", f_red.dtype, ("reduced_channels"))
                output['f_red'] = f_red

                data.createVariable("median", typs, ("records", "spectras"))
                output["median"] = []

                data.createVariable("pseudo_transmission", typs, ("records", "spectras"))
                output["pseudo_transmission"] = []

                data.createVariable(var, typs, ("records", "spectras", "reduced_channels"))
                output[var] = []

                data.createVariable("mean_cold_count", typs, ("records", "spectras", "one"))
                data.createVariable("mean_hot_count", typs, ("records", "spectras", "one"))
                data.createVariable("mean_atm_count", typs, ("records", "spectras", "one"))
                data.createVariable("mean_cold_temp", typs, ("records", "one"))
                data.createVariable("mean_hot_temp", typs, ("records", "one"))
                output["mean_cold_count"] = []
                output["mean_hot_count"] = []
                output["mean_atm_count"] = []
                output["mean_cold_temp"] = []
                output["mean_hot_temp"] = []
            else:
                data.createVariable(var, typs, dims)
                output[var] = []
        data.sync()

        # Generate data
        for k in range(data.dimensions['records'].size):
            if not k%100:
                print('{}% DONE'.format(round(100*k/data.dimensions['records'].size, 1)))

            ind = 2*k + 1  # C[A]H[A], selecting A gives every 2k+1 variable is important
            pc = np.array(self.pc(ind)[:, start_ind:end_ind])
            ph = np.array(self.ph(ind)[:, start_ind:end_ind])
            pm = np.array(self.pm(ind)[:, start_ind:end_ind])
            tc = np.array(self.tc(ind)) + reduction_method.get('cold', 0.)
            th = np.array(self.th(ind)) + reduction_method.get('hot', 0.)
            cal = calibrate(self, pc, ph, pm, tc, th, noise=False)
            bads, x = bad_val_helper(cal)
            cal[bads]= np.interp(x(bads), x(~bads), cal[~bads])

            output["mean_cold_count"].append(np.mean(pc, axis=1))
            output["mean_hot_count"].append(np.mean(ph, axis=1))
            output["mean_atm_count"].append(np.mean(pm, axis=1))
            output["mean_cold_temp"].append(tc.flatten())
            output["mean_hot_temp"].append(th.flatten())

            if cal is None:
                raise RuntimeError("Bad netcdf conversion")

            # for all variables but record, keep a copy
            for var in self.rawfile.variables():
                if var == 'record':
                    cal0 = np.zeros((self.rawfile.get_dimension("spectras")), dtype="f4")
                    pt = np.zeros((self.rawfile.get_dimension("spectras")), dtype="f4")
                    cal_red = np.zeros((self.rawfile.get_dimension("spectras"), len(f_red)), dtype="f4")
                    for spec in range(self.rawfile.get_dimension("spectras")):
                        c, pt[spec], cal0[spec] = tropospheric_correction(cal[spec])
                        cal_red[spec], _ = bindata(c, f_orig[start_ind:end_ind],
                               reduction_method['freq0'], reduction_method['steps'], do_x=True)
                    output[var].append(cal_red)
                    output["pseudo_transmission"].append(pt)
                    output["median"].append(cal0)
                else:
                    output[var].append(self.measurement_variable(var, ind))

        # Write variables to file
        for var in output:
            data.variables[var][:] = np.array(output[var])

        # Set the standard attributes
        data.version = self.version
        data.source = self.rawfile.get_attribute('source') if self.rawfile.has_attribute('source') else "UNDEFINED"
        data.end_time = self.rawfile.get_attribute('end_time') if self.rawfile.has_attribute('end_time') else "UNDEFINED"
        data.start_time = self.rawfile.get_attribute('start_time') if self.rawfile.has_attribute('start_time') else "UNDEFINED"
        data.hot_load_offset = self.rawfile.get_attribute('hot_load_offset') if self.rawfile.has_attribute('hot_load_offset') else 0.0
        data.cold_load_offset = self.rawfile.get_attribute('cold_load_offset') if self.rawfile.has_attribute('cold_load_offset') else 0.0
        data.orig_filename = self.rawfile.filename

        data.sync()
        data.close()

def timegroup(timelist, times):
    for i in range(len(timelist)-1):
        hl = timelist[i]
        hh = timelist[i+1]
        if times >= hl and times < hh:
            return i
    return len(timelist)-1


def minute(r, min):
    try:
        time = r['TIME'].flatten()
        n = r.n
    except:
        time = r
        n = len(r)

    t0 = datetime.datetime.fromtimestamp(time[0])
    start = 0

    minutes = np.linspace(0, 60-min, 60//min)
    g0 = timegroup(minutes, t0.minute)

    inds = [start]
    for i in range(start, n):
        t = datetime.datetime.fromtimestamp(time[i])
        g = timegroup(minutes, t.minute)

        if t0.day != t.day or g != g0:
            g0 = g
            t0 = t
            inds.append(i)
    return inds


def hour(r, h):
    try:
        time = r['TIME'].flatten()
        n = r.n
    except:
        time = r
        n = len(r)

    t0 = datetime.datetime.fromtimestamp(time[0])
    start = 0

    hours = np.linspace(0, 24-h, 24//h)
    g0 = timegroup(hours, t0.hour)

    inds = [start]
    for i in range(start, n):
        t = datetime.datetime.fromtimestamp(time[i])
        g = timegroup(hours, t.hour)

        if t0.day != t.day or g != g0:
            g0 = g
            t0 = t
            inds.append(i)
    return inds


def days(r, days):
    try:
        time = r['TIME'].flatten()
        n = r.n
    except:
        time = r
        n = len(r)

    t0 = datetime.datetime.fromtimestamp(time[0])
    start = 0

    inds = [start]
    for i in range(start, n):
        t = datetime.datetime.fromtimestamp(time[i])

        if (days+t0.day) <= t.day:
            t0 = t
            inds.append(i)
    return inds


def minutely(r):
    return minute(r, 1)


def one_minutely(r):
    return minute(r, 1)


def per_minute(r):
    return minute(r, 1)


def two_minutely(r):
    return minute(r, 2)


def three_minutely(r):
    return minute(r, 3)


def five_minutely(r):
    return minute(r, 5)


def six_minutely(r):
    return minute(r, 6)


def ten_minutely(r):
    return minute(r, 10)


def twelve_minutely(r):
    return minute(r, 12)


def quarter_hourly(r):
    return minute(r, 15)


def fifteen_minutely(r):
    return minute(r, 15)


def twenty_minutely(r):
    return minute(r, 20)


def thirty_minutely(r):
    return minute(r, 30)


def half_hourly(r):
    return minute(r, 30)


def hourly(r):
    return hour(r, 1)


def one_hourly(r):
    return hour(r, 1)


def two_hourly(r):
    return hour(r, 2)


def three_hourly(r):
    return hour(r, 3)


def four_hourly(r):
    return hour(r, 4)


def six_hourly(r):
    return hour(r, 6)


def twelve_hourly(r):
    return hour(r, 12)


def daily(r):
    return days(r, 1)


def bi_daily(r):
    return days(r, 2)


def weekly(r):
    return days(r, 7)


class timescale:
    def __init__(self, types):
        self.types = types

    def __call__(self, list_of_files):
        times = np.array([])
        files = []
        for fil in list_of_files:
            x = nc.Dataset(fil, 'r')

            tn = x.variables['time'][:].flatten()
            x.close()

            files.append([fil, len(tn)])
            times = np.append(times, tn)

        inds = {}
        if not files:
            for key in self.types:
                inds[key] = {}
            return inds

        for key in self.types:
            inds[key] = {}

            if key == 'minute':
                s = minutely(times)
            elif key == 'two_minutes':
                s = two_minutely(times)
            elif key == 'five_minutes':
                s = five_minutely(times)
            elif key == 'quarter':
                s = fifteen_minutely(times)
            elif key == 'hour':
                s = hourly(times)
            elif key == 'two_hours':
                s = two_hourly(times)
            elif key == 'day':
                s = daily(times)
            else:
                raise Warning("Did not find the time-key: {}".format(key))
                s = None

            if s is None:
                continue

            # For all the times
            for i in range(len(s)-1):
                month = datetime.datetime.fromtimestamp(times[s[i]]).strftime("%Y-%m")
                if month not in inds[key]:
                    inds[key][month] = [[s[i], s[i+1]]]
                else:
                    inds[key][month].append([s[i], s[i+1]])

                # Append all the files and append those that fits the time range
                n = 0
                for filedata in files:
                    file = filedata[0]
                    filelen = filedata[1]

                    if n < s[i] and s[i] <= (n+filelen):
                        inds[key][month][-1].append(file)
                    elif n < s[i+1] and s[i+1] <= (n+filelen):
                        inds[key][month][-1].append(file)

                    n += filelen
        return inds, times


def data_by_inds(ncdata, start, end):
    s = {}
    for key in ncdata.variables:
        if 'records' in ncdata.variables[key].dimensions:
            s[key] = ncdata.variables[key][start: end]
        else:
            s[key] = ncdata.variables[key][:]
    return s


def redfiles2prodir(redfiles, prodir, timescale, std=True):
    redfiles.sort()
    # Represent when and how in a file that a timescale is encountered from a list of files, will start from full timescale
    inds, times = timescale(redfiles)
    #  Here:
    #  inds = {TIMESCALE_1: {
    #              PROFILE_1: [[START_IND, END_IND, FILE1, FILE2, ...], [START_IND, END_IND, FILE1, FILE2, ...], ...],
    #              PROFILE_2: [[START_IND, END_IND, FILE1, FILE2, ...], [START_IND, END_IND, FILE1, FILE2, ...], ...],
    #              ...... },
    #          TIMESCALE_2: {
    #              PROFILE_1: [[START_IND, END_IND, FILE1, FILE2, ...], [START_IND, END_IND, FILE1, FILE2, ...], ...],
    #              PROFILE_2: [[START_IND, END_IND, FILE1, FILE2, ...], [START_IND, END_IND, FILE1, FILE2, ...], ...],
    #              ...... },
    #          ...... }
    # where each "TIMESCALE_X" is a timescale and "PROFILE_X" is a monthly name.
    # The list of each "PROFILE_X" is a list of files that combines to a single
    # entry in the saved profile.


    x = nc.Dataset(redfiles[0], 'r')
    source = x.source
    x.close()

    version = None
    for scale in inds:
        n = 0
        ts = inds[scale]

        for profile in ts:
            profilename = "{}/pro-{}-{}-{}.nc".format(prodir, source.replace(' ', '-'), profile, scale)
            save_file = nc.Dataset(profilename, 'w')

            prolist = ts[profile]

            fnames = []

            for i in range(len(prolist)):
#                print(profile, ' ', 100*i/len(prolist), '%', sep='')
                entrylist = prolist[i]
                start = entrylist[0]
                end = entrylist[1]

                if len(entrylist) == 3:
#                    print(start-n, end-n)
                    redfile = nc.Dataset(entrylist[2], 'r')
                    avg = data_by_inds(redfile, start-n, end-n)
                else:
                    for fileind in range(2, len(entrylist)):
                        fname = entrylist[fileind]
                        if fname not in fnames:
                            fnames.append(fname)
                        redfile = nc.Dataset(fname, 'r')
                        this_n = redfile.dimensions['records'].size

                        if fileind == len(entrylist) - 1:
                            tmp_avg = data_by_inds(redfile, 0, end-start)
                            for key in avg:
                                avg[key] = np.append(avg[key], tmp_avg[key], axis=0)
                        elif fileind == 2:
                            avg = data_by_inds(redfile, start-n, -1)
                            n += this_n
                        else:
                            tmp_avg = data_by_inds(redfile, 0, -1)
                            n += this_n
                            for key in avg:
                                avg[key] = np.append(avg[key], tmp_avg[key], axis=0)

                if version is not None and version != redfile.version:
                    print("Warning: different version numbers in redfiles")
                else:
                    version = redfile.version

                # Create the dimensions and variables
                if not i:
                    # Create all dimensions
                    save_file.createDimension('records', len(prolist))
                    for key in redfile.dimensions:
                        if key != 'records':
                            save_file.createDimension(key,
                                                      redfile.dimensions[key].size)

                    # Create all variables
                    save_file.createVariable('covmat_sy',
                                             redfile.variables['record'].dtype,
                                             ['records', 'spectras', 'reduced_channels'] if std else
                                             ['records', 'spectras', 'reduced_channels', 'reduced_channels'])
                    for key in avg:
                        save_file.createVariable(key,
                                                 redfile.variables[key].dtype,
                                                 redfile.variables[key].dimensions)

#                for key in avg:
#                    print(key, avg[key].shape)
#                print('\n')

                # Save to file
                for j in range(save_file.dimensions['spectras'].size):
                    if std:
                        std_data = np.float32(np.std(avg['record'][:, j], axis=0))
                    else:
                        std_data = np.float32(np.cov(avg['record'][:, j].T))

                    std_data /= avg['record'].shape[0] - 1
                    save_file.variables['covmat_sy'][i, j, :] = std_data

                for key in avg:
                    if 'records' in save_file.variables[key].dimensions:
                        save_file.variables[key][i] = np.mean(avg[key], axis=0)
                    else:
                        try:
                            save_file.variables[key][:] = avg[key]
                        except:
                            pass

            if len(prolist):
                save_file.version = version

                # fnames = np.unique(fnames)
                # origfiles = ''
                # for fname in fnames:
                #    origfiles+= '{};'.format(fname)
                # save_file.original_files = origfiles

                try:
                    save_file.start_time = datetime.datetime.fromtimestamp(save_file.variables['time'][0][0]).strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    save_file.start_time = "UNKNOWN"

                try:
                    save_file.end_time = datetime.datetime.fromtimestamp(save_file.variables['time'][-1][0]).strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    save_file.end_time = "UNKNOWN"

                try:
                    save_file.source = redfile.source
                except:
                    save_file.source = "UNKNOWN"
            save_file.close()


def rawfiles2redfiles(rawfiles, reddir, corr_target=3.5, corr_trp_temp=273.15,
                      corr_method="median", red_f=np.array([-1, 1]), red_f0=0,
                      red_steps=10, start_ind=0, end_ind=-1,
                      cold_offset=0., hot_offset=0.):
    trp = trp_corr(trp_target=corr_target, trp_temp=corr_trp_temp,  method=corr_method)
    red = {"freq0": red_f0, 'freq': red_f, 'steps': red_steps, "start_ind": start_ind,
           "end_ind": end_ind, "cold": cold_offset, "hot": hot_offset}

    for rawfile in rawfiles:
        try:
            print("Doing", rawfile)
            clb = clb_nc(rawfile)

            fname = os.path.join(reddir,
                                 'red.' + os.path.split(rawfile)[-1])

            clb.save_full_red(fname, trp, red)
        except:
            pass


def profile2invfile(profile, invfile, p_grid, f_adjust, covmat_sx, atmdir, linefile, inv_func, truncate=True):
    assert len(p_grid) == covmat_sx.shape[0], "Bad dims or types"
    assert len(p_grid) == covmat_sx.shape[1], "Bad dims or types"

    if os.path.exists(invfile):
        os.system('rm {}'.format(invfile))

    # Read all necessary data
    data = nc.Dataset(profile, 'r')
    t = np.array(data.variables['time'])
    y = np.array(data.variables['record'])
    covmat_sy = np.array(data.variables['covmat_sy'])
    f = np.array(data.variables['f_red']) + f_adjust
    fo = np.array(data.variables['f_orig']) + f_adjust
    try:
        source = data.source
    except:
        source = "UNKNOWN"
    try:
        version = data.version
    except:
        version = 0.
    try:
        start_time = data.start_time
    except:
        start_time = "UNKNOWN"
    try:
        end_time = data.end_time
    except:
        end_time = "UNKNOWN"
    data.close()

    # Create the file to write towards
    outfile = nc.Dataset(invfile, 'w')

    # Create the dimensions
    outfile.createDimension('one', 1)
    outfile.createDimension('altitudes', len(p_grid))
    outfile.createDimension('records', covmat_sy.shape[0])
    outfile.createDimension('spectras', covmat_sy.shape[1])
    outfile.createDimension('reduced_channels', len(f))
    outfile.createDimension('channels', len(fo))
    outfile.std = int(len(covmat_sy.shape) == 3)
    outfile.source = source
    outfile.version = version
    outfile.start_time = start_time
    outfile.end_time = end_time

    # Create the variables that are known at start
    outfile.createVariable('y', np.float32, ('records', 'spectras', 'reduced_channels'))
    outfile.createVariable('time', np.float64, ('records', 'one'))
    outfile.createVariable('f_red', np.float32, ('reduced_channels'))
    outfile.createVariable('f_orig', np.float32, ('channels'))
    if outfile.std:
        outfile.createVariable('covmat_sy', np.float32, ('records', 'spectras', 'reduced_channels'))
    else:
        outfile.createVariable('covmat_sy', np.float32, ('records', 'spectras', 'reduced_channels', 'reduced_channels'))
    outfile.createVariable('covmat_sx', np.float32, ('altitudes', 'altitudes'))
    outfile.createVariable('p_grid', np.float32, ('altitudes'))

    # Fill the variables that are known at start
    outfile.variables['y'][:] = y
    outfile.variables['time'][:] = t
    outfile.variables['covmat_sy'][:] = covmat_sy
    outfile.variables['covmat_sx'][:] = covmat_sx
    outfile.variables['p_grid'][:] = p_grid
    outfile.variables['f_red'][:] = f
    outfile.variables['f_orig'][:] = fo

    done_a_loop = False
    for i in range(outfile.dimensions['records'].size):
        print(invfile, ' ',
              round(100 * i / outfile.dimensions['records'].size, 1),
              '% done', sep='')
        for j in range(outfile.dimensions['spectras'].size):

            if any(np.isnan(y[i][j])) or any(np.isnan(covmat_sy[i][j])):
                continue

            out = inv_func(np.float64(y[i][j]), np.float64(f), np.float64(p_grid),
                           np.float64(covmat_sy[i][j]), np.float64(covmat_sx), atmdir, linefile)

            if not done_a_loop:
                outfile.createVariable('f_grid', np.float64, ('reduced_channels'))
                outfile.variables['f_grid'][:] = out['f']

                outfile.createDimension('retrieval_grid', len(out['xa']))
                outfile.createVariable('xa', np.float64, ('retrieval_grid'))
                outfile.variables['xa'][:] = out['xa']

                outfile.createDimension('diags', len(out['diag']))
                outfile.createVariable('diag', np.float64, ('records', 'spectras', 'diags'))

                outfile.createVariable('x', np.float64, ('records', 'spectras', 'retrieval_grid'))
                outfile.createVariable('fx', np.float64, ('records', 'spectras', 'reduced_channels'))
                outfile.createVariable('yf', np.float64, ('records', 'spectras', 'reduced_channels'))
                outfile.createVariable('y_baseline', np.float64, ('records', 'spectras', 'reduced_channels'))
                outfile.createVariable('G', np.float64, ('records', 'spectras', 'retrieval_grid', 'reduced_channels'))
                outfile.createVariable('J', np.float64, ('records', 'spectras', 'reduced_channels', 'retrieval_grid'))
                outfile.createVariable('avk', np.float64, ('records', 'spectras', 'retrieval_grid', 'retrieval_grid'))
                outfile.createVariable('covmat_ss', np.float64, ('records', 'spectras', 'retrieval_grid', 'retrieval_grid'))
                outfile.createVariable('covmat_so', np.float64, ('records', 'spectras', 'retrieval_grid', 'retrieval_grid'))

                outfile.description = out['description']

                done_a_loop = True

            outfile.variables['x'][i,j] = out['x']
            outfile.variables['fx'][i,j] = out['y']
            outfile.variables['yf'][i,j] = out['yf']
            outfile.variables['y_baseline'][i,j] = out['y_baseline']
            outfile.variables['G'][i,j] = out['G']
            outfile.variables['J'][i,j] = out['J']
            outfile.variables['avk'][i,j] = out['avk']
            outfile.variables['covmat_ss'][i,j] = out['covmat_ss']
            outfile.variables['covmat_so'][i,j] = out['covmat_so']
            outfile.variables['diag'][i,j] = out['diag']

    outfile.close()


def bad_val_helper(y):
    """Helper to handle indices and logical indices of NaNs.

    Input:
        - y, 1d numpy array with possible NaNs
    Output:
        - bads, logical indices of Bad Values
        - index, a function, with signature indices= index(logical_indices),
          to convert logical indices of NaNs to 'equivalent' indices
    Example:
        >>> # linear interpolation of NaNs
        >>> bads, x= bad_val_helper(y)
        >>> y[nans]= np.interp(x(bads), x(~bads), y[~bads])
    """

    return np.logical_not(np.isfinite(y)), lambda z: z.nonzero()[0]
