import numpy as np
import xarray as xr
import sys
import os
import pandas as pd
import pickle
import matplotlib.pyplot as plt
from datetime import datetime
from scipy import stats, signal


def list_of_variables():
    """ Returns a list of all available variables in the GCP dataframe.
    """

    GCPfname = os.path.join(os.path.dirname(__file__),
                            './../../data/GCP/budget.csv')

    return pd.read_csv(GCPfname, index_col=0).columns


class Analysis:
    """ This class takes the budget.csv in the GCP data folder and provides
    analysis and visualisations on selected data as required, including
    plotting timeseries, linear regression over whole an decadal periods and
    frequency analyses.

    Parameters
    ----------
    variable: the name of a selected column from budget.csv.

    """

    def __init__(self, variable):
        """ Read budget.csv and convert the columns into single arrays assigned
        to a variable.

        Parameters
        ----------

        variable: str

            variable to choose from columns in budget.csv.

        """

        GCPfname = os.path.join(os.path.dirname(__file__),
                                './../../data/GCP/budget.csv')
        GCP = pd.read_csv(GCPfname, index_col=0)

        self.variable = variable

        self.all_data = GCP
        self.data = GCP[variable]

    def _time_to_CO2(self, time):
        """ Converts any time series array to corresponding atmospheric CO2
        values.
        This function should only be used within the 'cascading_window_trend'
        method.

        Parameters
        ==========

        time:

            time series to convert.

        """

        CO2fname = os.path.join(os.path.dirname(__file__),
                                "./../../data/CO2/co2_year.csv")
        CO2 = pd.read_csv(CO2fname, index_col="Year")['CO2']

        time = list(self.data.index)
        try:
            return CO2.loc[time[0]:time[-1]].values
        except AttributeError:
            return CO2.loc[time[0]:time[-1]]

    def cascading_window_trend(self, indep="time", window_size=10, plot=False,
                               include_pearson=False):
        """ Calculates the slope of the trend of an uptake variable for each
        time window and for a given window size. The function also plots the
        slopes as a timeseries and, if prompted, the r-value of each slope as
        a timeseries.

        Parameters
        ----------

        indep: string, optional

            Regress uptake variable over "time" or "CO2".
            Defaults to "time".

        window_size: int, optional

            size of time window of trends. Defaults to 10.

        plot: bool, optional

            Option to show plots of the slopes.
            include_pearson: Defaults to False. Option to include dataframe and
            plot of r-values for each year.
            Defaults to False.

        """

        df = self.data

        x_time = df.index
        if indep == "time":
            x_var = x_time
            ts_xlabel = "Year"
            cascading_yunit = "(GtC/ppm/yr)"
            cascading_xlabel = f"First year of {window_size}-year window"
        else:
            x_var = self._time_to_CO2(x_time)
            ts_xlabel = "CO2 (ppm)"
            cascading_yunit = "(GtC/ppm$^2$)"
            cascading_xlabel = f"Start of {window_size}-year CO2 window (ppm)"

        roll_vals, r_vals = [], []
        for i in range(0, len(df.index) - window_size):
            sub_df = df[i:i+window_size+1]

            sub_x = x_var[i:i+window_size+1]
            sub_vals = df[i:i+window_size+1].values

            linreg = stats.linregress(sub_x, sub_vals)

            roll_vals.append(linreg[0])
            r_vals.append(linreg[2])

        roll_df = pd.DataFrame(
                            {f"{window_size}-year trend slope": roll_vals},
                            index = x_var[:-window_size]
                            )


        if plot:
            plt.figure(figsize=(22,16))
            plt.subplot(211)
            plt.plot(x_var, df.values)
            plt.xlabel(ts_xlabel, fontsize=20)
            plt.ylabel("C flux to the atmosphere (GtC)", fontsize=20)

            plt.subplot(212)
            plt.plot(roll_df, color='g')
            plt.xlabel(cascading_xlabel, fontsize=20)
            plt.ylabel(f"Slope of C flux trend {cascading_yunit}", fontsize=20)

        if include_pearson:
            r_df = pd.DataFrame(
                                {"r-values of trends": r_vals},
                                index = x_var[:-window_size]
                                )
            return roll_df, r_df
        else:
            return roll_df



    def psd(self, xlim=None, plot=False):
        """ Calculates the power spectral density (psd) of a timeseries of a
        variable using the Welch method. Also provides the timeseries plot and
        psd plot if passed. This function is designed for the monthly
        timeseries, but otherwise plotting the dataframe is possible.

        Parameters
        ----------

        xlim: list-like, optional

            apply limit to x-axis of the psd. Must be a list of two values.

        plot: bool, optional

            If assigned to True, shows two plots of timeseries and psd.
            Defaults to False.

        """

        df = self.data

        period = " (years)"
        unit = "((GtC/yr)$^2$.yr)"

        # All GCP timeseries are annual, therefore fs is set to 1.
        freqs, spec = signal.welch(df.values, fs=1)

        if plot:
            plt.figure(figsize=(12,9))

            plt.subplot(211)
            plt.plot(df.index, df.values)

            plt.subplot(212)
            plt.semilogy(1/freqs, spec)
            plt.gca().invert_xaxis()
            plt.xlim(xlim)

            plt.title(f"Power Spectrum of {self.variable}")
            plt.xlabel(f"Period{period}")
            plt.ylabel(f"Spectral Variance {unit}")

        return pd.DataFrame(
                                {
                                    f"Period{period}": 1/freqs,
                                    f"Spectral Variance {unit}": spec
                                },
                                index=freqs
                           )



    def bandpass(self, fc, order=5, btype="low"):
        """ Applies a bandpass filter to a dataset (either lowpass, highpass or
        bandpass) using the scipy.signal.butter function.

        Parameters
        ----------

        fc: float

            cut-off frequency or frequencies.

        order: int, optional

            order of the filter. Defaults to 5.

        btype: string, optional

            options are low, high and band.

        """

        x = self.data.values

        if btype == "band":
            assert type(fc) == list, "fc must be a list of two values."
            fc = np.array(fc)

        fs = 1 # All GCP timeseries are annual, hence fs is set to 1.
        w = fc / (fs / 2) # Normalize the frequency.
        b, a = signal.butter(order, w, btype)

        return signal.filtfilt(b, a, x)


    def autocorrelation_plot(self):
        """ Plots autocorrelation of model uptake timeseries using
        pandas.plotting.

        """

        ax = pd.plotting.autocorrelation_plot(self.data.values)
        ax.set_xlabel("Lag (in years)")

        return ax
