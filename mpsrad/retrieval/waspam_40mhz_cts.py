#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 17 13:53:17 2019

@author: dabrowski
"""


from typhon.arts.workspace import Workspace, arts_agenda
import numpy as np
import numpy.matlib
import scipy as sp
from copy import deepcopy as copy


def _to_same_size(*args):
    """
    Make python floats and numpy.array to numpy.array of same size
    """

    if len(args) == 1:
        if np.isscalar(args[0]):
            return np.array([args[0]])
        else:
            return np.array(args[0])
    one = np.array([1]).shape
    msz = one
    size = []
    out = []

    # Checks the shapes and sizes of things
    for i in args:
        if np.isscalar(i):
            size.append(one)  # scalars are the same as one-long arrays
        else:
            if type([]) == type(i):
                i = np.array(i)  # lists are treated the same as arrays
            sz = i.shape
            size.append(sz)

            # Either (1,) or (n,m,x, ...).  If any other raise a fuss
            if sz == one or msz == sz:
                continue
            elif msz == one:
                msz = sz
            else:
                raise RuntimeError("Only scalars and arrays of the same" +
                                   " length allowed.")

    # Now we can add things to the output
    v = np.ones(msz)
    for ii in range(len(size)):
        if size[ii] == one:
            out.append(v*args[ii])
        else:
            out.append(np.array(args[ii]))

    return tuple(out)


def covmat1d_from_cfun(xp, Std, cfun='exp', Cl=1, cco=0, mapfun=None):
    """
    COVMAT1D_FROM_CFUN   Correlation function based covariance matrix

    This function sets up a covariance matrix from a defined correlation
    function. The correlation function is specified by giving a functional
    form (such as exponential decreasing) and correlation lengths. The
    correlation length is throughout defined as the distance where the
    correlation has dropped to exp(-1). For off-diagonal values, the
    correlation length is averaged between the two involved positions.

    Correlation matrices are obtained by setting *Std* to 1.

    FORMAT   S = covmat1d_from_cfun( xp, Std, cfun, Cl, cco, mapfun )

    OUT
          S
              The covariance matrix as csc sparse from scipy

    IN
          xp
              The data abscissa.

          Std
              Standard deviations. Given as a two column matrix. First column
              holds position in same unit as *xp*. The second column is the
              standard deviation at the postions of the first column. These
              values are then interpolated to *xp*, extrapolating end
              values to +-Inf (in a "nearest" manner).
              If set to a scalar, this value is applied for all *xp*.

           cfun
               Correlation function. Possible choices are:

                   'drc' : Dirac. No correlation. Any given correlation length
                   is ignored here.

                   'lin' : Linearly decreasing (down to zero).

                   'exp' : Exponential decreasing (exp(-dx/cl)).

                   'gau' : Gaussian (normal) deceasing (exp(-(dx/cl))^2).

     OPT
           Cl
               Correlation lengths. Given as a column matrix as *Std*.
               Must be given for all *cfun* beside 'drc'. Extrapolation as
               for *Std*. Scalar input is allowed.

           cco
               Correlation cut-off. All values below this limit are set to 0.

           mapfun
              Mapping function from grid unit to unit for correlation
              lengths. For example, if correlation lengths are given in
              pressure decades, while the basic coordinate is Pa, this is
              *mapfun* handled by setting *mapfun* to np.log10.

    2005-05-20   Created by Patrick Eriksson.
    """

    from copy import deepcopy as copy

    xp = np.broadcast_arrays(xp)[0]

    if not len(xp.shape) == 1:
        raise RuntimeError("xp must be broadcasted as 1-d arrays")

    if not np.isscalar(cco):
        raise RuntimeError("cco must be a scalar")

    if cco < 0 or cco > 1:
        raise RuntimeError("Argument *cco* must be a scalar [0,1]")

    n = len(xp)

    Std = _to_same_size(Std)

    if Std.shape == (0,):
        si = np.ones((n, 1))
    elif Std.shape == (1,):
        si = np.matlib.repmat(Std, 1, n)[0]
    else:
        assert False

    if any(np.isnan(si)):
        raise RuntimeError("NaN obtained when interpolating Std")

    if cfun == "drc":
        S = sp.sparse.csc_matrix(np.diag(si ** 2))
        return S

    if mapfun is not None:
        if isinstance(mapfun, type(np.log)):
            xp = mapfun(xp)
        else:
            raise RuntimeError("Input mapfun must be None or numpy.ufunc.")

        if not np.isscalar(Cl):
            Cl[:, 0] = mapfun(Cl[:, 0])

    (X1, X2) = np.matlib.meshgrid(xp, xp)
    D = abs(X1 - X2)
    if np.isscalar(Cl):
        L = copy(Cl)
    else:
        assert False

    if cfun == "lin":
        S = 1 - (1 - np.exp(- 1)) * (D / L)
    elif cfun == "exp":
        S = np.exp(- D / L)
    elif cfun == "gau":
        S = np.exp(- (D / L) ** 2)
    else:
        raise RuntimeError("Unknown correlation function (" + str(cfun) + ")")

    S[S < cco] = 0

    S *= np.multiply.outer(si, si)
    return sp.sparse.csc_matrix(S)


def sa_matrix_interp(custom_sx, z, sa_orig):
    ppmv = custom_sx['ppmv']
    alts = custom_sx['alts']
    times = custom_sx['times']

    dim = 0 if ppmv.shape[0] == len(times) else 1

    sa_base = np.empty((len(times), len(z)))
    for i in range(len(times)):
        if dim:
            ppm = ppmv[:, i].flatten()
        else:
            ppm = ppmv[i].flatten()
        sa_base[i] = np.interp(z, alts, ppm)

    Sa = np.cov(sa_base.T)
    sa_orig = sa_orig.todense()

    for i in range(len(z)):
        for j in range(len(z)):
            if z[i] > alts.min() and z[j] > alts.min():
                if z[i] < alts.max() and z[j] < alts.max():
                    sa_orig[i, j] = Sa[i, j]
    return sp.sparse.csc.csc_matrix(sa_orig), sa_base.mean(axis=0)


def water_psat_agenda(ws):
    ws.water_p_eq_fieldMK05()


def sensor_response_agenda_waspam(ws):
    ws.AntennaOff()
    ws.sensorOff()
    ws.Ignore(ws.f_backend)


def sensor_response_agenda_iram(ws):
    ws.AntennaOff()
    ws.sensor_norm = 1
    ws.sensor_responseInit()
    ws.sensor_responsePolarisation()
    ws.Ignore(ws.f_backend)

def inversion_iterate_agenda(arts):
    arts.Ignore(arts.inversion_iteration_counter)
    arts.x2artsAtmAndSurf()
    arts.Copy(arts.f_backend, arts.f_grid)
    arts.x2artsSensor()
    arts.atmfields_checkedCalc(negative_vmr_ok=1) # negative_vmr_ok added to avoid error with negative vmr values
    arts.atmgeom_checkedCalc()
    arts.yCalc()
    #arts.jacobianAdjustAndTransform()
    arts.VectorAddVector( arts.yf, arts.y, arts.y_baseline )


def propmat_clearsky_agenda_onthefly(ws):
    ws.propmat_clearskyInit()
    ws.propmat_clearskyAddOnTheFly()
    ws.Ignore(ws.rtp_mag)
    ws.Ignore(ws.rtp_los)


def propmat_clearsky_agenda_zeeman_onthefly(ws):
    ws.propmat_clearskyInit()
    ws.propmat_clearskyAddOnTheFly()
    ws.propmat_clearskyAddZeeman()


def ppath_agenda_step_by_step(ws):
    ws.Ignore(ws.rte_pos2)
    ws.ppathStepByStep()


def iy_main_agenda_emission(ws):
    ws.Ignore(ws.iy_id)
    ws.ppathCalc()
    ws.iyEmissionStandard()


def iy_space_agenda_cosmic_background(ws):
    ws.Ignore(ws.rtp_pos)
    ws.Ignore(ws.rtp_los)
    ws.MatrixCBR(ws.iy, ws.stokes_dim, ws.f_grid)
    ws.iy = ws.iy.value * 0


def iy_surface_agenda(ws):
    ws.SurfaceDummy()
    ws.iySurfaceRtpropAgenda()


def ppath_step_agenda_geometric(ws):
    ws.Ignore(ws.t_field)
    ws.Ignore(ws.vmr_field)
    ws.Ignore(ws.f_grid)
    ws.Ignore(ws.ppath_lraytrace)
    ws.ppath_stepGeometric()


def abs_xsec_agenda_conts(ws):
    ws.abs_xsec_per_speciesInit()
    ws.abs_xsec_per_speciesAddConts()
    ws.abs_xsec_per_speciesAddLines2()


def surface_rtprop_agenda(ws):
    ws.InterpSurfaceFieldToPosition(out=ws.surface_skin_t,
                                    field=ws.t_surface)
    ws.surfaceBlackbody()


def geo_pos_agenda(ws):
    ws.Ignore(ws.ppath)
    ws.VectorSet(ws.geo_pos, np.array([]))


def arts_inv(y, f, p, sy, sx, atmdir, linefile, custom_sx):
    arts = Workspace(0)

    # Set some agendas
    arts.Copy(arts.surface_rtprop_agenda, arts_agenda(surface_rtprop_agenda))
    arts.Copy(arts.abs_xsec_agenda, arts_agenda(abs_xsec_agenda_conts))
    arts.Copy(arts.ppath_step_agenda, arts_agenda(ppath_step_agenda_geometric))
    arts.Copy(arts.propmat_clearsky_agenda, arts_agenda(propmat_clearsky_agenda_onthefly))
    arts.Copy(arts.iy_main_agenda, arts_agenda(iy_main_agenda_emission))
    arts.Copy(arts.iy_space_agenda, arts_agenda(iy_space_agenda_cosmic_background))
    arts.Copy(arts.ppath_agenda, arts_agenda(ppath_agenda_step_by_step))
    arts.Copy(arts.iy_surface_agenda, arts_agenda(iy_surface_agenda))
    arts.Copy(arts.geo_pos_agenda, arts_agenda(geo_pos_agenda))
    arts.Copy(arts.water_p_eq_agenda, arts_agenda(water_psat_agenda))
    arts.Copy(arts.inversion_iterate_agenda, arts_agenda(inversion_iterate_agenda))
    arts.Copy(arts.sensor_response_agenda, arts_agenda(sensor_response_agenda_waspam))

    # Set some quantities that are unused because you do not need them
    arts.Touch(arts.surface_props_data)
    arts.Touch(arts.surface_props_names)
    arts.Touch(arts.mag_u_field)
    arts.Touch(arts.mag_v_field)
    arts.Touch(arts.mag_w_field)
    arts.Touch(arts.wind_u_field)
    arts.Touch(arts.wind_v_field)
    arts.Touch(arts.wind_w_field)
    arts.Touch(arts.transmitter_pos)
    arts.Touch(arts.iy_aux_vars)
    arts.Touch(arts.mblock_dlos_grid)
    arts.Touch(arts.particle_bulkprop_field)
    arts.Touch(arts.particle_bulkprop_names)
    arts.VectorSetConstant(arts.sensor_time, 1, 0.)

    # Ozone line and continua
    arts.abs_cont_descriptionInit()
    arts.abs_cont_descriptionAppend(tagname="O2-PWR98", model="Rosenkranz")
    arts.abs_cont_descriptionAppend(tagname="H2O-PWR98", model="Rosenkranz")
    arts.abs_cont_descriptionAppend(tagname="N2-CIArotCKDMT252",
                                    model="CKDMT252")
    arts.abs_cont_descriptionAppend(tagname="N2-CIAfunCKDMT252",
                                    model="CKDMT252")
    arts.abs_speciesSet(species=['H2O', 'O2-PWR98',
                                 'N2-CIAfunCKDMT252, N2-CIArotCKDMT252'])

    arts.ReadXML(arts.abs_lines, linefile)
    arts.abs_lines_per_speciesCreateFromLines()

    # Set builtin Earth-viable isotopologue values and partition functions
    arts.isotopologue_ratiosInitFromBuiltin()
    arts.partition_functionsInitFromBuiltin()

    arts.nlteOff()  # LTE
    arts.atmosphere_dim = 1  # 1D atmosphere
    arts.stokes_dim = 1  # No polarization
    arts.rte_alonglos_v = 0.  # No movement of satellite or rotation of planet
    arts.lm_p_lim = 0.  # Just do line mixing if available (it is not)
    arts.abs_f_interp_order = 1  # Interpolation in frequency if you add a sensor
    arts.ppath_lmax = 1000.  # Maximum path length
    arts.ppath_lraytrace = 1000.  # Maximum path trace
    arts.refellipsoidEarth(model="Sphere")  # Europa average radius
    arts.iy_unit = "RJBT"  # Output results in Planck Brightess Temperature

    #  Set the size of the problem (change to your own numbers)
    arts.lon_grid = np.array([])
    arts.lat_grid = np.array([])
    arts.lon_true = np.array([])
    arts.lat_true = np.array([])
    arts.p_grid = p
    arts.z_surface = np.zeros((1, 1))
    arts.t_surface = np.full((1, 1), 295.)
    arts.f_grid = f
    arts.sensorOff()  # No sensor simulations

    # Read the atmosphere... folder should contain:
    # "H2O.xml"
    # "t.xml"
    # "z.xml"
    # The files can be in binary format
    arts.AtmRawRead(basename=atmdir)
    arts.AtmFieldsCalc()

    arts.wind_u_field = arts.z_field.value*0+0.1
    arts.wind_v_field = arts.z_field.value*0+0.1
    arts.wind_w_field = arts.z_field.value*0+0.1

    # Set observation geometry... You can make more positions and los
    arts.sensor_pos = np.array([[10000]])  # [[ALT, LAT, LON]]
    arts.sensor_los = np.array([[70]])  # [[ZENITH, AZIMUTH]]

    sa1 = covmat1d_from_cfun(arts.z_field.value.flatten(),
                             1e-6, Cl=1e3,
                             cfun='exp')
    if custom_sx:
        sa1, _ = sa_matrix_interp(sx,
                                  arts.z_field.value.flatten(), sa1)
    arts.retrievalDefInit()
    arts.covmat_block = copy(sa1)
    arts.retrievalAddAbsSpecies(g1=arts.p_grid, g2=np.array([]),
                                g3=np.array([]), species='H2O', unit="vmr",
                                for_species_tag=0)

    arts.covmat_block = sp.sparse.csc.csc_matrix(100*np.ones((1, 1)))
    arts.retrievalAddWind(g1=np.array([arts.p_grid.value.mean()]),
                          g2=np.array([]), g3=np.array([]),
                          component="strength")

    arts.covmat_block = sp.sparse.csc.csc_matrix(np.ones((1, 1)))
    arts.retrievalAddPolyfit(poly_order=1)

    arts.covmat_block = sp.sparse.csc.csc_matrix(1e-4*np.diag(np.ones((2))))
    arts.retrievalAddSinefit(period_lengths=np.array([5e6, 10e6, 20e6, 40e6]))
    arts.retrievalDefClose()

    arts.cloudboxOff()

    arts.MatrixCreate("covmat")

    if len(sy.shape) == 2:
        arts.covmat_seSet(covmat=sp.sparse.csc.csc_matrix(np.float64(sy)))
    else:
        arts.covmat_seSet(covmat=sp.sparse.csc.csc_matrix(np.diag(sy)))

    arts.atmfields_checkedCalc()
    arts.atmgeom_checkedCalc()
    arts.cloudbox_checkedCalc()
    arts.sensor_checkedCalc()
    arts.propmat_clearsky_agenda_checkedCalc()
    arts.abs_xsec_agenda_checkedCalc()

    arts.xaStandard()
    arts.y = y

    arts.OEM(method="li", max_iter=20, display_progress=0, clear_matrices=0,
             lm_ga_settings=np.array([100.0, 5.0, 2.0, 10.0, 1.0, 1.0]))

    arts.x2artsSensor()

    out = {"f": copy(arts.f_grid.value),
           "xa": copy(arts.xa.value),
           "x": copy(arts.x.value),
           "y": copy(arts.y.value),
           "yf": copy(arts.yf.value),
           "diag": copy(arts.oem_diagnostics.value),
           "y_baseline": copy(arts.y_baseline.value)}

    arts.avkCalc()
    arts.covmat_ssCalc()
    arts.covmat_soCalc()

    out["G"] = copy(arts.dxdy.value)
    out["J"] = copy(arts.jacobian.value),
    out["avk"] = copy(arts.avk.value),
    out["covmat_ss"] = copy(arts.covmat_ss.value),
    out["covmat_so"] = copy(arts.covmat_so.value),

    out['description'] = "First order polynominal with waves at [5e6, 10e6, 20e6, 40e6]"

    del arts
    return out
