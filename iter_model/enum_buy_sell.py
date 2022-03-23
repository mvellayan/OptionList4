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

SAMPLING_SECONDS_INTERVAL = 30
NUM_FILES_TO_READ = 16
DAYS_ALREADY_PROCESSED = []
DAYS_LOADED = []
MAX_DAYS_TO_PROCESS = 5
SKIP_INTERVAL = 20 # = random.randint( int(SAMPLING_SECONDS_INTERVAL * 0.70), int(SAMPLING_SECONDS_INTERVAL * 1.3))


logging.basicConfig(level=logging.ERROR,  format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%H:%M:%S')
log = logging.getLogger("myLogger")
log.setLevel(logging.INFO)

pdOptionList: pd.DataFrame = None     # Data Frame all options Contracts for the symbol
pdOptionList_wData: pd.DataFrame = None     # options with data
pdStockQuotes: pd.DataFrame = None    # Data Frame all date/time quotes for the symbol
pdOptionQuotes_by_timeContractNo = {}

class StockQuote:
    def __init__(self, en: np.ndarray):
        self.time = en[0]
        self.bid = en[1]
        self.ask = en[2]
        self.time_do = en[3]
        # self.con_id = en[0]
        # self.symbol = en[1]
        # self.time = en[2]
        # self.bid = en[3]
        # self.bid_size = en[4]
        # self.ask = en[5]
        # self.ask_size = en[6]
        # self.last = en[7]
        # self.last_size = en[8]
        # self.volume = en[9]
        # self.hist_volatility = en[10]
        # self.implied_volatility = en[11]


def getComputedComponents(quoteTime, stockQuote, optionQuote, strike, expiry):
    theta = iv = tv = None
    if stockQuote > 0:
        iv = stockQuote - strike
        if iv < 0:
            iv = 0
        tv = optionQuote - iv
        dur = get_sec_to_expire(quoteTime, expiry)
        if dur == 0 or tv == 0:
            theta = 0
        else:
            theta = (tv / dur) * 100 * 1000  # 100 = cents, 100 = basis point
    return tv, iv, theta


def loadBasicData(in_zip_file, symbol):
    global pdStockQuotes, pdOptionList, pdOptionList_wData, pdOptionQuotes_by_timeContractNo

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
        curPd = curPd[['time', 'bid', 'ask']]
        if pdStockQuotes is None:
            pdStockQuotes = curPd
        else:
            pdStockQuotes = pdStockQuotes.append(curPd, ignore_index=True)
    pdStockQuotes['time_do'] = pdStockQuotes.apply(lambda rw: FileUtil.getDateObjFromStr(rw.time, 'YYYYMMDD'), axis=1)

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
        curPd = curPd[['time', 'bid', 'ask', 'con_id']]
        # for index, row in curPd.iterrows(): ## Very slow
        for row in curPd.itertuples():
            pdOptionQuotes_by_timeContractNo[ str(row.time) + ":" + str(row.con_id)] = row

    pdOptionList_wData.drop_duplicates(inplace=True, subset=['con_id'])
    pdOptionList_wData['expiry_do'] = pdOptionList_wData.apply(lambda rw: FileUtil.getDateObjFromStr(rw.expiry, 'YYYYMMDD'), axis=1)
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


last_index = 0
def flush_row(rows, outfile_path, model_no, fields):
    global last_index

    if len(rows) <= last_index: return
    old_data_date = rows[last_index][1]
    csvwriter, outfile = getFile(outfile_path, old_data_date, model_no, fields)

    for idx in range(last_index, len(rows)):
        if old_data_date != rows[idx][1]:
            outfile.close()
            old_data_date = rows[last_index][1]
            csvwriter, outfile = getFile(outfile_path, old_data_date, model_no, fields)
        csvwriter.writerow(rows[idx])
    last_index = len(rows)
    outfile.close()


def getFile(outfile_path, o_date, model_no, fields):
    assert str(o_date).isnumeric(), "expecting 2nd filed to be a numeric date field"
    outfile = outfile_path + "/" + str(model_no) + "_" + str(o_date) + ".csv"
    if os.path.exists(outfile):
        csvfile = open(outfile, "a")
        csvwriter = csv.writer(csvfile)
    else:
        csvfile = open(outfile, "w")
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(fields)
    return csvwriter, csvfile


def get_processed_dates(outfile_path):
    retArr = []
    for file in glob.glob(outfile_path + "/*.csv"):
        try:
            retArr.append(file.split("_")[-1:][0].replace(".csv",""))
        except:
            pass
    return retArr


def main(in_zip_files, out_dir: str, symbol: str):
    global pdStockQuotes, pdOptionList, pdOptionQuotes_by_timeContractNo, projection, df, pdOptionList_wData, last_index

    # Reset all globals
    df = projection = pdStockQuotes = pdOptionList_wData = pdOptionList = None
    pdOptionQuotes_by_timeContractNo = {}
    FileUtil.reset_quote_cache()
    fields = ["sold", "o_date", "o_time", "o_stock_ask", "o_option_bid", "strike", "expiry", "o_tv", "o_iv",
              "o_theta", "o_dr", "c_date", "c_time", "c_stock_bid", "c_option_ask", "c_tv", "c_iv", "c_theta",
              "c_dr", "net_option", "net_stock", "net", "dur-days"]


    for in_zip_file in in_zip_files:
        DAYS_LOADED.append(in_zip_file.split("/")[-1:][0].replace(".zip", "")[-8:])
        if not loadBasicData(in_zip_file, symbol):
            log.error("Error loading data files in this dir: " + in_zip_file)
    print(f'\tLoading Complete: {(time.time() - startTime):.2f}')
    DAYS_LOADED.sort()
    DAYS_TO_LOAD = DAYS_LOADED[0:MAX_DAYS_TO_PROCESS]
    pdStocks = pdStockQuotes.sort_values(by=['time'])
    npStocks = pdStocks.to_numpy()
    del pdStockQuotes

    # Reset local variables
    maxStockIndex = len(pdStocks)

    for model_no in range(1, ml_model.model_logic.get_model_count()+1):
        ctr = 0
        rows = []
        last_index = 0
        last_quote_day = "<none>"
        outfile_path = out_dir + "buy_sell_" + str(model_no)
        Path(outfile_path).mkdir(parents=True, exist_ok=True)
        processed = get_processed_dates(outfile_path)

        for open_stock in pdStocks.itertuples():
            quote_day = str(open_stock.time)[0:8]
            if quote_day != last_quote_day:
                print(f"Changing quote date new {quote_day} old {last_quote_day} model {model_no}")
                if quote_day in processed:
                    print(f"This day {quote_day} will be skipped.  In processed list {processed} ")
                if quote_day not in DAYS_TO_LOAD:
                    print(f"This day {quote_day} will be skipped.  Not in DAYS_TO_LOAD list {DAYS_TO_LOAD} ")
                last_quote_day = quote_day
            if quote_day in processed: continue
            if quote_day not in DAYS_TO_LOAD: continue
            # print(f"Considering day {quote_day} for model # {model_no}.  Loading Days = {DAYS_TO_LOADED} / max = {MAX_DAYS_TO_PROCESS}")

            ctr += 1
            if ctr % SKIP_INTERVAL != 0: continue  # analyze one per (average) minute.  too much data.
            expiries = get_expiry_list(open_stock.time, noWeeks=2, pdOptionList=pdOptionList_wData)
            pdOptions = pdOptionList_wData.loc[pdOptionList_wData['expiry'].isin(expiries)]
            for optionDef in pdOptions.itertuples():
                open_option = pdOptionQuotes_by_timeContractNo.get(str(open_stock.time) + ":" + str(optionDef.con_id), None)
                if open_option is None: continue
                # print(open_option)
                open_tv, open_iv, open_theta = getComputedComponents(open_stock.time_do, open_stock.ask, open_option.bid, optionDef.strike,
                                                                     optionDef.expiry_do)
                oexp: int = optionDef.expiry * 1000000 + 150000
                if optionDef.expiry == '20220121': oexp = optionDef.expiry * 1000000 + 110000
                #
                # Open Position
                #
                if ml_model.model_logic.open_position(model_no, open_stock.bid, open_stock.ask, open_option.bid,
                                                      open_option.ask, open_tv, open_iv, open_theta, optionDef.strike):
                    row = find_close(maxStockIndex, model_no, npStocks, oexp, open_iv, open_option, open_stock,
                                     open_theta, open_tv, optionDef)
                    rows.append(row)
                    if ctr % 1 == 0:
                        flush_row(rows, outfile_path, model_no, fields)
                        log.info(str(model_no) + " " + str(ctr) + " " + '\t'.join([str(x) for x in row]))
                    # break

        flush_row(rows, outfile_path, model_no, fields)


def find_close(maxStockIndex, model_no, npStocks, oexp, open_iv, open_option, open_stock, open_theta, open_tv,
               optionDef):
    sold = False
    for idx in range(open_stock.Index + 300, maxStockIndex, random.randint(10, 20)):
        close_stock = StockQuote(npStocks[idx])
        close_option = pdOptionQuotes_by_timeContractNo.get(str(int(close_stock.time)) + ":" + str(optionDef.con_id),
                                                            None)
        net_stock = min(close_stock.bid, optionDef.strike) - open_stock.ask
        if oexp < close_stock.time:
            row = ['expired', open_stock.time // 1000000, open_stock.time % 1000000,
                   open_stock.ask, open_option.bid,
                   optionDef.strike, optionDef.expiry, open_tv, open_iv, open_theta,
                   (optionDef.expiry_do - open_stock.time_do).days,
                   close_stock.time // 1000000, close_stock.time % 1000000, close_stock.bid,
                   0, 0, 0, 0, FileUtil.days_between(optionDef.expiry, close_stock.time),
                   round(open_option.bid, 2), round(net_stock, 2), round(net_stock + open_option.bid, 1),
                   (close_stock.time_do - open_stock.time_do).days]
            sold = True
            break

        if close_option is None: continue
        if close_option.ask < 0 or close_option.bid < 0: continue
        net_option = open_option.bid - close_option.ask
        close_tv, close_iv, close_theta = getComputedComponents(close_stock.time_do, close_stock.bid,
                                                                close_option.ask, optionDef.strike, optionDef.expiry_do)
        if ml_model.model_logic.close_position(model_no, close_tv, close_iv, close_theta,
                                               optionDef.strike, net_stock, net_option):
            row = ['sold', open_stock.time // 1000000, open_stock.time % 1000000,
                   open_stock.ask, open_option.bid,
                   optionDef.strike, optionDef.expiry, round(open_tv, 2), round(open_iv, 2), round(open_theta, 2),
                   (optionDef.expiry_do - open_stock.time_do).days,
                   close_stock.time // 1000000, close_stock.time % 1000000, close_stock.bid, close_option.ask,
                   round(close_tv, 2), round(close_iv, 2), round(close_theta, 2),
                   FileUtil.days_between(optionDef.expiry, close_stock.time),
                   round(net_option, 2), round(net_stock, 2), round(net_stock + net_option, 1),
                   (close_stock.time_do - open_stock.time_do).days]
            sold = True
            break

    if not sold:
        # print("Not Sold!", last)
        if close_option is None:
            row = ['not sold1', open_stock.time // 1000000, open_stock.time % 1000000,
                   open_stock.ask, open_option.bid,
                   optionDef.strike, optionDef.expiry, round(open_tv, 2), round(open_iv, 2), round(open_theta, 2),
                   (optionDef.expiry_do - open_stock.time_do).days,
                   close_stock.time // 1000000, close_stock.time % 1000000, close_stock.bid,
                   0, 0, 0, 0,
                   FileUtil.days_between(optionDef.expiry, close_stock.time),
                   open_option.bid, close_stock.bid - open_stock.ask,
                   round(close_stock.bid - open_stock.ask + open_option.bid, 1),
                   (close_stock.time_do - open_stock.time_do).days]
        else:
            row = ['no data', open_stock.time // 1000000, open_stock.time % 1000000,
                   open_stock.ask, open_option.bid,
                   optionDef.strike, optionDef.expiry, open_tv, open_iv, open_theta,
                   (optionDef.expiry_do - open_stock.time_do).days,
                   close_stock.time // 1000000, close_stock.time % 1000000, close_stock.bid, close_option.ask,
                   round(close_tv, 2), round(close_iv, 2), round(close_theta, 2),
                   FileUtil.days_between(optionDef.expiry, close_stock.time),
                   net_option, net_stock, round(net_stock + net_option, 1),
                   (close_stock.time_do - open_stock.time_do).days]
    return row


def getParams():
    config = FileUtil.readConfig(sys.argv[1])
    start_date = sys.argv[2]
    pd.set_option('display.max_columns', None)
    l_symbol = config["stock"]
    data_dir = os.getcwd() + "/" + config["ib"]["data_dir"] + "/"
    l_out_dir = os.getcwd() + "/" + "iter_model/data/"

    file_list = []
    for rootdir, dirs, files in os.walk(data_dir):
        for subdir in dirs:
            full_dir = os.path.join(rootdir, subdir)
            search_mask = full_dir + "/" + l_symbol + '*.zip'
            file_list += glob.glob(search_mask)

    file_list.sort()
    for index, zip_file in enumerate(file_list):
        if zip_file[-16:] in [l_symbol + start_date + '.zip']:
            file_list_subset = file_list[index:index + NUM_FILES_TO_READ]
            # file_list_subset = file_list[index:index + 16]
            break

    return l_symbol, file_list_subset, l_out_dir


if __name__ == "__main__":
    symbol, file_list, out_dir = getParams()
    startTime = time.time()
    main(file_list, out_dir, symbol)
    print(f'TIME Main: {(time.time() - startTime):.2f}')

