import random
import time
import logging
import shutil
from datetime import datetime, timedelta, date
import glob, sys, os

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
def write_stuff():
    # read res file!
    fields = ["sold", "o_date", "o_time", "o_stock_ask", "o_option_bid", "strike", "expiry", "o_tv", "o_iv",
              "o_theta", "o_dr", "c_date", "c_time", "c_stock_bid", "c_option_ask", "c_tv", "c_iv", "c_theta",
              "c_dr", "net_option", "net_stock", "net", "dur-days"]
    res = pd.DataFrame(rows, columns=fields)
    res["net_per_day"] = res["net"] / res["dur-days"]


    # reference
    # https://xlsxwriter.readthedocs.io/working_with_pandas.html
    statuses = ['sold', 'expired', 'not sold1', 'no data']
    summary_outfile = outfile.replace(".csv", '_summary.xlsx')
    row_ct = 1
    writer = pd.ExcelWriter(summary_outfile, engine='xlsxwriter')
    for status in statuses:
        summaryPD = res.loc[res['sold'] == status]
        summaryStat = summaryPD.groupby('net').agg({
            'o_theta': ['count', 'mean'],
            'o_tv': ['mean'],
            'o_iv': ['mean'],
            'o_dr': ['mean'],
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

        if summaryStat.shape[0] > 0:
            ## remove zeros in net, meybe
            summaryStat.index.name = status
            summaryStat.to_excel(writer, sheet_name='SheetA', startrow=row_ct)
            row_ct += summaryStat.shape[0] + 1

    # Get the xlsxwriter workbook and worksheet objects.
    workbook = writer.book
    worksheet = writer.sheets['SheetA']
    format2 = workbook.add_format({'num_format': '#,##0.00'})
    format0 = workbook.add_format({'num_format': '#'})
    worksheet.set_column(2, 13, None, format2)
    worksheet.conditional_format(0, 13, row_ct + 2, 13,
                                 {'type': '3_color_scale'})

    writer.save()


######################################################################################################################
    fields = ["sold", "o_date", "o_time", "o_stock_ask", "o_option_bid", "strike", "expiry", "o_tv", "o_iv",
              "o_theta", "o_dr", "c_date", "c_time", "c_stock_bid", "c_option_ask", "c_tv", "c_iv", "c_theta",
              "c_dr", "net_option", "net_stock", "net", "dur-days"]
    # reference
    # https://xlsxwriter.readthedocs.io/working_with_pandas.html
    summary_outfile = outfile.replace(".csv", '_summary_by_day.xlsx')
    summaryStat = res.groupby([ 'sold', 'o_date', 'expiry']).agg({
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
    writer = pd.ExcelWriter(summary_outfile, engine='xlsxwriter')
    summaryStat.to_excel(writer, sheet_name='SheetA')

    # Get the xlsxwriter workbook and worksheet objects.
    workbook = writer.book
    worksheet = writer.sheets['SheetA']
    # Add some cell formats.
    format2 = workbook.add_format({'num_format': '#,##0.00'})
    format0 = workbook.add_format({'num_format': '#'})
    worksheet.set_column(4, 22, None, format2)
    worksheet.conditional_format(0, 21, summaryStat.shape[0] + 2, 21,
                                 {'type': '3_color_scale'})
    writer.save()

    # summaryStat.to_excel(summary_outfile)


