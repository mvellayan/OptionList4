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

#logging.basicConfig(level=logging.ERROR)
logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%H:%M:%S')
log = logging.getLogger("myLogger")

pdOptionList: pd.DataFrame = None     # Data Frame all options Contracts for the symbol
pdStockQuotes: pd.DataFrame = None    # Data Frame all date/time quotes for the symbol
optionQuotesDict = {}
stockQuoteDict = {}

def lookupStockQutoe(pTime):
    ret = stockQuoteDict.get(pTime, 0)
    return  ret


def loadBasicData(in_zip_file, symbol):
    global pdStockQuotes, pdOptionList, optionQuotesDict, stockQuoteDict
    stockQuoteDict = {}

    createdTmpDir = False
    # 1 Unzip the zip file in a temp dir:
    if os.path.exists(in_zip_file):
        createdTmpDir = True
        startingDir = in_zip_file[ : in_zip_file.rfind("/")] + "/" + FileUtil.getDateTimeStamp(1)
        os.makedirs(startingDir, exist_ok=True)
        unzip_file(directory_name=startingDir, zip_file_name=in_zip_file)
        log.info(f"unzippeddir {startingDir}")

    # 2. Load/Accumulate pdStockQuotes -- Stock Quotes
    for file in glob.glob(startingDir + "/sq_" + symbol + "_" + "*csv"):
        curPd = pd.read_csv(file)
        # Store only 9:25 to 16:10 data for quotes
        curPd = curPd[(curPd['time'] % 1000000).between(93000, 160000)]
        if pdStockQuotes is None:
            pdStockQuotes = curPd
        else:
            pdStockQuotes = pdStockQuotes.append(curPd, ignore_index=True)

    #
    # No files in the directory
    if pdStockQuotes is None:
        log.error("No files in the directory?? " + startingDir + "/sq_" + symbol + "_" + "*csv")
        return False
    else:
        log.info(f"Loaded stock_quote {pdStockQuotes.shape}")
    # Load into cache
    for index, row in pdStockQuotes.iterrows():
        stockQuoteDict[row['time']] = row['last']
    pdStockQuotes.rename(columns={"last": "stock_last"}, inplace=True)

    # 4. Load/Accumulate pdOptionList -- options List
    for file in glob.glob(startingDir + "/ol_" + symbol + "*csv"):
        ol = pd.read_csv(file)
        if pdOptionList is None:
            pdOptionList = ol
        else:
            pdOptionList = pdOptionList.append(ol, ignore_index=True)
    pdOptionList.drop_duplicates(inplace=True, subset=['con_id'])
    log.info(f"Loaded pdOptionList {pdOptionList.shape}")


    min_rows = 17000
    row_count = 0
    file_added = 0
    file_dropped = 0
    #
    # 5. Load/Accumulate pdOptionQuotesIdx -- Options Quotes
    for file in glob.glob(startingDir + "/oq_" + symbol + "*csv"):
        # clean up
        curPd = None
        option_contract = None

        curPd = pd.read_csv(file)
        if curPd.shape[0] < min_rows:
            # print(f"Dropping file [{file}] with shape {curPd.shape} because there is less than {min_rows}.  ")
            file_dropped += 1
            continue
        else:
            # print(f"Adding file [{file}] with shape {curPd.shape}")
            file_added += 1
            row_count += curPd.shape[0]

        # Store only 9:25 to 16:10 data for quotes
        curPd = curPd[(curPd['time'] % 1000000).between(93000, 160000)]

        # To join on symbol column, make them strings & then merge the Pds
        curPd['symbol'] = curPd['symbol'].astype(str)
        # pdOptionList['symbol'] = pdOptionList['symbol'].astype(str)
        curPd = curPd.merge(ol, on='symbol', how='outer')

        option_contract = pdOptionList.loc[pdOptionList['symbol'] == curPd["symbol"][0]]

        curPd["stock_last"] = curPd.apply(lambda lRow: lookupStockQutoe(lRow['time']), axis=1)
        curPd["delta_strike"] = curPd['stock_last'] - curPd['strike']  # add delta_strike column
        curPd["delta_expiry"] = ((curPd['time'] // 1000000) - curPd['expiry']) * -1
        curPd["ask_bid_spread"] = curPd["ask"] - curPd["bid"]

        optionQuotesDict[option_contract['con_id'].iloc[0]] = curPd

    # No files in the directory
    if len(optionQuotesDict) == 0:
        log.error("No complete option quote files in the directory?? " + startingDir + "/oq_" + symbol + "_" + "*csv")
        return False
    else:
        log.info(f"Loaded options [{len(optionQuotesDict)}] option quote: [{row_count}] file added {file_added} dropped {file_dropped} total {file_dropped+ file_added}")


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

    # Window looking back
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

    buy_time = np.int64(buyQuote["time"])
    buy_last = buyQuote["last"]

    end_time = int(FileUtil.dateAdd(FileUtil.getDateObjFromStr(buy_time), seconds=int(config["window_time"])))
    start_buyback_delay = int(FileUtil.dateAdd(FileUtil.getDateObjFromStr(buy_time), seconds=15))

    new_df = optQuotePd[optQuotePd["time"].between(start_buyback_delay, end_time, inclusive="both")]
    new_df.sort_values(by="time")
    if new_df.shape[0] == 0:
        return buy_time, buyQuote["time"], buyQuote["bid"], \
               buyQuote["ask"], buyQuote["last"], 0, 0

    # find the 1st/next row with sell
    # if not use the very last quote row
    for index, quote in new_df.iterrows():
        if quote["last"] < buyQuote["min_sell_value"] or quote["last"] > buyQuote["max_sell_value"]:
            break

    transaction = {
        "time": buyQuote["time"],
        "sell_search_begin": start_buyback_delay,
        "sell_search_end":  end_time,
        "sell_time": quote["time"],
        "sell_bid": quote["bid"],
        "sell_ask": quote["ask"],
        "sell_last": quote["last"],
        "sell_duration" : quote["time"] - buy_time,
        "sell_net":  quote['last'] - buy_last
        }
    # print("returning: ", transaction)
    return transaction

#
#
#
def main(in_zip_file, out_dir, config):
    global pdStockQuotes, pdOptionList, optionQuotesDict, projection

    outfile = out_dir + "sigma_security_" + config["stock"] + getDateStrFromPath(in_zip_file) + ".csv"
    log.info(f"Processing {in_zip_file} => {outfile}")
    if os.path.exists(outfile):
        log.error(f"\nAssessment File Exist, skipping directory: {outfile}")
        return


    pdOptionList = None  # Data Frame all options Contracts for the symbol
    pdStockQuotes = None  # Data Frame all date/time quotes for the symbol
    projection = None
    optionQuotesDict = {}
    FileUtil.reset_quote_cache()

    if not loadBasicData(in_zip_file, config["stock"]):
        log.error("Cant find data in this dir: " + in_zip_file)
        return

    # get_decision(optQuotePd, time, col_name, col_value, discard_two_pct=True):
    col_name = "last"
    wSellPdAll = None
    i: int = 1
    for contract_no in optionQuotesDict:
        # get optionQuote pd
        optQuotePd = optionQuotesDict[contract_no]

        # add buy / sell / other decision
        log.info(f"Getting BUY signal for [{contract_no}]")
        df = optQuotePd.apply(lambda x: get_decision(optQuotePd, x['time'], col_name, x[col_name]), axis=1, result_type='expand')
        optQuotePd = optQuotePd.merge(df, on="time", how="outer")

        log.info(f"Getting SELL signal for [{contract_no}]")
        # find sell / exit info for all the "buy"
        transPd = pd.DataFrame()
        for index, quote in optQuotePd.iterrows():
            buy_sell: str = quote["buy_sell"]
            # print (buy_sell, type(buy_sell))
            if buy_sell == "buy":
                try:
                    ins_obj = find_sell(optQuotePd, quote)
                    transPd = transPd.append(ins_obj, ignore_index=True)
                except Exception as e:
                    print(ins_obj)
                    print("error:", e)
            elif (buy_sell in ["", 'sell']) or ("NotEnoughData" in buy_sell):
                continue
            else:
                print(f">{quote['buy_sell']}<")
                raise Exception("Unexpected buy_sell value")

        transPd.astype({"time": int, "sell_time": int})
        optQuotePd2 = optQuotePd.merge(transPd, on="time", how="outer")

        #
        # Create summary panda
        log.info(f"Creating summary panda for [{contract_no}] for all sell signals")
        wSellPd = optQuotePd2.loc[optQuotePd2["buy_sell"] == "buy"]
        if wSellPdAll is None:
            wSellPdAll = wSellPd
        else:
            wSellPdAll = wSellPdAll.append(wSellPd, ignore_index=True)
        wSellPdAll.to_csv(outfile, float_format='%.6f', index=False)

        wSellPdAll['trade_date'] = wSellPdAll['time'].astype(str).str[:8] # missing trade_date???????????????????????

        wSellPdAllSummary = wSellPdAll.groupby(['symbol']).agg({
            'trade_date': ['max'],
            'symbol': ['max', 'count'],
            'delta_strike': ['mean'],
            'delta_expiry': ['mean'],
            'sell_duration': ['mean', 'std'],
            'ask_bid_spread': ['mean'],
            'sell_net': ['mean', 'std', 'sum']
        })


        summary_file_name = outfile.replace('.csv','_summary.csv')
        with open(summary_file_name, 'w') as f:
            f.write('# Model Parameters\n')
            f.write(f'# \tWindow_time\t{config["window_time"]}\tMax seconds option will be held.  Also time window looking back for avg/std\n')
            f.write(f'# \tBuy_sigma_range\t{" ".join(str(x) for x in config["window_buy_sigma_range"])}')
            f.write(f'# \tHold_sigma_range\t{" ".join(str(x) for x in config["window_hold_sigma_range"])}')
            f.write(f'# \tSpacing Seconds\t{config["min_seconds_buy_spacing"]}')
            f.write("#")
        wSellPdAllSummary.to_csv(summary_file_name, float_format='%.6f', mode='a', index=False)
        print(f"{i} of {len(optionQuotesDict)}: completed contract {contract_no} found rows {optQuotePd.shape} saved rows "
              f"{wSellPd.shape} total {wSellPdAll.shape}")
        i += 1


if __name__ == "__main__":

    config = {}  # parameter config object
    config = FileUtil.readConfig(sys.argv[1])

    # 5. Define variables
    config["window_time"] = 15 * 60 ## Max Window to hold this position = 15 minutes * 60 seconds
    config["window_buy_sigma_range"] = [ -1, -.5 ]
    config["window_hold_sigma_range"] = [ -1.5, 2 ]
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


