import plotly.graph_objects as go
import pandas as pd
import numpy as np
import argparse
import logging
import math
import shutil
from datetime import datetime, timedelta, date
import glob, sys, os

import numpy as np
import pandas as pd
from pprint import pprint
import pytz
from timeit import default_timer as timer
from datetime import timedelta

from utils import FileUtil, IBUtil
from utils.FileUtil import makeDirectory, unzip_file, get_sec_to_expire, getDateStrFromPath


def main(symbol: str, in_file: str):

    # Read data from a csv
    data = pd.read_csv(in_file)
    x_cols = [ c1 for c1 in data.columns.values if '0121' in c1 and 'time_value' in c1 ]
    data["time2"] = data["time"] % 1000000
    y_cols = data["time2"].values
    z_vals = data[x_cols].values


    fig = go.Figure(go.Surface(
        contours={
            "x": {"show": True, "start": 1.5, "end": 2, "size": 0.04, "color": "white"},
            "z": {"show": True, "start": 0.5, "end": 0.8, "size": 0.05}
        },
        x = x_cols,
        y = y_cols,
        z = z_vals
        ))
    fig.update_layout(
        scene={
            "xaxis": {"nticks": 20},
            "zaxis": {"nticks": 4},
            'camera_eye': {"x": 0, "y": -1, "z": 0.5},
            "aspectratio": {"x": 1, "y": 1, "z": 0.2}
        })
    fig.show()
    # z = z_data.values
    # sh_0, sh_1 = z.shape
    # x, y = np.linspace(0, 1, sh_0), np.linspace(0, 1, sh_1)
    # fig = go.Figure(data=[go.Surface(z=z, x=x, y=y)])
    # fig.update_layout(title='Mt Bruno Elevation', autosize=False,
    #                   width=500, height=500,
    #                   margin=dict(l=65, r=50, b=65, t=90))
    # fig.show()
    #


if __name__ == "__main__":

    config = {}  # parameter config object

    pd.set_option('display.max_columns', None)
    config = FileUtil.readConfig(sys.argv[1])
    symbol_m = config["stock"]

    file_list = os.getcwd() + "/" + config["ml_day"]["data_dir"] + "/data/*106.csv"
    for file in glob.glob(file_list):
        print(f"Main scanning: {file}")
        main(symbol_m, file)
        break  #  do only once for now


