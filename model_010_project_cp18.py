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

delta_labels = ["p5s", "p15s", "p30s", "p60s", "p300s", "p600s", "n5s", "n15s", "n30s", "n60s", "n300s", "n600s"]
delta_values = [5, 15, 30, 60, 300, 600, -5, -15, -30, -60, -300, -600]
delta_quarts = [3, 3, 5, 5, 7, 7, 3, 3, 5, 5, 7, 7]
bucket_labels = []
for s in delta_labels:
    bucket_labels.append(s + "_bucket")

pdOptionList: pd.DataFrame = None     # Data Frame all options Contracts for the symbol
pdOptionList3wC: pd.DataFrame = None     # 3 week calls only
pdStockQuotes: pd.DataFrame = None    # Data Frame all date/time quotes for the symbol
pdOptionQuotesIdx = {}
expiryList = []                 # list of expiry we are interested in for the given date
running_missing = 0
running_total = 0
total_lookup = 0

def expandX(quoteTime, conId, quoteLast):
    global pdStockQuotes, pdOptionList, pdOptionList3wC, pdOptionQuotesIdx
    global running_total, running_missing, total_lookup, expiryList
    contractList = IBUtil.filter_option_list(expiryList, quoteLast, pdOptionList3wC, strikeBox=3)
    # pprint (list)
    listLabel = ["c_w1_n3", "c_w1_n2", "c_w1_n1", "c_w1_p1", "c_w1_p2", "c_w1_p3",
                 "c_w2_n3", "c_w2_n2", "c_w2_n1", "c_w2_p1", "c_w2_p2", "c_w2_p3",
                 "c_w3_n3", "c_w3_n2", "c_w3_n1", "c_w3_p1", "c_w3_p2", "c_w3_p3"]
    retDict = {}
    index = 0
    retDict["time"] = quoteTime
    quoteDateObj = FileUtil.getDateObjFromStr(quoteTime)

    retDict["p0"] = FileUtil.get_quote_with_delta(pdStockQuotes, quoteDateObj, 0)

    for ctr_delta_labels in range(len(delta_labels)):
        label = delta_labels[ctr_delta_labels]
        value = delta_values[ctr_delta_labels]
        retDict[label] = FileUtil.get_quote_with_delta(pdStockQuotes, quoteDateObj, value)
        if retDict[label]:
            retDict[label + "_delta"] = (retDict[label] - retDict["p0"])

    for contract in contractList:
        running_total += 1

        for ctr in range(2):
            idx = pdOptionQuotesIdx.get(str(contract.conId) + ":" + str(quoteTime+ctr))
            if idx is not None:
                break
        if idx is None:
            running_missing += 1
            if running_missing % 5000 == 0:
                print("\t", "missing=[", running_missing, round(running_missing/total_lookup, 4), "% ] total=[",
                      running_total, "/", total_lookup, round(running_total/total_lookup, 4), '% ]:',
                      str(conId) + ":" + str(quoteTime), "Missing")
        else:
            res = idx
            tv = None
            tv = ((res["ask"] + res["bid"])/2) - (quoteLast - contract.strike)
            dur = get_sec_to_expire(
                FileUtil.getDateObjFromStr(quoteTime),
                FileUtil.getDateObjFromStr(contract.lastTradeDateOrContractMonth, 'YYYYMMDD'))
            if dur == 0 or tv == 0:
                theta = 0
            else:
                theta = (tv / dur) * 100 * 1000 # 100 = cents, 100 = basis point
            retDict[listLabel[index] + "_" + "symbol"] = res["symbol"]
            retDict[listLabel[index] + "_" + "bid_ask_delta"] = res["bid"] - res["ask"]
            retDict[listLabel[index] + "_" + "ask"] = res["ask"]
            retDict[listLabel[index] + "_" + "ask_size"] = res["ask_size"]
            retDict[listLabel[index] + "_" + "bid"] = res["bid"]
            retDict[listLabel[index] + "_" + "bid_size"] = res["bid_size"]
            retDict[listLabel[index] + "_" + "last"] = res["last"]
            retDict[listLabel[index] + "_" + "last_size"] = res["last_size"]
            retDict[listLabel[index] + "_" + "strike"] = contract.strike
            if index == 0:
                retDict[listLabel[index] + "_" + "strike_delta"] = quoteLast - contract.strike
            retDict[listLabel[index] + "_" + "time_value"] = tv
            retDict[listLabel[index] + "_" + "theta"] = theta
            retDict[listLabel[index] + "_" + "implied_volatility"] = res["implied_volatility"]
        index += 1

    return retDict

def loadBasicData(in_zip_file, symbol):
    global pdStockQuotes, pdOptionList, pdOptionList3wC, pdOptionQuotesIdx, expiryList

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

    pdStockQuotes["bid_ask_delta"] = pdStockQuotes["bid"] - pdStockQuotes["ask"]

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


    # 3. Load variable : expiryList
    expiryList = IBUtil.get_expiry_list(pdStockQuotes[['time']].values[0][0], 3, pdOptionList)


    # 4.b load pdOptionList3wC
    # filtering now for performance improvement.
    pdOptionList3wC = pdOptionList[pdOptionList['right'] == 'C']
    pdOptionList3wC = pdOptionList3wC[pdOptionList3wC['expiry'] <= expiryList[-1]]

    # 5. Load pdOptionQuotesIdx -- Options Quotes
    for file in glob.glob(startingDir + "/oq_" + symbol + "*csv"):
        curPd = pd.read_csv(file)
        # Store only 9:25 to 16:10 data for quotes
        curPd = curPd[(curPd['time'] % 1000000).between(93000, 160000)]
        for index, row in curPd.iterrows():
            hash_idx = str(row.con_id) + ":" + str(row.time)
            # print (index, '->', row, '==>', hash_idx)
            pdOptionQuotesIdx[hash_idx] = row


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

def bucket_it2(col_val, q_array):
    if pd.isna(col_val): return np.NaN
    for i in range(len(q_array)):
        if col_val <= q_array[i]: return str(i) # + "_p"
    return str(len(q_array)) # + "_p"

def main(in_zip_file, out_dir, symbol: str):
    global pdStockQuotes, pdOptionList, pdOptionQuotesIdx, expiryList, projection, df, pdOptionList3wC
    global running_missing, running_total, total_lookup

    outfile = out_dir + "ml_cp18_" + symbol + getDateStrFromPath(in_zip_file) + ".csv"
    print(f"Processing {in_zip_file} => {outfile}")
    if os.path.exists(outfile):
        print(f"\tAssessment File Exist, skipping directory: {outfile}")
        return

    pdOptionList = None  # Data Frame all options Contracts for the symbol
    pdOptionList3wC = None  # 3 week calls only
    pdStockQuotes = None  # Data Frame all date/time quotes for the symbol
    projection = None
    df = None
    pdOptionQuotesIdx = {}
    expiryList = []  # list of expiry we are interested in for the given date
    running_missing = 0
    running_total = 0
    total_lookup = 0
    FileUtil.reset_quote_cache()

    if not loadBasicData(in_zip_file, symbol):
        log.error("Cant find data in this dir: " + in_zip_file)
        return

    running_total = running_missing = 0
    total_lookup = len(pdStockQuotes) * 18

    df = pdStockQuotes.apply(lambda x: expandX(x['time'], x['con_id'], x['last']), axis=1, result_type='expand')
    projection = pdStockQuotes.merge(df, on="time", how="outer")
    # for col in projection.columns: print(f"{ctr}: {col}")

    #delta_labels = ["p5s", "p15s", "p30s", "p60s", "p300s", "p600s", "n5s", "n15s", "n30s", "n60s", "n300s", "n600s"]
    #delta_values = [5, 15, 30, 60, 300, 600, -5, -15, -30, -60, -300, -600]
    #delta_quarts = [3, 3, 5, 5, 7, 7, 3, 3, 5, 5, 7, 7]
    #bucket_labels = [ bucket_p5s, bucket_p15s....]

    for ctr_bucket_labels in range(len(bucket_labels)):
        new_col = bucket_labels[ctr_bucket_labels]
        from_col = delta_labels[ctr_bucket_labels] + '_delta'
        no_bins = delta_quarts[ctr_bucket_labels]
        min_val = projection[from_col].min()
        max_val = projection[from_col].max()
        range_value = (max_val - min_val) / no_bins
        from_series = projection[from_col].squeeze()
        quartile_vals = from_series.quantile(np.linspace(start=0, stop=1, num=(no_bins+1)), 'lower').tolist()
        quartile_vals.pop(0)
        print(f"ctr={ctr_bucket_labels}: {new_col} from_col={from_col} "
              f"bins={no_bins} min={min_val:.3f} max={max_val:.3f} range={range_value:.3f} {quartile_vals}]")
        projection[new_col] = projection.apply(lambda x: bucket_it2(x[from_col], quartile_vals), axis=1, result_type='expand')

    projection.to_csv(outfile, float_format='%.6f', index=False)

if __name__ == "__main__":

    config = {}  # parameter config object

    pd.set_option('display.max_columns', None)
    config = FileUtil.readConfig(sys.argv[1])
    symbol_m = config["stock"]

    data_dir_m = os.getcwd() + "/" + config["ib"]["data_dir"] + "/"
    out_dir_m = os.getcwd() + "/" + config["ml18"]["data_dir"] + "/"

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
