""" pytest: inv_flux module.
"""


""" IMPORTS """
import os
CURRENT_DIR = ''#os.path.dirname(__file__)

import sys
sys.path.append(CURRENT_DIR + "./../scripts/core")
import TRENDY_flux as TRENDYf

import numpy as np
import xarray as xr

import pytest

""" SETUP """
def setup_module(module):
    print('--------------------setup--------------------')
    global original_ds, test_ds, month_output, year_output
    global basic_test_result, lat, lon, land_vals, ocean_vals

    fname = CURRENT_DIR + "./../data/TRENDY/models/OCN/S1/OCN_S1_nbp.nc"

    ds = xr.open_dataset(fname)

    lat = ds.latitude.values
    lon = ds.longitude.values
    time = ds.time.values

    vals = ds.nbp.values
    vals[np.where(np.isnan(vals))] = 0
    vals[np.where(vals != 0)] = 1 * 30*24*3600

    testData = xr.Dataset(
                {
                'nbp': (('time', 'latitude', 'longitude'),
                                    vals)
                },
                coords = {'longitude': lon, 'latitude': lat, 'time': time}
                )

    original_ds = TRENDYf.SpatialAgg(fname)
    test_ds = TRENDYf.SpatialAgg(testData)
    test_ds.time_resolution = original_ds.time_resolution

    basic_test_result = test_ds.latitudinal_splits()

    # Output dataframe
    output_dir = CURRENT_DIR + './../output/TRENDY/spatial/output_all/OCN_S1_nbp/'
    month_output = xr.open_dataset(output_dir + 'month.nc')
    year_output = xr.open_dataset(output_dir + 'year.nc')


""" TESTS """
def test_check_instance():
    assert isinstance(basic_test_result, xr.Dataset)

def test_regions_add_to_global():

    def differences(dataset):

        components = (dataset.South_Land.values +
                           dataset.Tropical_Land.values +
                           dataset.North_Land.values).sum()

        values = dataset.Earth_Land.values.sum()
        return np.array([abs(components - values)])

    assert np.all(differences(basic_test_result) < 1)
    assert np.all(differences(test_ds.latitudinal_splits(23)) < 1)
    assert np.all(differences(original_ds.latitudinal_splits()) < 1)
    assert np.all(differences(original_ds.latitudinal_splits(23)) < 1)
    assert np.all(differences(month_output) < 1)

def test_spatial_sum():

    def differences(dataset):
        one_month_result = dataset.sel(time = "1780-04")
        # earth_surface_area = test_ds.earth_area_grid(lat,lon).sum()

        total_flux = one_month_result.Earth_Land.values.sum() * 1e-15
        expected_result = test_ds.earth_area_grid(lat,lon).sum() * 2e-15

        return abs(total_flux - expected_result)

    assert differences(basic_test_result) < 1
    assert differences(test_ds.latitudinal_splits(23)) < 1

def test_output_equals_result():

    assert month_output == basic_test_result

def test_months_add_to_years():

    def sums(year, variable):
        month_time = slice(f"{year}-01", f"{year}-12")
        month_sum = (month_output
                        .sel(time=month_time)[variable].values
                        .sum()
                    )
        year_sum = (year_output
                        .sel(time=year)[variable].values
                        .sum()
                   )

        return month_sum, year_sum

    args = [
                ("1990", "Earth_Land"),
                ("1800", "Earth_Land"),
                ("1945", "South_Land"),
                ("2006", "North_Land"),
                ("1976", "Tropical_Land"),

           ]
    for arg in args:
        assert np.subtract(*sums(*arg)) == 0