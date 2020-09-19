""" pytest: AirborneFraction module.
"""


""" IMPORTS """
from core import AirborneFraction

import numpy as np
import xarray as xr
import pandas as pd
from statsmodels import api as sm
import os
from itertools import *

import pytest

co2_month

""" SETUP """
def setup_module(module):
    print('--------------------setup--------------------')
    global co2_year, co2_month, temp_year, temp_month, invf_uptake, invf_uptake_mock

    INV_DIRECTORY = "./../output/inversions/spatial/output_all/"

    co2_year = pd.read_csv(f"./../data/CO2/co2_year.csv").set_index('Year')
    co2_month = pd.read_csv(f"./../data/CO2/co2_month.csv", index_col=["Year", "Month"])

    temp_year = xr.open_dataset('./../output/TEMP/spatial/output_all/HadCRUT/year.nc')
    temp_month = xr.open_dataset('./../output/TEMP/spatial/output_all/HadCRUT/month.nc')

    invf_models = os.listdir(INV_DIRECTORY)

    invf_models = os.listdir(INV_DIRECTORY)
    invf_uptake = {'year': {}, 'month': {}}
    for timeres in invf_uptake:
        for model in invf_models:
            model_dir = INV_DIRECTORY + model + '/'
            invf_uptake[timeres][model] = xr.open_dataset(model_dir + f'{timeres}.nc')

    invf_uptake_mock = {'month': {}}
    for timeres in invf_uptake_mock:
        for model in invf_models:
            model_dir = INV_DIRECTORY + model + '/'
            ds =  xr.open_dataset(model_dir + f'{timeres}.nc')
            start = str(ds.time.values[0])[:4]
            end = str(ds.time.values[-1])[:4]
            C = co2_month.CO2.loc[int(start):int(end)].values
            T = temp.sel(time=slice(start, end)).Earth.values
            invf_uptake_mock[timeres][model] = xr.Dataset(
                {key: (('time'), (C + T) / 2) for key in ['Earth_Land', 'Earth_Ocean']},
                coords={
                        'time': (('time'), ds.time.values)
                       }
            )

""" TESTS """
def test_GCP_airborne():
    df = AirborneFraction.GCP(co2_year, temp_year)
    df.GCP['land sink'] = (df.co2 + df.temp) / 2
    df.GCP['ocean sink'] = (df.co2 + df.temp) / 2

    params = df._feedback_parameters()
    for sink, param in product(['land', 'ocean'], ['CO2', 'temp']):
        assert params[sink][param] == pytest.approx(0.5)

    emission_rate = 2
    b = 1 / np.log(1 + emission_rate / 100)
    beta = 0.5 * 2 / 2.12
    u_gamma = 0.5 * 2 * 0.015 / 2.12 / 1.94
    u = 1 - b * (beta + u_gamma)
    test_af = 1 / u

    return df.airborne_fraction(emission_rate), pytest.approx(test_af)

def test_invf_airborne():
    df = AirborneFraction.INVF(co2_month.CO2, temp_month, invf_uptake_mock['month'])

    land = df._feedback_parameters('Earth_Land')
    ocean = df._feedback_parameters('Earth_Ocean')
    assert land['beta'] == pytest.approx(0.5 / 2.12)
    assert land['gamma'] == pytest.approx(0.5)
    assert ocean['beta'] == pytest.approx(0.5 / 2.12)
    assert ocean['gamma'] == pytest.approx(0.5)

    emission_rate = 2
    b = 1 / np.log(1 + emission_rate / 100)
    beta = 0.5 * 2 / 2.12
    u_gamma = 0.5 * 2 * 0.015 / 2.12 / 1.94
    u = 1 - b * (beta + u_gamma)
    test_af = 1 / u

    return df.airborne_fraction(emission_rate), pytest.approx(test_af)

# CHECK INVF TEST, then tests should work

test_GCP_airborne()
test_invf_airborne()
