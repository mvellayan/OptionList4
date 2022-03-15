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
def flush_row(rows, outfile, write_mode="a", flush_all=False):
    global last_index
    with open(outfile, write_mode) as csvfile:
        if write_mode == "w":
            csvfile.write(ml_model.model_logic.get_description(model_no) + "\n")
        csvwriter = csv.writer(csvfile)
        if flush_all:
            for row in rows:
                csvwriter.writerow(row)
        else:
            new_index = len(rows)
            for idx in range(last_index, new_index):
                csvwriter.writerow(rows[idx])
            last_index = new_index

    # rows.clear()

def main(model_no, in_zip_files, out_dir, symbol: str):
    global pdStockQuotes, pdOptionList, pdOptionQuotes_by_timeContractNo, projection, df, pdOptionList_wData

    #outfile = out_dir + "ml_iteration_" + symbol + getDateStrFromPath(in_zip_files[0]) + ".csv"
    outfile = out_dir + "run_" + str(model_no) + "_" + ml_model.model_logic.get_short_title(model_no) \
              + "_" + datetime.now().strftime('%m%d%H%M%S') + ".csv"
    log.info(f"Processing {in_zip_files[0]} => {outfile}")

    pdOptionList = None  # Data Frame all options Contracts for the symbol
    pdOptionList_wData = None  # 3 week calls only
    pdStockQuotes = None  # Data Frame all date/time quotes for the symbol
    projection = None
    df = None
    pdOptionQuotes_by_timeContractNo = {}
    FileUtil.reset_quote_cache()

    for in_zip_file in in_zip_files:
        if not loadBasicData(in_zip_file, symbol):
            log.error("Error loading data files in this dir: " + in_zip_file)
    print(f'\tLoading Complete: {(time.time() - startTime):.2f}')

    pdStocks = pdStockQuotes.sort_values(by=['time'])
    npStocks = pdStocks.to_numpy()
    del pdStockQuotes

    fields = ["sold", "o_date", "o_time", "o_stock_ask", "o_option_bid", "strike", "expiry", "o_tv", "o_iv",
              "o_theta", "o_dr", "c_date", "c_time", "c_sock_bid", "c_option_ask", "c_tv", "c_iv", "c_theta",
              "c_dr", "net_option", "net_stock", "net", "dur-days"]

    flush_row([ fields ], outfile, write_mode="w", flush_all=True)
    print('\t'.join([x for x in fields]))

    maxStockIndex = len(pdStocks)
    ctr = 0
    rnd = random.randint(20, 40)
    rows = []
    for open_stock in pdStocks.itertuples():
        ctr += 1
        if ctr % rnd != 0: continue  # analyze one per (average) minute.  too much data.
        rnd = random.randint(20, 40)
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
                sold = False
                ctr = 0
                # for close_stock in close_stockPd.itertuples():
                for idx in range (open_stock.Index + 300, maxStockIndex, random.randint(10, 20)):
                    close_stock = StockQuote(npStocks[idx])
                    ctr += 1
                    close_option = pdOptionQuotes_by_timeContractNo.get(str(int(close_stock.time)) + ":" + str(optionDef.con_id), None)
                    net_stock = min(close_stock.bid,optionDef.strike) - open_stock.ask
                    if oexp < close_stock.time:
                        row = ['expired', open_stock.time // 1000000, open_stock.time % 1000000,
                               open_stock.ask, open_option.bid,
                               optionDef.strike, optionDef.expiry, open_tv, open_iv, open_theta,
                               (optionDef.expiry_do - open_stock.time_do).days,
                               close_stock.time // 1000000, close_stock.time % 1000000, close_stock.bid,
                               0, 0, 0, 0, FileUtil.days_between(optionDef.expiry, close_stock.time),
                               round(open_option.bid, 2), round(net_stock, 2), round(net_stock + open_option.bid, 1),
                               (close_stock.time_do - open_stock.time_do).days]
                        rows.append(row)
                        sold = True
                        break

                    if close_option is None: continue
                    if close_option.ask < 0 or close_option.bid < 0: continue
                    net_option = open_option.bid - close_option.ask
                    close_tv, close_iv, close_theta = getComputedComponents(close_stock.time_do, close_stock.bid,
                                                                         close_option.ask, optionDef.strike, optionDef.expiry_do)
                    if ml_model.model_logic.close_position(model_no, close_tv, close_iv, close_theta,
                                                           optionDef.strike, net_stock, net_option):
                        row=['sold', open_stock.time // 1000000, open_stock.time % 1000000,
                             open_stock.ask, open_option.bid,
                             optionDef.strike, optionDef.expiry, round(open_tv,2), round(open_iv,2), round(open_theta,2),
                             (optionDef.expiry_do - open_stock.time_do).days,
                             close_stock.time // 1000000, close_stock.time % 1000000, close_stock.bid, close_option.ask,
                             round(close_tv, 2), round(close_iv, 2), round(close_theta, 2),
                             FileUtil.days_between(optionDef.expiry, close_stock.time),
                             round(net_option, 2), round(net_stock, 2), round(net_stock + net_option, 1),
                             (close_stock.time_do - open_stock.time_do).days]
                        rows.append(row)
                        sold = True
                        break

                if not sold:
                    # print("Not Sold!", last)
                    if close_option is None:
                        row = ['not sold1', open_stock.time // 1000000, open_stock.time % 1000000,
                               open_stock.ask, open_option.bid,
                               optionDef.strike, optionDef.expiry, round(open_tv,2), round(open_iv,2), round(open_theta,2),
                               (optionDef.expiry_do - open_stock.time_do).days,
                               close_stock.time // 1000000, close_stock.time % 1000000, close_stock.bid,
                               0, 0, 0, 0,
                               FileUtil.days_between(optionDef.expiry, close_stock.time),
                               open_option.bid, close_stock.bid - open_stock.ask,
                               round(close_stock.bid - open_stock.ask + open_option.bid,1),
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
                    rows.append(row)

                if ctr % 100 == 0:
                    flush_row(rows, outfile)
                    log.info('\t'.join([str(x) for x in row]))

    print(f"max seen ctr = {ctr}")
    print("last stock", open_stock)
    flush_row(rows, outfile)
    print("\n\n############################################################################")
    print("final results\n")
    res = pd.DataFrame(rows, columns=fields)

    statuses = ['sold', 'expired', 'not sold1', 'no data']
    for status in statuses:
        summaryPD = res.loc[res['sold'] == status]
        summaryStat = summaryPD.groupby('net').agg({
            'o_theta': ['count', 'mean'], 'c_theta': ['mean'],
            'o_tv': ['mean'], 'c_tv': ['mean'],
            'o_iv': ['mean'], 'c_iv': ['mean'],
            'o_dr': ['mean', 'std'], 'c_dr': ['mean'],
            'net_option': ['mean'], 'net_stock': ['mean'],
            'dur-days': ['mean'], 'net': ['mean', 'sum']
            })
        summaryStat.index.name = status
        print(df)

        summary_outfile = outfile.replace(".csv", '_summary.csv')
        if status == "sold":
            with open(summary_outfile, "w") as csvfile:
                csvfile.write("#" + ml_model.model_logic.get_description(model_no) + "\n")
        summaryStat.to_csv(summary_outfile, mode="a")


if __name__ == "__main__":

    config = {}  # parameter config object
    pd.set_option('display.max_columns', None)
    model_no = int(sys.argv[2])
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
        if zip_file[-16:] in ['AAPL20220111.zip']:
            startTime = time.time()
            main(model_no,  file_list[index: index+26], out_dir_m, symbol_m)
            print(f'TIME Main: {(time.time() - startTime):.2f}')
            break

