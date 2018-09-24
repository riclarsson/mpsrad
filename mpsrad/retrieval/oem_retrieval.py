# The following code has been adapted from https://github.com/simonpf/typhon_examples/

import struct
import numpy as np
import seaborn
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from scipy import signal as sg
from typhon.arts.workspace import Workspace, arts_agenda
import typhon
from scipy.optimize import leastsq
from files import calibration


class oem_retrieval():
    """
    AUTHOR:
      Hayden Smotherman
    DESCRIPTION:
      This class is meant to run an OEM retrieval on data from the radiometers at MPI Solar System.
      The hope is that it simplifies the process of using the typhon OEM retreival for the specific
      use-case of Paul Hartogh's group at MPI Solar System.

      It can load in the data, attempt to fit and subtract-out sine curves from the noise,
      and filter high-frequency oscillations that are present in some data.

      It can also run a retrieval using the typhon OEM retrieval and plot the results,
      along with relevant statistical metrics.
    """
    def __init__(self):
        """
        AUTHOR:
          Hayden Smotherman
        DESCRIPTION:
          This function initializes the oem_retrieval class
        INPUTS:
          NONE
        OUTPUTS:
          NONE
        """

        self.signal = np.array([]) # This array will hold the brightness temperature data
        self.noise  = np.array([]) # This array will hold the noise for the radiometer
        self.freq   = np.array([]) # This array will hold the frequencies of "signal" and "noise"

    def load_data(self,data_type='radiometer',use_data=0,filename='',signal=[],noise=[],freq=[]):
        """
        AUTHOR:
          Hayden Smotherman
        DESCRIPTION:
          This function loads in radiometer data to the oem_retrival class.
          It accepts data in a number of different formats.
        INPUTS:
          data_type - A string denoting which format the input data will be in.
            VALUES:   'numpy'  - Regular numpy arrays passed in to "signal", "noise", and "freq"
                        REQUIRES: signal, noise, freq
                      'radiometer' - A .raw file generated by a radiometer at MPI Solar System.
                        REQUIRES: filename
          use_data - Integer value denoting how much data to use when running a mean OEM retrieval.
                     This value should be zero (use all data) or negative (use the last x signals)
          signal - An array of the brightness temperatures of an O3-666 line.
                   ONLY USED WITH data_type='numpy'
          noise  - An array of the noise of the radiometer
                   ONLY USED WITH data_type='numpy'
          freq   - An array of the central frequency of each datapoint in "signal" and "noise"
                   ONLY USED WITH data_type='numpy'
        OUTPUTS:
        """

        eform = '>i16f7500f100f28f28f'

        dform = '>i16f4092f100f28f28f'

        aform = '>i16f16384f128f28f28f'

        xform = '>i16f1019f128f28f28f'

        if data_type == 'radiometer':
        # Load data from a .raw file from the 210MHz radiometer
            # Load in the raw data
            if filename[0] == 'a':
                data_format = aform
            elif filename[0] == 'd':
                data_format = dform
            elif filename[0] == 'e':
                data_format = eform
            elif filename[0] == 'x':
                data_format = xform
            else:
                raise ImportError('Could not understand the data format based on the file name.')

            Calibrated = calibration(format=data_format)
            Calibrated.load(filename)
            Calibrated.calibrate()

            # Pre-allocate signal and noise arrays
            self.signal = np.array(Calibrated._signal[use_data:])
            self.noise  = np.array(Calibrated._noise[use_data:])

            # Generate the frequency array based on the data format
            if filename[0] == 'a':
                # First we split the data, since two signals are embedded in the ._signal array
                # NOTE: Currently this only keeps the first half of the data. It should keep all of it.
                self.signal = Calibrated._signal[use_data:]
                self.noise  = Calibrated._noise[use_data:]
                Half_Length = int(len(Calibrated._noise[0])/2) # Data is set as one long array
                for i in range(len(self.signal)):
                    self.signal[i] = np.copy(Calibrated._signal[i][0:Half_Length])
                    self.noise[i] = np.copy(Calibrated._noise[i][0:Half_Length])
                self.signal = np.array(self.signal)
                self.noise  = np.array(self.noise)

                # Width of data is 1.5GHz
                # Central frequency is data number 14 in _raw array, requested frequency
                Min_Freq=Calibrated._raw[0][14]-1.50/2
                Max_Freq=Calibrated._raw[0][14]+1.50/2
                self.freq = np.linspace(Min_Freq,Max_Freq,Half_Length)
            elif filename[0] == 'd':
                # Width of data is 40MHz
                # Central frequency is data number 14 in _raw array, requested frequency
                Min_Freq=Calibrated._raw[0][14]-.040/2
                Max_Freq=Calibrated._raw[0][14]+.040/2
                self.freq = np.linspace(Min_Freq,Max_Freq,len(Calibrated._noise[0]))
            elif filename[0] == 'e':
                # Width of data is 210MHz
                # Central frequency is data number 14 in _raw array, requested frequency
                Min_Freq=Calibrated._raw[0][14]-.210/2
                Max_Freq=Calibrated._raw[0][14]+.210/2
                self.freq = np.linspace(Min_Freq,Max_Freq,len(Calibrated._noise[0]))
            elif filename[0] == 'x':
                # Width of data is 4.4GHz
                # Central frequency is data number 14 in _raw array, requested frequency
                Min_Freq=Calibrated._raw[0][14]-4.4/2
                Max_Freq=Calibrated._raw[0][14]+4.4/2
                self.freq = np.linspace(Min_Freq,Max_Freq,len(Calibrated._noise[0]))
            else:
                raise ImportError('Could not generate frequency array. Unknown file format.')

            Calibrated = None
            
        elif data_type == 'numpy':
        # Load in arbitrary data that is already in a numpy array
            self.signal = np.array(signal)
            self.noise  = np.array(noise)
            self.freq   = np.array(freq)

        # Define fit_ values here in case subtract_sinewave is never called
        self.fit_freq   = np.copy(self.freq)
        self.fit_signal = np.copy(self.signal)
        self.fit_noise  = np.copy(self.noise)


    def process_data(self,lims=[138,146],shift_freq=False,fit_sine=False,plot_example=True,initial_guess=[3,1/1000,0]):
        """
        AUTHOR:
          Hayden Smotherman
        DESCRIPTION:
          This function clips data from the front and back of the dataset based on front_lim and
          back_lim. If "fit_sine=True", then it also subtracts out sine waves from the data.
        INPUTS:
          lims - Optional frequency limits (in GHz) that determine the range of data to use.
          shift_freq - Boolean that determines whether or not to shift the frequency such that the
                       max of the averaged data aligns with the peak of the O3 signal.
          fit_sine      - Boolean that determines whether or not to fit a sine wave to the noise then
                          subtract it out of the signal.
          plot_example  - Boolean that determines whether or not to plot an example fit. Only used if
                          fit_sine=True
          initial_guess - This is the initial guess for the sine parameters used by lsqfit. Only used
                          if fit_sine=True
        OUTPUTS:
          NONE
        NOTES:
          - This function works best for data in dform and eform. Datasets with longer frequency
            baselines are not fit as well and may give bad results.
          - By default, "process_data" clips the first 25 data points regardless of what is set in "lims".
            This is done because the first ~20 data points are often severe outliers.
        """

        # Calculate the index corresponding to the minimum frequency limit
        if shift_freq:
            if len(self.signal.shape) > 1:
                Average_Signal = np.mean(self.signal,axis=0)
            else:
                Average_Signal = np.copy(self.signal)

            Freq_Peak = self.freq[Average_Signal==np.max(Average_Signal)]
            Freq_Difference = Freq_Peak-1.42175037e+2
            self.freq -= Freq_Difference

        front_lim = np.where(self.freq == np.min(self.freq[self.freq>lims[0]]))
        front_lim = int(front_lim[0])
        if (front_lim<25):
        # Set front_lim minimum to 25, since the first ~25 data points are very often bad
            front_lim = 25
        # Calculate the index corresponding to the maximum frequency limit
        back_lim  = np.where(self.freq == np.max(self.freq[self.freq<lims[1]]))
        back_lim  = int(back_lim[0])

        Signal_Length = self.signal.shape[1] # Length of the signal array
        Signal_Number = self.signal.shape[0] # Number of signals in the data file

        X_Data = np.linspace(0,Signal_Length-1,Signal_Length) # Array of indicies for the fitting
        X_Data = X_Data[front_lim:back_lim]

        # Preallocate the memory for the fitted values of signal and noise
        self.fit_signal = np.zeros([self.signal.shape[0],np.size(self.signal[0][front_lim:back_lim])])
        self.fit_noise  = np.zeros([self.noise.shape[0],np.size(self.noise[0][front_lim:back_lim])])
        self.fit_freq   = np.copy(self.freq[front_lim:back_lim])

        if fit_sine:
            for i in range(Signal_Number):
            # Iterate over all signals and subtract out the best-fit sine curve

                # Load in noise locally for ease of use
                Noise_0 = self.noise[i]

                # Limit the data based on front_lim and back_lim and subtract the mean
                Noise_0 = Noise_0[front_lim:back_lim]
                Noise_Median = np.median(Noise_0)
                Base_Noise = Noise_0-Noise_Median # Subtract out the noise mean for fitting

                Sine_Params = initial_guess # Amplitude, freq, phase

                # Sine function
                optimize_func = lambda x: x[0]*np.sin(x[1]*X_Data+x[2]) - Base_Noise
                # Perform least square fit to the sine function
                est_amp, est_freq, est_phase = leastsq(optimize_func, Sine_Params)[0]
                # Save the fit
                Fit = est_amp*np.sin(est_freq*X_Data+est_phase)

                # Load in signal locally
                Signal_0 = self.signal[i]
                Signal_0 = Signal_0[front_lim:back_lim]

                # Subtract the fit from the signal and the noise and save it in new variables
                #print(np.size(Signal_0), np.size(Fit))
                self.fit_signal[i] = Signal_0-Fit
                self.fit_noise[i]  = Noise_0-Fit

            if plot_example:
                # Plot the last "noise" value along with the fit sine curve
                plt.figure(figsize=[12,8])
                plt.plot(self.fit_freq,Noise_0)
                plt.plot(self.fit_freq,Fit+Noise_Median)
                plt.legend(['Unfitted Noise','Best Fit Sine Curve'],fontsize=20)
                plt.xlabel('Frequency [GHz]',fontsize=20)
                plt.ylabel('Brightness Temperature [K]',fontsize=20)
                plt.title('Raw Noise and Best Fit Curve',fontsize=24)

                # Plot the fitted noise over the raw noise
                plt.figure(figsize=[12,8])
                plt.plot(self.fit_freq,self.noise[-1][front_lim:back_lim])
                plt.plot(self.fit_freq,self.fit_noise[-1])
                plt.legend(['Unfitted Noise','Fitted Noise'],fontsize=20)
                plt.xlabel('Frequency [GHz]',fontsize=20)
                plt.ylabel('Brightness Temperature [K]',fontsize=20)
                plt.title('Unfitted Noise and Fitted Noise',fontsize=24)

                # Plot the fitted signal over the raw signal
                plt.figure(figsize=[12,8])
                plt.plot(self.fit_freq,self.signal[-1][front_lim:back_lim])
                plt.plot(self.fit_freq,self.fit_signal[-1])
                plt.legend(['Unfitted Signal','Fitted Signal'],fontsize=20)
                plt.xlabel('Frequency [GHz]',fontsize=20)
                plt.ylabel('Brightness Temperature [K]',fontsize=20)
                plt.title('Unfitted Signal and Fitted Signal',fontsize=24)
        else:
            for i in range(Signal_Number):
                self.fit_signal[i] = self.signal[i][front_lim:back_lim]
                self.fit_noise[i]  = self.noise[i][front_lim:back_lim]

    def mean_retrieval(self,filtered=False,plot_results=False,plot_statistics=False):
        """
        AUTHOR:
          Hayden Smotherman
        DESCRIPTION:
          This function uses the Typhon OEM retrieval package to recover atmospheric O3 levels
          given the brightness temperature signal of the O3-666 line. If self.signal is a 2D
          matrix, then this function will run the retrieval on the mean of this data.
        INPUTS:
          filtered - Boolean that determines whether or not to use the scipy.signal.filtfilt
                     function on the mean signal value in order to potentially improve the signal
          plot_results - Boolean that determines whether or not to plot the results of the retrieval.
          plot_statistics - Boolean that determines whether or not to plot relevant statistics
                            from the retrieval.
        OUTPUTS:
          NONE
        """

        if len(self.signal.shape) > 1:
            self.average_signal = np.mean(self.fit_signal,axis=0)
            self.average_noise  = np.mean(self.fit_noise, axis=0)
        else:
            self.average_signal = np.copy(self.fit_signal)
            self.average_noise  = np.copy(self.fit_noise)

        if filtered:
            n = 7  # the larger n is, the smoother the curve will be
            b = [1.0 / n] * n
            a = 1

            self.average_signal = sg.filtfilt(b,a,self.average_signal)
            self.average_noise  = sg.filtfilt(b,a,self.average_noise)

        self._initialize_arts_workspace()

        self.sigma = np.sqrt(np.sum(np.abs(self.average_noise-np.mean(self.average_noise)))/len(self.average_noise))

        self._initialize_covmat()

        self._run_retrieval()

        if plot_results:
        # Plot the retrieved signal and the retrieval values
            # First plot the averaged signal and the retrieved signal
            plt.figure(figsize=[12,8])
            plt.plot(self.fit_freq,self.average_signal)
            plt.plot(self.arts.f_grid.value/1e9,self.arts.yf.value,'r')
            plt.xlabel('Frequency [GHz]',fontsize=20)
            plt.ylabel('Brightness Temperature [K]',fontsize=20)
            plt.legend(['Data', 'Retrieval'],fontsize=20)
            plt.title('Average Signal and Retrieved Signal',fontsize=24)

            # Now plot the actual retrieved Ozone VMR
            Altitude = self.arts.z_field.value.flatten()
            plt.figure(figsize=[8,12])
            plt.plot(10**self.arts.xa.value[:-1],Altitude)
            plt.plot(10**self.arts.x.value[:-1],Altitude)
            plt.legend(['Prior','OEM Retrieval'],fontsize=20)
            plt.ylabel('Altitude [m]',fontsize=20)
            plt.xlabel('O3',fontsize=20)
            plt.title('Altitude vs. O3 VMR',fontsize=24)

        if plot_statistics:
        # Plot some relevant statistics of the OEM retrieval
            Altitude = self.arts.z_field.value.flatten()
            averaging_kernel = (self.arts.dxdy.value @ self.arts.jacobian.value).T
            measurement_response = averaging_kernel @ np.ones(averaging_kernel.shape[1])

            plt.figure(figsize=[12,8])
            [plt.plot(kernel[:-1],Altitude) for kernel in averaging_kernel]
            plt.title('Averaging kernel for the OEM retrieval',fontsize=24)
            plt.ylabel('Altitude [m]',fontsize=20)

            plt.figure(figsize=[12,8])
            plt.plot(measurement_response[:-1],Altitude)
            plt.title('Measurement response for the OEM retrieval',fontsize=24)
            plt.ylabel('Alititude [m]',fontsize=20)

    def _initialize_arts_workspace(self):
        """
        AUTHOR:
          Richard Larsson, Hayden Smotherman
        DESCRIPTION:
          This function is meant to be run interally to this class. It initializes the arts workspace.
        INPUTS:
          NONE
        OUTPUTS:
          NONE
        """

        # -*- coding: utf-8 -*-
        """
        Created on Thu Jul  5 15:53:02 2018

        @author: larsson
        """

        self.arts = Workspace(0)

        @arts_agenda
        def water_psat_agenda(ws):
            ws.water_p_eq_fieldMK05()
        @arts_agenda
        def propmat_clearsky_agenda_zeeman(ws):
            ws.propmat_clearskyInit()
            ws.propmat_clearskyAddOnTheFly()
            ws.Ignore(ws.rtp_mag)
            ws.Ignore(ws.rtp_los)
        @arts_agenda
        def ppath_agenda_step_by_step(ws):
            ws.Ignore(ws.rte_pos2)
            ws.ppathStepByStep()
        @arts_agenda
        def iy_main_agenda_emission(ws):
            ws.Ignore(ws.iy_id)
            ws.ppathCalc()
            ws.iyEmissionStandard()
        @arts_agenda
        def iy_space_agenda_cosmic_background(ws):
            ws.Ignore(ws.rtp_pos)
            ws.Ignore(ws.rtp_los)
            ws.MatrixCBR(ws.iy, ws.stokes_dim, ws.f_grid)
        @arts_agenda
        def iy_surface_agenda(ws):
            ws.SurfaceDummy()
            ws.iySurfaceRtpropAgenda()
        @arts_agenda
        def ppath_step_agenda_geometric(ws):
            ws.Ignore(ws.t_field)
            ws.Ignore(ws.vmr_field)
            ws.Ignore(ws.f_grid)
            ws.Ignore(ws.ppath_lraytrace)
            ws.ppath_stepGeometric()
        @arts_agenda
        def abs_xsec_agenda_lines(ws):
            ws.abs_xsec_per_speciesInit()
            ws.abs_xsec_per_speciesAddLines2()
            ws.abs_xsec_per_speciesAddConts()
        @arts_agenda
        def surface_rtprop_agenda(ws):
            ws.InterpSurfaceFieldToPosition(out=ws.surface_skin_t,
                                            field=ws.t_surface)
            ws.surfaceBlackbody()
        @arts_agenda
        def geo_pos_agenda(ws):
            ws.Ignore(ws.ppath)
            ws.VectorSet(ws.geo_pos, np.array([]))

        # Set some agendas
        self.arts.surface_rtprop_agenda = surface_rtprop_agenda
        self.arts.abs_xsec_agenda = abs_xsec_agenda_lines
        self.arts.ppath_step_agenda = ppath_step_agenda_geometric
        self.arts.propmat_clearsky_agenda = propmat_clearsky_agenda_zeeman
        self.arts.iy_main_agenda = iy_main_agenda_emission
        self.arts.iy_space_agenda = iy_space_agenda_cosmic_background
        self.arts.ppath_agenda = ppath_agenda_step_by_step
        self.arts.iy_surface_agenda = iy_surface_agenda
        self.arts.geo_pos_agenda = geo_pos_agenda
        self.arts.water_p_eq_agenda = water_psat_agenda

        # Set some quantities that are unused because you do not need them (for now)
        self.arts.Touch(self.arts.surface_props_data)
        self.arts.Touch(self.arts.surface_props_names)
        self.arts.Touch(self.arts.mag_u_field)
        self.arts.Touch(self.arts.mag_v_field)
        self.arts.Touch(self.arts.mag_w_field)
        self.arts.Touch(self.arts.wind_u_field)
        self.arts.Touch(self.arts.wind_v_field)
        self.arts.Touch(self.arts.wind_w_field)
        self.arts.Touch(self.arts.transmitter_pos)
        self.arts.Touch(self.arts.iy_aux_vars)
        self.arts.Touch(self.arts.mblock_dlos_grid)
        self.arts.Touch(self.arts.scat_species)

        # Ozone line and continua
        self.arts.abs_cont_descriptionInit()
        self.arts.abs_cont_descriptionAppend(tagname="H2O-PWR98", model="Rosenkranz" )
        self.arts.abs_cont_descriptionAppend(tagname="O2-PWR98", model="Rosenkranz" )
        self.arts.abs_cont_descriptionAppend(tagname="O2-PWR98", model="Rosenkranz" )
        self.arts.abs_cont_descriptionAppend(tagname="N2-CIArotCKDMT252", model="CKDMT252" )
        self.arts.abs_cont_descriptionAppend(tagname="N2-CIAfunCKDMT252", model="CKDMT252" )
        self.arts.abs_speciesSet(species=['O3-666', 'O2-PWR98', 'H2O-PWR98',
                                     'N2-CIAfunCKDMT252, N2-CIArotCKDMT252'])
        self.arts.abs_linesReadFromSplitArtscat(basename='lines/', fmin=142e9, fmax=143e9)
        self.arts.abs_lines_per_speciesCreateFromLines()

        # Set builtin Earth-viable isotopologue values and partition functions
        self.arts.isotopologue_ratiosInitFromBuiltin()
        self.arts.partition_functionsInitFromBuiltin()


        self.arts.nlteOff()  # LTE
        self.arts.atmosphere_dim = 1  # 3D atmosphere
        self.arts.stokes_dim = 1  # No polarization
        self.arts.xsec_speedup_switch = 0  # No speedup (experimental feature)
        self.arts.rte_alonglos_v = 0.  # No movement of satellite or rotation of planet
        self.arts.lm_p_lim = 0.  # Just do line mixing if available (it is not)
        self.arts.abs_f_interp_order = 1  # Interpolation in frequency if you add a sensor
        self.arts.ppath_lmax = 10000.  # Maximum path length (Original)
        self.arts.ppath_lraytrace = 10000.  # Maximum path trace (Original)
        self.arts.refellipsoidEarth(model="Sphere")  # Europa average radius
        self.arts.iy_unit = "PlanckBT"  # Output results in Planck Brightess Temperature

        #  Set the size of the problem (change to your own numbers)
        NP = 51 # Number of pressure levels
        NF = len(self.fit_freq)
        self.arts.lon_grid = np.array([])
        self.arts.lat_grid = np.array([])
        self.arts.p_grid = np.logspace(5.04, -1.2, NP)
        self.arts.z_surface = np.zeros((1, 1))
        self.arts.t_surface = np.full((1, 1), 295.)
        self.arts.f_grid = np.linspace(np.min(self.fit_freq)*1e9,np.max(self.fit_freq)*1e9, NF)
        self.arts.sensorOff()  # No sensor simulations

        # Read the atmosphere... folder should contain:
        # "H2O.xml"
        # "t.xml"
        # "z.xml"
        # The files can be in binary format
        self.arts.AtmRawRead(basename='atm/')
        self.arts.AtmFieldsCalc()

        # Set observation geometry... You can make more positions and los
        self.arts.sensor_pos = np.array([[300]])  # [[ALT, LAT, LON]] (Original)

        self.arts.sensor_los = np.array([[45]])  # [[ZENITH, AZIMUTH]]

        # Temperature and Ozone VMR Jacobian
        self.arts.jacobianInit()
        self.arts.jacobianAddTemperature(g1=self.arts.p_grid.value, g2=np.array([]), g3=np.array([]))
        self.arts.jacobianAddAbsSpecies(g1=self.arts.p_grid.value, g2=np.array([]), g3=np.array([]), species='O3-666')
        self.arts.jacobianClose()
        self.arts.cloudboxOff()  # No Clouds

        # Check that the input looks OK
        self.arts.atmgeom_checkedCalc()
        self.arts.atmfields_checkedCalc()
        self.arts.cloudbox_checkedCalc()
        self.arts.sensor_checkedCalc()
        self.arts.propmat_clearsky_agenda_checkedCalc()
        self.arts.abs_xsec_agenda_checkedCalc()

        # Perform the calculations!
        self.arts.yCalc()

    def _initialize_covmat(self):
        """
        AUTHOR:
          Simon Pfreundschuh, Hayden Smotherman
        DESCRIPTION:
          This function is meant to be run interally to this class. It initializes the covariance matricies.
        INPUTS:
          NONE
        OUTPUTS:
          NONE
        """
        z_grid = self.arts.z_field.value.flatten()

        n_p = self.arts.p_grid.value.size

        self.arts.retrievalDefInit()
        # Kernel panic if 'grid_1' and 'sigma_1' are not the same size
        self.arts.covmat1D(self.arts.covmat_block,
                    grid_1 = z_grid,
                    sigma_1 = 0.1 * np.ones(n_p), # Relative uncertainty
                    cls_1   = 0.5e3 * np.ones(n_p), # Correlation length [m]
                    fname   = "exp")
        self.arts.retrievalAddAbsSpecies(species = "O3-666",
                                  unit    = "vmr",
                                  atmosphere_dim = 1,
                                  g1      = self.arts.p_grid,
                                  g2      = np.array([]),
                                  g3      = np.array([]))
        self.arts.jacobianSetFuncTransformation(transformation_func = "log10")

        self.arts.covmatDiagonal(out = self.arts.covmat_block,
                            out_inverse = self.arts.covmat_inv_block,
                            vars = 100.0  * np.ones(1))
        self.arts.retrievalAddPolyfit(poly_order = 0)
        self.arts.retrievalDefClose()

        # More uncertainty measurements
        self.arts.covmatDiagonal(self.arts.covmat_block, self.arts.covmat_inv_block,
                                 vars = self.sigma**2 * np.ones(self.arts.y.value.shape))
        self.arts.covmat_seSet(self.arts.covmat_block)
        self.arts.jacobianAdjustAndTransform

        # Kernel panic if 'arts.Ignore(arts.inversion_iteration_counter)' is not included

        @arts_agenda
        def inversion_iterate_agenda(arts):
            arts.Ignore(arts.inversion_iteration_counter)
            arts.x2artsStandard()
            arts.atmfields_checkedCalc(negative_vmr_ok=1) # negative_vmr_ok added to avoid error with negative vmr values
            arts.atmgeom_checkedCalc()
            arts.yCalc()
            arts.jacobianAdjustAndTransform()
            arts.VectorAddVector( arts.yf, arts.y, arts.y_baseline )

        self.arts.Copy(self.arts.inversion_iterate_agenda, inversion_iterate_agenda)

    def _run_retrieval(self):
        """
        AUTHOR:
          Simon Pfreundschuh, Hayden Smotherman
        DESCRIPTION:
          This function is meant to be run interally to this class. It runs the actual retrieval.
        INPUTS:
          NONE
        OUTPUTS:
          NONE
        """

        # Run the OEM retrieval

        self.arts.Touch(self.arts.particle_bulkprop_field)
        self.arts.Touch(self.arts.particle_bulkprop_names)
        self.arts.VectorSetConstant(self.arts.sensor_time,1,0.)
        self.arts.xaStandard()
        self.arts.x        = np.zeros(0)
        self.arts.y.value[:] = self.average_signal
        self.arts.jacobian = np.zeros((0,0))

        self.arts.OEM(method="lm", max_iter=20, display_progress=0,
               lm_ga_settings=np.array([100.0, 5.0, 2.0, 10.0, 1.0, 1.0]))
