""" Outputs plots of all the analysis features for each of the six models.

Run this script from the bash shell. """

import sys
sys.path.append("./../core/")

import os
import inv_flux
import pickle
import matplotlib.pyplot as plt


def main():
    input_file = sys.argv[1]
    model_name = sys.argv[2]
    output_dir = sys.argv[3] # For main output: ./../../Output/analysis/ , but can use other directories as a test.
    
    input_dataset = pickle.load(open(input_file, "rb"))

    df = inv_flux.Analysis(input_dataset)
    
    """Parameters."""
    window_size = int(sys.argv[4]) # Usually 25.
    period = sys.argv[5]
    fc = 1/float(period) # Cut-off frequency for bandpass func.
    btype = "low"
    deseasonalise_first = True # Tune to false if deseasonalisation not wanted in bandpass func.

    if input_file.endswith("year.pik"):
        fs = 1
        output_folder = f"{output_dir}year/{model_name}/"
    elif input_file.endswith("spatial.pik"):
        fs = 12
        output_folder = f"{output_dir}monthly/{model_name}/"
        window_size *= 12
    else:
        raise TypeError("Input file must end in either year or spatial.")
    
    
    """ Global plots."""
    variables = ["Earth_Land"]
    
    for variable in variables:
        plt.clf()
        rolling_trend(variable, df, output_folder, window_size)
        plt.clf()
        psd(variable, df, fs, output_folder)
        deseasonalise(variable, df, output_folder)
        bandpass(variable, df, fc, fs, btype, deseasonalise_first, output_folder, period)
    
    """ Regional plots."""
    

def rolling_trend(variable, df, output_folder, window_size):

    roll_df, r_df = df.rolling_trend(variable, window_size, True, True)

    plt.savefig(f"{output_folder}rolling_trend_{str(window_size)}_{variable}.png")

    pickle.dump(roll_df, open(f"{output_folder}rolling_trend_{str(window_size)}_{variable}.pik", "wb"))
    pickle.dump(r_df, open(f"{output_folder}rolling_trend_pearson_{str(window_size)}_{variable}.pik", "wb"))


def psd(variable, df, fs, output_folder):

    psd = df.psd(variable, fs, plot=True)
    plt.savefig(f"{output_folder}psd_{variable}.png")
    pickle.dump(psd, open(f"{output_folder}psd_{variable}.pik", "wb"))


def deseasonalise(variable, df, output_folder):
    deseason = df.deseasonalise(variable)
    pickle.dump(deseason, open(f"{output_folder}deseasonalise_{variable}.pik", "wb"))


def bandpass(variable, df, fc, fs, btype, deseasonalise_first, output_folder, period):
    bandpass = df.bandpass(variable, fc, fs, btype=btype, deseasonalise_first=deseasonalise_first)
    if deseasonalise_first:
        bandpass_fname = f"{output_folder}bandpass_{period}_{btype}_{variable}_deseason.pik"
    else:
        bandpass_fname = f"{output_folder}bandpass_{period}_{btype}_{variable}.pik"
    pickle.dump(bandpass, open(bandpass_fname, "wb"))

    
    
if __name__ == "__main__":
    main()

