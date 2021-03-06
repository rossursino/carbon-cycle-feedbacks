""" Test and developments of the GCP Analysis functions.
"""

import os
import pandas as pd
import matplotlib.pyplot as plt

import sys
from core import GCP_flux as GCPf

from importlib import reload
reload(GCPf)

GCPf.list_of_variables()

df = GCPf.Analysis("land sink")

df.plot_timeseries((1968,2178))

df.cascading_window_trend("time", plot=True, include_pearson=True, window_size=15,
                            include_linreg=True)

plt.plot(df.data.index, df.data.values)
plt.plot(df.data.index, df.bandpass(1/10))

df.autocorrelation_plot()
