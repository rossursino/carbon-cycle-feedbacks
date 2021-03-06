""" IMPORTS """
import numpy as np
import pandas as pd
import xarray as xr

import matplotlib.pyplot as plt
import seaborn as sns
sns.set_style('darkgrid')

from statsmodels import api as sm

from copy import deepcopy

import pickle


""" INPUTS """
FIGURE_DIRECTORY = "./../../latex/thesis/figures/"
INPUT_DIRECTORY = './../../data/'
U = pd.read_csv(INPUT_DIRECTORY + 'GCP/budget.csv',
                index_col='Year',
                usecols=[0,4,5]
               )
Ul = U['land sink']
Uo = U['ocean sink']

C = pd.read_csv(INPUT_DIRECTORY + 'CO2/co2_year.csv',index_col='Year').CO2[2:]
T = (xr
        .open_dataset('./../../output/TEMP/spatial/output_all/HadCRUT/year.nc')
        .sel(time=slice("1959", "2018"))
    )
T= T.Earth

phi, rho = 0.015 / 2.12, 1.93


""" FUNCTIONS """
def feedback_regression(uptake, co2, temp):
    df = pd.DataFrame(
        {
            "C": co2,
            "T": temp,
            "U": uptake
        },
        index = co2.index
    )

    X = sm.add_constant(df[["C", "T"]])
    Y = df["U"]

    return sm.OLS(Y, X).fit()

def latex_fb_gcp():
    fb_land = feedback_regression(Ul, C, T)
    fb_ocean = feedback_regression(Uo, C, T)

    latex_df = pd.DataFrame(
        {
            'land': fb_land.params.loc[['C', 'T']].values,
            'ocean': fb_ocean.params.loc[['C', 'T']].values
        },
        index = ['beta', 'gamma']
    ).T

    latex_df["beta"] /= 2.12
    latex_df["u_gamma"] = latex_df["gamma"] * phi / rho

    return latex_df.to_latex(float_format="%.3f")

def feedback_window_regression(uptake, co2, temp):

    times = (
        ('1959', '1968'),
        ('1969', '1978'),
        ('1979', '1988'),
        ('1989', '1998'),
        ('1999', '2008'),
        ('2009', '2018'),
    )

    df = pd.DataFrame(
        {
            "C": co2,
            "T": temp,
            "U": uptake
        },
        index = co2.index
    )

    params = {'beta': [], 'gamma': []}
    for time in times:
        X = sm.add_constant(df[["C", "T"]].loc[time[0]:time[1]])
        Y = df["U"].loc[time[0]:time[1]]
        model = sm.OLS(Y, X).fit()

        params['beta'].append(model.params.loc['C'])
        params['gamma'].append(model.params.loc['T'])

    dataframe = pd.DataFrame(
        params,
        index = [time[0] for time in times]
    )
    dataframe['u_gamma'] = dataframe['gamma'] * phi / rho

    return dataframe


""" FIGURES """
def fb_gcp_decade(save=False):
    df = {
        'land': feedback_window_regression(Ul, C, T),
        'ocean': feedback_window_regression(Uo, C, T)
    }

    fig = plt.figure(figsize=(12,10))
    ax = {}
    axl = fig.add_subplot(111, frame_on=False)
    axl.tick_params(labelcolor="none", bottom=False, left=False)

    bar_width = 4

    fb_gcp_vals = {}

    for subplot, sink in zip(['211', '212'], ['land', 'ocean']):
        ax[subplot] = fig.add_subplot(subplot)

        x = [int(year) for year in df[sink].index]
        x_beta = [int(year) - bar_width / 2 for year in df[sink].index]
        x_ugamma = [int(year) + bar_width / 2 for year in df[sink].index]
        y = df[sink]
        y['beta'] /= 2.12

        fb_gcp_vals[sink] = y[['beta', 'u_gamma']]

        ax[subplot].bar(x_beta, y['beta'], width=bar_width, color='green')
        ax[subplot].bar(x_ugamma, y['u_gamma'], width=bar_width, color='red')
        # ax[subplot].plot(x, y['beta'] + y['u_gamma'], color='black')

        # ax[subplot].legend([r'$\alpha$', r'$\beta$', r'$u_{\gamma}$'],
        #                    fontsize=12)
        ax[subplot].legend([r'$\beta$', r'$u_{\gamma}$'],
                           fontsize=12)

    ax["211"].set_xlabel("Land", fontsize=18, labelpad=10)
    ax["211"].xaxis.set_label_position('top')
    ax["212"].set_xlabel("Ocean", fontsize=18, labelpad=10)
    ax["212"].xaxis.set_label_position('top')

    axl.set_ylabel('Feedback parameter ($yr^{-1}$)', fontsize=18, labelpad=15)

    if save:
        plt.savefig(FIGURE_DIRECTORY + f"fb_gcp_decade.png")

    return fb_gcp_vals

def carbon_gained():
    beta = {
        'land': latex_fb_gcp()['beta']['land'],
        'ocean': latex_fb_gcp()['beta']['ocean']
    }

    gamma = {
        'land': latex_fb_gcp()['gamma']['land'],
        'ocean': latex_fb_gcp()['gamma']['ocean']

    }

    u_gamma = {
        'land': latex_fb_gcp()['u_gamma']['land'],
        'ocean': latex_fb_gcp()['u_gamma']['ocean']

    }

    gained = {}
    for region in beta:
        gained[region] = {}
        gained[region]['beta'] = (beta[region] * (C - C.iloc[0]).values * 2.12).sum()
        gained[region]['gamma'] = (gamma[region] * (T - T[0]).values).sum()
        gained[region]['u_gamma'] = (u_gamma[region] * (C - C.iloc[0]).values * 2.12).sum()

    return pd.DataFrame(gained)

""" EXECUTION """
latex_fb_gcp()[['beta', 'u_gamma']].sum(axis=1)
print(latex_fb_gcp())

land_fwr = feedback_window_regression(Ul, C, T)
ocean_fwr = feedback_window_regression(Uo, C, T)

land_fwr['alpha'] = land_fwr['beta'] / 2.12 + land_fwr['u_gamma']
ocean_fwr['alpha'] = ocean_fwr['beta'] / 2.12 + ocean_fwr['u_gamma']

abs(land_fwr)

abs(land_fwr / ocean_fwr).mean()

fb_gcp_decade(save=True)

carbon_gained()

carbon_gained().sum(axis=1)['beta'] / carbon_gained().sum(axis=1)['gamma']
carbon_gained()['land']['beta'] / carbon_gained()['land']['gamma']

# 1990s analysis
def analysis_1990s(pop=None):
    start, end = 1989, 1998
    nU = Ul.loc[start:end]
    nC = C.loc[start:end]
    nT = pd.Series(T.sel(time=slice(str(start), str(end))).values, index=nC.index)

    if pop:
        for item in pop:
            nU.pop(item)
            nC.pop(item)
            nT.pop(item)

    ds = feedback_regression(nU, nC, nT).params
    data = pd.Series({'beta': ds.C, 'gamma': ds['T']})
    data['u_gamma'] = data['gamma'] * phi / rho
    data['alpha'] = data['beta'] + data['u_gamma']
    return data

analysis_1990s()

analysis_1990s([1991, 1998])

analysis_1990s([1991])

analysis_1990s([1998])


nU = Ul.loc[1989:1998]
nC = C.loc[1989:1998]
nT = pd.Series(T.sel(time=slice(str(1989), str(1998))).values, index=nC.index)

plt.scatter(np.arange(1989,1999), nT)


# 2000s analysis
def analysis_2000s(pop=None):
    start, end = 1999, 2008
    nU = Ul.loc[start:end]
    nC = C.loc[start:end]
    nT = pd.Series(T.sel(time=slice(str(start), str(end))).values, index=nC.index)

    if pop:
        for item in pop:
            nU.pop(item)
            nC.pop(item)
            nT.pop(item)

    ds = feedback_regression(nU, nC, nT).params
    data = pd.Series({'beta': ds.C, 'gamma': ds['T']})
    data['u_gamma'] = data['gamma'] * phi / rho
    data['alpha'] = data['beta'] + data['u_gamma']
    return data

analysis_2000s()


nU = Ul.loc[1999:2008]
nC = C.loc[1999:2008]
nT = pd.Series(T.sel(time=slice(str(1999), str(2008))).values, index=nC.index)

# plt.scatter(np.arange(1999,2009), nU)
plt.scatter(nC, nT)


# Pickle
pickle.dump(fb_gcp_decade(), open(FIGURE_DIRECTORY+'/rayner_df/fb_gcp_decade.pik', 'wb'))
