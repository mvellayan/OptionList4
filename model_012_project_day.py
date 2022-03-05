import argparse
import time
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
from utils.FileUtil import makeDirectory, unzip_file, get_sec_to_expire, getDateStrFromPath, dateAddInt
from utils.IBUtil import get_expiry_list
import csv

logging.basicConfig(level=logging.ERROR,  format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%H:%M:%S')
log = logging.getLogger("myLogger")
log.setLevel(logging.INFO)

pdOptionList: pd.DataFrame = None     # Data Frame all options Contracts for the symbol
pdOptionList_wData: pd.DataFrame = None     # options with data
pdStockQuotes: pd.DataFrame = None    # Data Frame all date/time quotes for the symbol
pdOptionQuotes_by_timeContractNo = {}
pdOptionQuotes_by_ContractNoTime = {}

class StockQuote:
    def __init__(self, en: np.ndarray):
        self.con_id = en[0]
        self.symbol = en[1]
        self.time = en[2]
        self.bid = en[3]
        self.bid_size = en[4]
        self.ask = en[5]
        self.ask_size = en[6]
        self.last = en[7]
        self.last_size = en[8]
        self.volume = en[9]
        self.hist_volatility = en[10]
        self.implied_volatility = en[11]



def getComputedComponents(quoteTime, stockQuote, optionQuote, strike, expiry):
    """
    with quote & strike we compute tv & iv
    with quoteTime & expiry, compute theta
    :param quoteTime:
    :param quote:
    :param strike:
    :param expiry:
    :return:
        tv - time value.  can be pos or neg
        iv - intrinsic value. must be >= 0
    """
    tv = None
    iv = None
    theta = None

    if stockQuote > 0:
        iv = stockQuote - strike
        if iv < 0:
            iv = 0
        tv = optionQuote - iv
        dur = get_sec_to_expire(
            FileUtil.getDateObjFromStr(quoteTime), FileUtil.getDateObjFromStr(expiry, 'YYYYMMDD'))
        if dur == 0 or tv == 0:
            theta = 0
        else:
            theta = (tv / dur) * 100 * 1000  # 100 = cents, 100 = basis point
    return round(tv,3), round(iv,3), round(theta,5)

def expandX(quoteTime, quoteLast):
    global pdStockQuotes, pdOptionList, pdOptionList_wData, pdOptionQuotes_by_timeContractNo, pdOptionQuotes_by_ContractNoTime

    quoteTimeObj = FileUtil.getDateObjFromStr(quoteTime)
    # pprint (list)

    retDict = {}
    retDict["time"] = quoteTime

    # retDict["p0"] = FileUtil.get_value_with_delta(pdStockQuotes, quoteTimeObj, 0)
    sorted_ol = pdOptionList_wData.sort_values(by=['expiry', 'strike'], ascending=True)
    for index, contract in sorted_ol.iterrows():
        # print(row['c1'], row['c2'])


        idx = pdOptionQuotes_by_timeContractNo.get(str(contract.con_id) + ":" + str(quoteTime))

        if idx is not None:

            col_prefix = str(f"C_{(contract.expiry % 1000):04d}_{contract.strike}")

            retDict[col_prefix + "_symbol"] = idx["symbol"]
        #    retDict[col_prefix + "_bid_ask_delta"] = idx["bid"] - idx["ask"]
            retDict[col_prefix + "_ask"] = idx["ask"]
        #    retDict[col_prefix + "_ask_size"] = idx["ask_size"]
            retDict[col_prefix + "_bid"] = idx["bid"]
        #    retDict[col_prefix + "_bid_size"] = idx["bid_size"]
        #    retDict[col_prefix + "_last"] = idx["last"]
        #    retDict[col_prefix + "_last_size"] = idx["last_size"]
            retDict[col_prefix + "_strike"] = contract.strike
            retDict[col_prefix + "_strike_delta"] = quoteLast - contract.strike

            tv, iv, theta = getComputedComponents(quoteTime, quoteLast, (idx["bid"]+idx["ask"])/2, contract.strike, contract.expiry)
            retDict[col_prefix + "_tv"] = tv
            retDict[col_prefix + "_iv"] = iv
            retDict[col_prefix + "_theta"] = theta

        #    retDict[col_prefix + "_" + "implied_volatility"] = idx["implied_volatility"]
        #    retDict[label] = FileUtil.get_value_with_delta(pdStockQuotes, quoteTimeObj, value)

    return retDict

def loadBasicData(in_zip_file, symbol):
    global pdStockQuotes, pdOptionList, pdOptionList_wData, pdOptionQuotes_by_timeContractNo, pdOptionQuotes_by_ContractNoTime

    log.info(f"Starting to load file {in_zip_file}")
    createdTmpDir = False
    # 1 Unzip the zip file in a temp dir:
    if os.path.exists(in_zip_file):
        createdTmpDir = True
        startingDir = in_zip_file[ : in_zip_file.rfind("/")] + "/" + FileUtil.getDateTimeStamp(1)
        os.makedirs(startingDir, exist_ok=True)
        unzip_file(directory_name=startingDir, zip_file_name=in_zip_file)
        log.debug(f"unzip [{createdTmpDir}] into directory [{startingDir}]")
    # 2. Load pdStockQuotes -- Stock Quotes
    for file in glob.glob(startingDir + "/sq_" + symbol + "_" + "*csv"):
        curPd = pd.read_csv(file)
        # Store only 9:30 to 16:00 data for quotes
        curPd = curPd[(curPd['time'] % 1000000).between(93000, 160000)]
        if pdStockQuotes is None:
            pdStockQuotes = curPd
        else:
            pdStockQuotes = pdStockQuotes.append(curPd, ignore_index=True)

    # No files in the directory
    if pdStockQuotes is None:
        log.error(f"No files in the directory [{file}]?? ")
        return False
    else:
        log.debug(f"Adding stock {symbol} from {pdStockQuotes.shape} w/ size ")

    # 3. Load pdOptionList -- options List
    for file in glob.glob(startingDir + "/ol_" + symbol + "*csv"):
        ol = pd.read_csv(file)
        if pdOptionList is None:
            pdOptionList = ol
        else:
            pdOptionList = pdOptionList.append(ol, ignore_index=True)
    pdOptionList.drop_duplicates(inplace=True, subset=['con_id'])

    # 3.b load pdOptionList3wC
    # filtering now for performance improvement.
    # pdOptionList3_wData = pdOptionList # Need to filter out options without data

    # 4. Load pdOptionQuotesIdx -- Options Quotes
    for file in glob.glob(startingDir + "/oq_" + symbol + "*C*csv"):

        curPd = pd.read_csv(file)
        curPd_cont_id = curPd.loc[0, "con_id"]
        log.debug(f"Adding option {curPd_cont_id} from {curPd.shape} w/ size {file}")
        p = pdOptionList.loc[pdOptionList['con_id'] == curPd_cont_id]

        if pdOptionList_wData is None:
            pdOptionList_wData = p
        else:
            pdOptionList_wData = pdOptionList_wData.append(p, ignore_index=True)
            pass
        # Store only 9:25 to 16:10 data for quotes
        curPd = curPd[(curPd['time'] % 1000000).between(93000, 160000)]
        # for index, row in curPd.iterrows(): ## Very slow
        for row in curPd.itertuples():
            pdOptionQuotes_by_timeContractNo[ str(row.time)   + ":" + str(row.con_id) ] = row
            pdOptionQuotes_by_ContractNoTime[ str(row.con_id) + ":" + str(row.time) ] = row
    pdOptionList_wData.drop_duplicates(inplace=True, subset=['con_id'])

    # 6. Cleanup
    if createdTmpDir:
        log.debug(f"removing temp dir {startingDir}")
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

def flush_row(rows, outfile, write_mode="a"):
    with open(outfile, write_mode) as csvfile:
        csvwriter = csv.writer(csvfile)
        for row in rows:
            csvwriter.writerow(row)
    rows.clear()

def main(in_zip_files, out_dir, symbol: str):
    global pdStockQuotes, pdOptionList, pdOptionQuotes_by_timeContractNo, pdOptionQuotes_by_ContractNoTime, projection, df, pdOptionList_wData

    outfile = out_dir + "ml_iteration_" + symbol + getDateStrFromPath(in_zip_files[0]) + ".csv"
    log.info(f"Processing {in_zip_files[0]} => {outfile}")
    if os.path.exists(outfile):
        print(f"\tAssessment File Exist, skipping directory: {outfile}")
        # return

    pdOptionList = None  # Data Frame all options Contracts for the symbol
    pdOptionList_wData = None  # 3 week calls only
    pdStockQuotes = None  # Data Frame all date/time quotes for the symbol
    projection = None
    df = None
    pdOptionQuotes_by_timeContractNo = {}
    pdOptionQuotes_by_ContractNoTime = {}
    FileUtil.reset_quote_cache()

    for in_zip_file in in_zip_files:
        if not loadBasicData(in_zip_file, symbol):
            log.error("Error loading data files in this dir: " + in_zip_file)
    print(f'\tLoading Complete: {(time.time() - startTime):.2f}')

    pdStocks = pdStockQuotes.sort_values(by=['time'])
    npStocks = pdStocks.to_numpy()

    fields = [["ctr", "Sold", "open_date", "open_time", "open_stock_ask", "open_option_bid", "strike", "expiry", "open_tv",
              "open_iv", "open_theta", "close_date", "close_time", "close_sock_bid", "close_option_ask", "close_tv", "cloe_iv",
              "close_theta", "net_stock", "net_option", "net", "dur-days"]]
    flush_row(fields, outfile, write_mode="w")
    print('\t'.join([x for x in fields]))

    maxStockIndex = len(pdStocks)
    ctr = 0
    rows = []
    for open_stock in pdStocks.itertuples():
        ctr += 1
        if ctr % 50 != 0: continue
        expiries = get_expiry_list(open_stock.time, noWeeks=2, pdOptionList=pdOptionList_wData)
        pdOptions = pdOptionList_wData.loc[pdOptionList_wData['expiry'].isin(expiries)]
        for optionDef in pdOptions.itertuples():
            # print(open_stock)
            # print(optionDef_buy)
            open_option = pdOptionQuotes_by_timeContractNo.get(str(open_stock.time) + ":" + str(optionDef.con_id), None)
            if open_option is None: continue
            # print(open_option)
            open_tv, open_iv, open_theta = getComputedComponents(open_stock.time, open_stock.ask, open_option.bid, optionDef.strike, optionDef.expiry)
            if (open_tv > 2.3) and (open_theta > 1) and (optionDef.strike+1) > open_stock.ask:  # Values from week 2 average!
                # print(f"{open_stock.time}\t{open_stock.ask}\t{open_option.bid}\t{optionDef.strike}\t{optionDef.expiry}\t{open_tv:.3f}\t{open_iv:.3f}\t{open_theta:.3f}")
                # start_close_time = dateAddInt(open_stock.time, seconds=300)
                # close_stockPd = pdStocks.loc [pdStocks['time'] >= start_close_time]
                sold = False
                ctr = 0
                # for close_stock in close_stockPd.itertuples():
                for idx in range (open_stock.Index + 300, maxStockIndex, 10):
                    close_stock = StockQuote(npStocks[idx])
                    ctr += 1
                    close_option = pdOptionQuotes_by_timeContractNo.get(str(close_stock.time) + ":" + str(optionDef.con_id), None)
                    if close_option is None: continue
                    if close_option.ask < 0 or close_option.bid < 0: continue
                    tv_sell, iv_sell, theta_sell = getComputedComponents(close_stock.time, close_stock.bid,
                                                                         close_option.ask, optionDef.strike, optionDef.expiry)
                    net_stock = close_stock.bid - open_stock.ask
                    net_option = open_option.bid - close_option.ask
                    if tv_sell < 1 and (net_stock + net_option > 0):
                        row=[ctr, 'sold', open_stock.time // 1000000, open_stock.time % 1000000, open_stock.ask, open_option.bid,
                            optionDef.strike, optionDef.expiry, open_tv, open_iv, open_theta,
                            close_stock.time // 1000000, close_stock.time % 1000000, close_stock.bid, close_option.ask, tv_sell, iv_sell,
                            theta_sell, net_stock, net_option, net_stock + net_option,
                            (close_stock.time // 1000000 - open_stock.time // 1000000)]
                        rows.append(row)
                        sold = True
                        break

                if not sold:
                    if close_option is None:
                        row = [ctr, 'Not Sold1', open_stock.time // 1000000, open_stock.time % 1000000,
                            open_stock.ask, open_option.bid,
                           optionDef.strike, optionDef.expiry, open_tv, open_iv, open_theta,
                           close_stock.time // 1000000, close_stock.time % 1000000, close_stock.bid,
                               0, 0, 0, 0,
                               close_stock.bid - open_stock.ask, open_option.bid, close_stock.bid - open_stock.ask + open_option.bid,
                           (close_stock.time // 1000000 - open_stock.time // 1000000)]
                    else:
                        row = [ctr, 'Not Sold2', open_stock.time // 1000000, open_stock.time % 1000000,  open_stock.ask, open_option.bid,
                           optionDef.strike, optionDef.expiry, open_tv, open_iv, open_theta,
                           close_stock.time // 1000000, close_stock.time % 1000000,  close_stock.bid,
                                close_option.ask, tv_sell, iv_sell, theta_sell,
                               net_stock, net_option, net_stock + net_option,
                           (close_stock.time // 1000000 - open_stock.time // 1000000)]
                    rows.append(row)

                if ctr % 100 == 0: flush_row(rows, outfile)
                log.info('\t'.join([str(x) for x in row]))

    print(f"max seen ctr = {ctr}")
    print("last stock", open_stock)
    flush_row(rows, outfile)

    #df = pdStockQuotes.apply(lambda x: expandX(x['time'], x['last']), axis=1, result_type='expand')
    #print(f'\tExpansion Complete: {(time.time() - startTime):.2f}')

    #projection = pdStockQuotes.merge(df, on="time", how="outer")
    #print(f'\tProjection Complete: {(time.time() - startTime):.2f}')
    # for col in projection.columns: print(f"{ctr}: {col}")

    #delta_labels = ["p5s", "p15s", "p30s", "p60s", "p300s", "p600s", "n5s", "n15s", "n30s", "n60s", "n300s", "n600s"]
    #delta_values = [5, 15, 30, 60, 300, 6003, -5, -15, -30, -60, -300, -600]
    #delta_quarts = [3, 3, 5, 5, 7, 7, 3, 3, 5, 5, 7, 7]
    #bucket_labels = [ bucket_p5s, bucket_p15s....]

    #projection.to_csv(outfile, float_format='%.6f', index=False)
    #out2 = ['time', 'last']
    #out2_1 = [col for col in projection.columns if ('theta' in col) or ('tv' in col) or ('iv' in col) or ('bid' in col) or ('ask' in col)]
    #out2_1.sort()
    #out2 += out2_1
    #projection[out2].to_csv(outfile.replace(".csv","_tv.csv"), float_format='%.6f', index=False)

if __name__ == "__main__":

    config = {}  # parameter config object
    pd.set_option('display.max_columns', None)
    config = FileUtil.readConfig(sys.argv[1])
    symbol_m = config["stock"]

    data_dir_m = os.getcwd() + "/" + config["ib"]["data_dir"] + "/"
    out_dir_m = os.getcwd() + "/" + "ml_projection/data/"

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
    for index, zip_file in enumerate(file_list):
        # if zip_file[-16:] not in ['AAPL20220103.zip', 'AAPL20220104.zip']:
        print (index, zip_file)
        if zip_file[-16:] in ['AAPL20220106.zip']:
            startTime = time.time()
            main(file_list[index: index+21], out_dir_m, symbol_m)
            print(f'TIME Main: {(time.time() - startTime):.2f}')
            break

