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

# TODO
# 1. read data
# 2. filter data to 945-1545
# 3. filter drop 1% max, min
#        df[df.a between  df.a.quantile(.01) and  df.a.quantile(.99)]
# 4. Normalize/Standardize data
# 5. Define variables
#     entry_sigma_window = [ -2, -1 ]
#     hold_sigma_window = [ -2.5, 1 ]
#     max_seconds_stayin = 5 * 60
#     max_hold_positions = 20
#     min_seconds_buy_spacing
# 6. for each stock + option, add these columns:
#      window_avg
#      window_std
#      t_decision[buy/sell]
#
# 7. loop through create new pd.  This is detailed report
#       buy_contract_id
#       buy_symbol
#       buy_price
#       buy_stdev
#       sell_price
#       sell_stdev
#       duration
#
# 8 Summary Report output
#        contract_id, symbol,
#        avg(buy_price), avg(buy_stdev),
#        avg(sell_price), avg(sell_stdev),
#        count(*) avg(duration),
#        avg(net), stdev(net)




pdOptionList: pd.DataFrame = None     # Data Frame all options Contracts for the symbol
pdOptionList3_wData: pd.DataFrame = None     # options with data
pdStockQuotes: pd.DataFrame = None    # Data Frame all date/time quotes for the symbol
pdOptionQuotesIdx = {}


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
        curPd = curPd[(curPd['time'] % 1000000).between(94500, 1545000)]
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
    min_rows = 17000
    for file in glob.glob(startingDir + "/oq_" + symbol + "*csv"):

        curPd = pd.read_csv(file)
        if curPd.shape[0] < min_rows:
            print(f"Dropping file [{file}] with shape {curPd.shape} because there is less than {min_rows}.  ")
            continue
        else:
            print(f"Adding file [{file}] with shape {curPd.shape}")

        curPd_cont_id = curPd.loc[0, "con_id"]
        optionPd = pdOptionList.loc[pdOptionList['con_id'] == curPd_cont_id]
        if pdOptionList3_wData is None:
            pdOptionList3_wData = optionPd
        else:
            pdOptionList3_wData = pdOptionList3_wData.append(optionPd, ignore_index=True)

        # Store only 9:25 to 16:10 data for quotes
        curPd = curPd[(curPd['time'] % 1000000).between(93000, 160000)]
        pdOptionQuotesIdx[curPd["con_id"].iloc[0]] = curPd
        #for index, row in curPd.iterrows():
        #    hash_idx = str(row.con_id) + ":" + str(row.time)
        #    # print (index, '->', row, '==>', hash_idx)
        #    pdOptionQuotesIdx[hash_idx] = row

    # No files in the directory
    if len(pdOptionQuotesIdx) == 0:
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


# 4. Normalize/Standardize data
# 6. for each stock + option, add these columns:
def get_decision(optQuotePd, time, col_name, col_value, discard_two_pct=True):
    global config

    retValue = {}
    retValue["time"] = time

    start_time = time - config["window_time"]
    new_df = optQuotePd [optQuotePd["time"].between(start_time, time, inclusive="both") ]
    if (new_df.shape[0] < (time - start_time) * 0.5):
        retValue["buy_sell"] = f"NotEnoughData {new_df.shape[0]} / {time - start_time}"
        return retValue

    new_df.sort_values(by="time")

    if discard_two_pct:
        #new_df = new_df[newdf.a between  newdf.a.quantile(.01) and  newdf.a.quantile(.99)]
        pass

    retValue["window_mean"] = new_df[col_name].mean()
    retValue["window_std"] = new_df[col_name].std()

    min_buy_value = retValue["window_mean"] + (retValue["window_std"]  * config["window_buy_sigma_range"][0])
    max_buy_value = retValue["window_mean"] + (retValue["window_std"]  * config["window_buy_sigma_range"][1])
    retValue["min_buy_value"] = min_buy_value
    retValue["max_buy_value"] = max_buy_value

    min_sell_value = retValue["window_mean"] + (retValue["window_std"]  * config["window_hold_sigma_range"][0])
    max_sell_value = retValue["window_mean"] + (retValue["window_std"]  * config["window_hold_sigma_range"][1])
    retValue["min_sell_value"] = min_sell_value
    retValue["max_sell_value"] = max_sell_value

    if min_buy_value <= col_value <= max_buy_value:
        retValue["buy_sell"] = "buy"
    elif col_value < min_sell_value or col_value > max_sell_value:
        retValue["buy_sell"] = "sell"
    else:
        retValue["buy_sell"] = ""

    return retValue

#
#
def find_sell(optQuotePd, buyQuote):
    buy_time = buyQuote["time"]
    buy_last = buyQuote["last"]
    end_time = buy_time + (config["window_time"] % 60 * 100) + (config["window_time"]//60)
    start_time = buy_time + 5
    new_df = optQuotePd[optQuotePd["time"].between(start_time, end_time, inclusive="both")]
    new_df.sort_values(by="time")
    if new_df.shape[0] == 0:
        return buy_time, buyQuote["time"], buyQuote["bid"], \
               buyQuote["ask"], buyQuote["last"], 0, 0

    # find the 1st/next row with sell
    # if not use the very last quote row
    for index, quote in new_df.iterrows():
        if quote["last"] < buyQuote["min_sell_value"] or quote["last"]> buyQuote["max_sell_value"]:
            break

    sq = pdStockQuotes.loc [ pdStockQuotes['time']== quote["time"] ]
    strike_price =
    strike_delta = sq ["last"] - strike_price
    days_left = 0


    return buyQuote["time"], quote["time"], quote["bid"], quote["ask"], quote["last"],  quote["time"] - buy_time, quote['last'] - buy_last


#
#
#
def main(in_zip_file, out_dir, config):
    global pdStockQuotes, pdOptionList, pdOptionQuotesIdx, projection, df, pdOptionList3_wData

    outfile = out_dir + "sigma_security_" + config["stock"] + getDateStrFromPath(in_zip_file) + ".csv"
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

    if not loadBasicData(in_zip_file, config["stock"]):
        log.error("Cant find data in this dir: " + in_zip_file)
        return

    # get_decision(optQuotePd, time, col_name, col_value, discard_two_pct=True):
    col_name = "last"
    wSellPdAll = None
    i: int = 1
    for contract_no in pdOptionQuotesIdx:
        optQuotePd = pdOptionQuotesIdx[contract_no]
        df = optQuotePd.apply(lambda x: get_decision(optQuotePd, x['time'], col_name, x[col_name]), axis=1, result_type='expand')
        optQuotePd = optQuotePd.merge(df, on="time", how="outer")

        transPd = pd.DataFrame()
        for index, quote in optQuotePd.iterrows():
            buy_sell: str = quote["buy_sell"]
            # print (buy_sell, type(buy_sell))
            if buy_sell == "":
                continue
            elif buy_sell == "sell":
                continue
            elif "NotEnoughData" in buy_sell:
                continue
            elif buy_sell == "buy":
                trans = {}
                trans["time"], trans["sell_time"], trans["sell_bid"], trans["sell_ask"], trans["sell_last"], \
                    trans["sell_duration"], trans["sell_net"] = find_sell(optQuotePd, quote)
                transPd = transPd.append(trans, ignore_index=True)
            else:
                print(f">{quote['buy_sell']}<")
                raise Exception("Unexpected buy_sell value")
        transPd.astype({"time": int, "sell_time": int})
        optQuotePd2 = optQuotePd.merge(transPd, on="time", how="outer")
        # probably don't need to put it back the updated pd... but just in case
        # pdOptionQuotesIdx[contract_no] = optQuotePd
        # save to file
        # optQuotePd.to_csv(outfile.replace(".csv", str(contract_no) + ".csv"), float_format='%.6f', index=False)
        wSellPd = optQuotePd2.loc[optQuotePd2["buy_sell"] == "buy"]
        if wSellPdAll is None:
            wSellPdAll = wSellPd
        else:
            wSellPdAll = wSellPdAll.append(wSellPd, ignore_index=True)
        wSellPdAll.to_csv(outfile, float_format='%.6f', index=False)
        print(f"{i} of {len(pdOptionQuotesIdx)}: completed contract {contract_no} found rows {optQuotePd.shape} saved rows "
              f"{wSellPd.shape} total {wSellPdAll.shape}")
        i += 1

if __name__ == "__main__":

    config = {}  # parameter config object
    config = FileUtil.readConfig(sys.argv[1])

    # 5. Define variables
    config["window_time"] = 15 * 60 ## 15 minutes * 60 seconds
    config["window_buy_sigma_range"] = [ -2, -1 ]
    config["window_hold_sigma_range"] = [ -2.5, 2 ]
    config["window_max_stay"] = 5 * 60
    config["max_hold_positions"] = 20
    config["min_seconds_buy_spacing"] = config["window_time"] / 10
    symbol_m = config["stock"]

    pd.set_option('display.max_columns', None)


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
        main(zip_file, out_dir_m, config)


