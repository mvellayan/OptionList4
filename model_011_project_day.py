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

logging.basicConfig(level=logging.ERROR)
log = logging.getLogger("myLogger")
log.setLevel(logging.INFO)

pdOptionList: pd.DataFrame = None     # Data Frame all options Contracts for the symbol
pdOptionList3_wData: pd.DataFrame = None     # options with data
pdStockQuotes: pd.DataFrame = None    # Data Frame all date/time quotes for the symbol
pdOptionQuotesIdx = {}

def expandX(quoteTime, quoteLast):
    global pdStockQuotes, pdOptionList, pdOptionList3_wData, pdOptionQuotesIdx

    quoteTimeObj = FileUtil.getDateObjFromStr(quoteTime)
    # pprint (list)

    retDict = {}
    retDict["time"] = quoteTime

    # retDict["p0"] = FileUtil.get_value_with_delta(pdStockQuotes, quoteTimeObj, 0)
    sorted_ol = pdOptionList3_wData.sort_values(by=['expiry', 'strike'], ascending=True)
    for index, contract in sorted_ol.iterrows():
        # print(row['c1'], row['c2'])

        if contract.expiry != 20220114:
            continue

        for ctr in range(2):
            idx = pdOptionQuotesIdx.get(str(contract.con_id) + ":" + str(quoteTime+ctr))
            if idx is not None:
                break
        if idx is not None:
            tv = None
            tv = ((idx["ask"] + idx["bid"])/2) - (quoteLast - contract.strike)
            dur = get_sec_to_expire(
                FileUtil.getDateObjFromStr(quoteTime),
                FileUtil.getDateObjFromStr(contract.expiry, 'YYYYMMDD'))
            if dur == 0 or tv == 0:
                theta = 0
            else:
                theta = (tv / dur) * 100 * 1000 # 100 = cents, 100 = basis point

            col_prefix = str(f"C_{(contract.expiry % 1000):04d}_{contract.strike}")

        #    retDict[col_prefix + "_" + "symbol"] = idx["symbol"]
            # retDict[col_prefix + "_" + "bid_ask_delta"] = idx["bid"] - idx["ask"]
        #    retDict[col_prefix + "_" + "ask"] = idx["ask"]
        #    retDict[col_prefix + "_" + "ask_size"] = idx["ask_size"]
        #    retDict[col_prefix + "_" + "bid"] = idx["bid"]
        #    retDict[col_prefix + "_" + "bid_size"] = idx["bid_size"]
            retDict[col_prefix + "_" + "last"] = idx["last"]
        #    retDict[col_prefix + "_" + "last_size"] = idx["last_size"]
        #    retDict[col_prefix + "_" + "strike"] = contract.strike
            retDict[col_prefix + "_" + "strike_delta"] = quoteLast - contract.strike
            retDict[col_prefix + "_" + "time_value"] = tv
            retDict[col_prefix + "_" + "theta"] = theta
        #    retDict[col_prefix + "_" + "implied_volatility"] = idx["implied_volatility"]

            # retDict[label] = FileUtil.get_value_with_delta(pdStockQuotes, quoteTimeObj, value)
    return retDict

def loadBasicData(in_zip_file, symbol):
    global pdStockQuotes, pdOptionList, pdOptionList3_wData, pdOptionQuotesIdx

    createdTmpDir = False
    # 1 Unzip the zip file in a temp dir:
    if os.path.exists(in_zip_file):
        createdTmpDir = True
        startingDir = in_zip_file[ : in_zip_file.rfind("/")] + "/" + FileUtil.getDateTimeStamp(1)
        os.makedirs(startingDir, exist_ok=True)
        unzip_file(directory_name=startingDir, zip_file_name=in_zip_file)

    # 2. Load pdStockQuotes -- Stock Quotes
    for file in glob.glob(startingDir + "/sq_" + symbol + "_" + "*csv"):
        curPd = pd.read_csv(file)
        # Store only 9:25 to 16:10 data for quotes
        curPd = curPd[(curPd['time'] % 1000000).between(93000, 160000)]
        if pdStockQuotes is None:
            pdStockQuotes = curPd
        else:
            pdStockQuotes = pdStockQuotes.append(curPd, ignore_index=True)

    # pdStockQuotes["bid_ask_delta"] = pdStockQuotes["bid"] - pdStockQuotes["ask"]

    # No files in the directory
    if pdStockQuotes is None:
        log.error("No files in the directory?? " + startingDir + "/sq_" + symbol + "_" + "*csv")
        return False
    else:
        log.info(f"Found [{pdStockQuotes.shape}] stocks rows.")

    # 4. Load pdOptionList -- options List
    for file in glob.glob(startingDir + "/ol_" + symbol + "*csv"):
        ol = pd.read_csv(file)
        if pdOptionList is None:
            pdOptionList = ol
        else:
            pdOptionList = pdOptionList.append(ol, ignore_index=True)
    pdOptionList.drop_duplicates(inplace=True, subset=['con_id'])

    # 4.b load pdOptionList3wC
    # filtering now for performance improvement.
    # pdOptionList3_wData = pdOptionList # Need to filter out options without data

    # 5. Load pdOptionQuotesIdx -- Options Quotes
    min_rows = 18000
    for file in glob.glob(startingDir + "/oq_" + symbol + "*csv"):

        curPd = pd.read_csv(file)
        if curPd.shape[0] < min_rows:
            print(f"Dropping file [{file}] with shape {curPd.shape} because there is less than {min_rows}.  ")
            continue
        else:
            print(f"Adding file [{file}] with shape {curPd.shape}")

        curPd_cont_id = curPd.loc[0, "con_id"]
        p = pdOptionList.loc[pdOptionList['con_id'] == curPd_cont_id]
        if pdOptionList3_wData is None:
            pdOptionList3_wData = p
        else:
            pdOptionList3_wData = pdOptionList3_wData.append(p, ignore_index=True)
        # Store only 9:25 to 16:10 data for quotes
        curPd = curPd[(curPd['time'] % 1000000).between(93000, 160000)]
        for index, row in curPd.iterrows():
            hash_idx = str(row.con_id) + ":" + str(row.time)
            # print (index, '->', row, '==>', hash_idx)
            pdOptionQuotesIdx[hash_idx] = row

    # No files in the directory
    if len(pdOptionQuotesIdx) is 0:
        log.error("No complete option quote files in the directory?? " + startingDir + "/oq_" + symbol + "_" + "*csv")
        return False
    else:
        log.info(f"Found [{pdOptionList.shape}] stocks rows.")


    # 6. Cleanup
    if createdTmpDir:
        try:
            shutil.rmtree(startingDir)
        except OSError as e:
            print("Error: %s : %s" % (startingDir, e.strerror))
    else:
        raise Exception("Unexpected createdTempDir == False.  Hmm")

    # 7. Done!!
    return True

def bucket_it2(column_value: float, dividing_value: float):
    if pd.isna(column_value): return np.NaN
    if column_value <= dividing_value:
        return 0  + ( np.sign(dividing_value) * 2)
    else:
        return 1 + ( np.sign(dividing_value) * 2)

def main(in_zip_file, out_dir, symbol: str):
    global pdStockQuotes, pdOptionList, pdOptionQuotesIdx, projection, df, pdOptionList3_wData

    outfile = out_dir + "ml_day_" + symbol + getDateStrFromPath(in_zip_file) + ".csv"
    print(f"Processing {in_zip_file} => {outfile}")
    if os.path.exists(outfile):
        print(f"\tAssessment File Exist, skipping directory: {outfile}")
        return

    pdOptionList = None  # Data Frame all options Contracts for the symbol
    pdOptionList3_wData = None  # 3 week calls only
    pdStockQuotes = None  # Data Frame all date/time quotes for the symbol
    projection = None
    df = None
    pdOptionQuotesIdx = {}
    FileUtil.reset_quote_cache()

    if not loadBasicData(in_zip_file, symbol):
        log.error("Cant find data in this dir: " + in_zip_file)
        return


    df = pdStockQuotes.apply(lambda x: expandX(x['time'], x['last']), axis=1, result_type='expand')
    projection = pdStockQuotes.merge(df, on="time", how="outer")
    # for col in projection.columns: print(f"{ctr}: {col}")

    #delta_labels = ["p5s", "p15s", "p30s", "p60s", "p300s", "p600s", "n5s", "n15s", "n30s", "n60s", "n300s", "n600s"]
    #delta_values = [5, 15, 30, 60, 300, 600, -5, -15, -30, -60, -300, -600]
    #delta_quarts = [3, 3, 5, 5, 7, 7, 3, 3, 5, 5, 7, 7]
    #bucket_labels = [ bucket_p5s, bucket_p15s....]

    projection.to_csv(outfile, float_format='%.6f', index=False)


if __name__ == "__main__":

    config = {}  # parameter config object

    pd.set_option('display.max_columns', None)
    config = FileUtil.readConfig(sys.argv[1])
    symbol_m = config["stock"]

    data_dir_m = os.getcwd() + "/" + config["ib"]["data_dir"] + "/"
    out_dir_m = os.getcwd() + "/" + config["ml_day"]["data_dir"] + "/data/"

    print("Main scanning: " + data_dir_m)

    file_list = []
    for rootdir, dirs, files in os.walk(data_dir_m):
        for subdir in dirs:
            full_dir = os.path.join(rootdir, subdir)
            search_mask = full_dir + "/" + symbol_m + '*.zip'
            file_list += glob.glob(search_mask)
            #if glob.glob(search_mask1) or glob.glob(search_mask2):
            #    main(full_dir, symbol)


    file_list.sort()
    for zip_file in file_list:
        main(zip_file, out_dir_m, symbol_m)
