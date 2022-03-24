import random
import time
import logging
import shutil
from datetime import datetime, timedelta, date
import glob, sys, os
from pathlib import Path

import numpy as np
import pandas as pd
from pprint import pprint
import pytz
from timeit import default_timer as timer
from datetime import timedelta

import ml_model
from utils import FileUtil, IBUtil
from utils.FileUtil import makeDirectory, unzip_file, get_sec_to_expire, getDateStrFromPath, dateAddInt
from utils.IBUtil import get_expiry_list
import csv
import ml_model.model_logic


######################################################################################################################
def write_summary1(pdTrades, outfile, groupby_arr):
    fields = ["sold", "o_date", "o_time", "o_stock_ask", "o_option_bid", "strike", "expiry", "o_tv", "o_iv",
              "o_theta", "o_dr", "c_date", "c_time", "c_stock_bid", "c_option_ask", "c_tv", "c_iv", "c_theta",
              "c_dr", "net_option", "net_stock", "net", "dur-days"]
    columns = pdTrades.columns


    # reference
    # https://xlsxwriter.readthedocs.io/working_with_pandas.html
    writer = pd.ExcelWriter(outfile, engine='xlsxwriter')
    workbook = writer.book

    for model_no in pdTrades['model_no'].unique():
        summaryPD = pdTrades.loc[pdTrades['model_no'] == model_no]
        summaryStat = summaryPD.groupby(groupby_arr).agg({
            'o_stock_ask': ['count', 'mean', 'min', 'max'],
            'o_theta': ['mean'],
            'o_tv': ['mean'],
            'o_iv': ['mean'],
            'o_dr': ['mean'],
            'c_stock_bid': ['mean', 'min', 'max'],
            'c_theta': ['mean'],
            'c_tv': ['mean'],
            'c_iv': ['mean'],
            'c_dr': ['mean'],
            'net_option': ['mean'],
            'net_stock': ['mean'],
            'dur-days': ['mean'],
            'net_per_day': ['mean'],
            'net': ['mean', 'sum']
            })
        # summaryStat.index.name = status
        sheet = 'model ' + model_no
        summaryStat.to_excel(writer, sheet_name=sheet)
        worksheet = writer.sheets[sheet]
        # Add some cell formats.
        format2 = workbook.add_format({'num_format': '#,##0.00'})
        worksheet.set_column(4, 22, None, format2)
        format0 = workbook.add_format({'num_format': '#'})
        worksheet.set_column(23, 23, None, format0)
        worksheet.conditional_format(0, 21, summaryStat.shape[0] + 2, 21,
                                     {'type': '3_color_scale'})
    writer.save()



def getParams():
    config = FileUtil.readConfig(sys.argv[1])
    pd.set_option('display.max_columns', None)
    l_symbol = config["stock"]
    data_dir = os.getcwd() + "/" + config["ib"]["data_dir"] + "/"
    l_in_dir = os.getcwd() + "/" + "iter_model/data/"
    l_out_dir = os.getcwd() + "/" + "iter_model/assessment/"
    Path(l_out_dir).mkdir(parents=True, exist_ok=True)

    file_list = []
    for rootdir, dirs, files in os.walk(l_in_dir):
        for subdir in dirs:
            full_dir = os.path.join(rootdir, subdir)
            search_mask = full_dir + "/*.csv"
            file_list += glob.glob(search_mask)

    file_list.sort()

    return l_symbol, file_list, l_out_dir


def load_trades(file_list):
    pdTrades = None
    for file in file_list:
        curPd = pd.read_csv(file)
        file_name= file.split("/")[-1]
        model_no = file_name.split("_")[0]
        curPd["net_per_day"] = curPd["net"] / curPd["dur-days"]
        curPd['model_no'] = model_no
        if pdTrades is None:
            pdTrades = curPd
        else:
            pdTrades = pdTrades.append(curPd, ignore_index=True)

    return pdTrades

if __name__ == "__main__":
    symbol, file_list, out_dir = getParams()
    startTime = time.time()
    pdTrades = load_trades(file_list)

    outfile = out_dir + 'summary_status_and_day.xlsx'
    write_summary1(pdTrades, outfile, [ 'sold', 'o_date', 'expiry'])

    outfile = out_dir + 'summary_dr_and_net.xlsx'
    write_summary1(pdTrades, outfile, ['sold', 'o_dr', 'net'])
print(f'TIME Main: {(time.time() - startTime):.2f}')

