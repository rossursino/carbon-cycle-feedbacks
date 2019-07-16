import numpy as np
import xarray as xr
import sys
import pandas as pd


from numpy import pi
r_earth = 6.371e6 # Radius of Earth
dtor = pi/180. # conversion from degrees to radians.


def scalar_earth_area(minlat, maxlat, minlon, maxlon):
    
    "Returns the area of earth in the defined grid box."
    
    diff_lon = np.unwrap((minlon,maxlon), discont=360.+1e-6)
    
    return 2.*pi*r_earth**2 *(np.sin( dtor*maxlat) - np.sin(dtor*minlat))*(diff_lon[1]-diff_lon[0])/360.


def earth_area(minlat, maxlat, minlon, maxlon):
    
    "Returns grid of areas with shape=(minlon, minlat) and earth area."
    
    result = np.zeros((np.array(minlon).size, np.array(minlat).size))
    diffsinlat = 2.*pi*r_earth**2 *(np.sin(dtor*maxlat) - np.sin(dtor*minlat))
    diff_lon = np.unwrap((minlon,maxlon), discont=360.+1e-6)
    
    for i in range(np.array(minlon).size):
        result[i, :] = diffsinlat *(diff_lon[1,i]-diff_lon[0,i])/360.
    
    return result

def earth_area_grid(lats,lons):
    
    "Returns an array of the areas of each grid box within a defined set of lats and lons."
    
    result=np.zeros((lats.size, lons.size))
    
    minlats = lats - 0.5*(lats[1]-lats[0])
    maxlats= lats + 0.5*(lats[1]-lats[0])
    minlons = lons - 0.5*(lons[1]-lons[0])
    maxlons=lons + 0.5*(lons[1]-lons[0])
    
    for i in range(lats.size):
        result[i,:] = scalar_earth_area(minlats[i],maxlats[i],minlons[0],maxlons[0])
    
    return result


def spatial_integration(df, variables, start_time=None, end_time=None):
    
    "Return a dataframe of total sinks for specific regions and the globe and at a specific time point or a range of time points. The regions are split into land and ocean and are latitudinally split as follows: 90 degN to 23 degN, 23 degN to 23 degS and 23 degS to 90 degS. Globally integrated fluxes are also included for each of land and ocean."
    
    # Initialise a dataframe of the regional flux values.
    columns = ['time',
               'earth_land_total', 'south_land_total', 'trop_land_total', 'north_land_total',
               'earth_ocean_total','south_ocean_total', 'trop_ocean_total','north_ocean_total']
    total_values = pd.DataFrame(columns=columns)
    
    
    # Create a list range of time indices.
    if start_time == None:
        start_time = df.time.values[0].strftime('%Y-%m')
    
    if end_time == None:
        end_time = df.time.values[-1]
        try:
            next_month = end_time.replace(month=end_time.month+1)
        except ValueError:
            next_month = end_time.replace(year=end_time.year+1, month=1)
        
        end_time = next_month.strftime('%Y-%m')
            
    arg_time_range = pd.date_range(start=start_time, end=end_time, freq='M').strftime('%Y-%m')
    
    
    # Aggregate fluxes spatially at each time point and insert into dataframe.
    lat = df.latitude
    lon = df.longitude
    earth_grid_area = earth_area_grid(lat,lon)
    
    
    # Create list of month numbers for conversion of yearly averaged monthly fluxes to month units.
    days = {'01': 31, '02': 28, '03': 31, '04': 30,
            '05': 31, '06': 30, '07': 31, '08': 31,
            '09': 30, '10': 31, '11': 30, '12': 31}
    
    for index,time_point in enumerate(arg_time_range):
        
        # Gather number of days in month number of the time point.
        days_in_month = days[time_point[-2:]]
        
        # Obtain a grid of land and ocean fluxes at a time point.
        earth_land_flux = df[variables[0]].sel(time=time_point).values[0]*(days_in_month/365)
        earth_ocean_flux = df[variables[1]].sel(time=time_point).values[0]*(days_in_month/365)

        # Obtain a grid of total sink.
        earth_land_sink = earth_grid_area*earth_land_flux
        earth_ocean_sink = earth_grid_area*earth_ocean_flux

        # Obtain total values of sinks in globe and regions.
        total_values.loc[index,:] = np.array([time_point,
                                          np.sum(1e-15*earth_land_sink),
                                          np.sum(1e-15*earth_land_sink[lat<-23]),
                                          np.sum(1e-15*earth_land_sink[(lat>-23) & (lat<23)]),
                                          np.sum(1e-15*earth_land_sink[lat>23]),
                                          np.sum(1e-15*earth_ocean_sink),
                                          np.sum(1e-15*earth_ocean_sink[lat<-23]),
                                          np.sum(1e-15*earth_ocean_sink[(lat>-23) & (lat<23)]),
                                          np.sum(1e-15*earth_ocean_sink[lat>23])])
        
    
    return total_values.reset_index(drop=True)


def year_integration(df):
    
    "Returns a dataframe with the yearly integrated regional fluxes. df must be a dataframe with previously spatially integrated fluxes and at a monthly scale."
    
    min_year = df.time[0].year
    max_year = df.time[df.time.size-1].year

    df_year = pd.DataFrame(columns= 
                           ['Year',
                            'earth_land_total', 'south_land_total', 'trop_land_total', 'north_land_total',
                            'earth_ocean_total','south_ocean_total', 'trop_ocean_total','north_ocean_total']
                          )

    for (j,year) in enumerate(range(min_year, max_year+1)):
        index = []
        for (i,time) in enumerate(df['time']):
            if time.year == year:
                index.append(i)
        df_year.loc[j,:] = df.iloc[index,1:].sum()

    df_year['Year'] = range(min_year, max_year+1)
    return df_year


def decade_integration(df):
    
    "Returns a dataframe with the decadal integrated regional fluxes. df must be a dataframe with previously spatially integrated fluxes and at a monthly scale."
    
    min_decade = int(df.time[0].year/10)*10
    max_decade = int(df.time[df.time.size-1].year/10)*10
        
    df_decade = pd.DataFrame(columns= 
                           ['Decade',
                            'earth_land_total', 'south_land_total', 'trop_land_total', 'north_land_total',
                            'earth_ocean_total','south_ocean_total', 'trop_ocean_total','north_ocean_total']
                          )

    for (j,decade) in enumerate(range(min_decade, max_decade+10,10)):
        index = []
        for (i,time) in enumerate(df['time']):
            if time.year in range(decade, decade+10):
                index.append(i)
        df_decade.loc[j,:] = df.iloc[index,1:].sum()

    df_decade['Decade'] = range(min_decade, max_decade+10,10)
    return df_decade


def whole_time_integration(df):
    
    "Returns a dataframe with regional fluxes integrated through the entire time period of df. df must be a dataframe with previously spatially integrated fluxes and at a monthly scale."
    
    return df.iloc[:,1:].sum()


def row_output(df, time_index, data_path=None):
    
    "Write a text file of total sinks at a specific time point."
    
    if data_path:
        data_line = "netCDF file path: " + data_path +"\n"
    else:
        data_line = ""
    
    output = open("single_time_output.txt", "w")
    output.write(
        
        data_line +"\n\n"
        "Time: " + str(df.loc[time_index,'time']) + "\n\n"
        "Earth Land Total Sink: " + str(df.loc[time_index,'earth_land_total']) +" GtC\n"
        "South Land Total Sink: " + str(df.loc[time_index,'south_land_total']) +" GtC\n"
        "Tropical Land Total Sink: " + str(df.loc[time_index,'trop_land_total']) +" GtC\n"
        "North Land Total Sink: " + str(df.loc[time_index,'north_land_total']) +" GtC\n\n"
        "Earth Ocean Total Sink: " + str(df.loc[time_index,'earth_ocean_total']) +" GtC\n"
        "South Ocean Total Sink: " + str(df.loc[time_index,'south_ocean_total']) +" GtC\n"
        "Tropical Ocean Total Sink: " + str(df.loc[time_index,'trop_ocean_total']) +" GtC\n"
        "North Ocean Total Sink: " + str(df.loc[time_index,'north_ocean_total']) +" GtC\n"
    )
    output.close()