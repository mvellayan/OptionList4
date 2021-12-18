import argparse
import logging
import shutil
from datetime import datetime, timedelta, date
import glob, sys, os
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
pdOptionList3wC: pd.DataFrame = None     # 3 week calls only
pdStockQuotes: pd.DataFrame = None    # Data Frame all date/time quotes for the symbol
pdOptionQuotesIdx = {}
config = {}                      # parameter config object
expiryList = []                 # list of expiry we are interested in for the given date
running_missing = 0
running_total = 0
total_lookup = 0


def expandX(quoteTime, conId, quoteLast):
    global config, pdStockQuotes, pdOptionList, pdOptionList3wC, pdOptionQuotesIdx
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
    retDict["p15s"] = FileUtil.get_quote_with_delta(pdStockQuotes, quoteDateObj, 15)
    retDict["p30s"] = FileUtil.get_quote_with_delta(pdStockQuotes, quoteDateObj, 30)
    retDict["p60s"] = FileUtil.get_quote_with_delta(pdStockQuotes, quoteDateObj, 60)
    if retDict["p60s"]:
        retDict["p60s_delta"] = (retDict["p60s"] - retDict["p0"])
    retDict["p300s"] = FileUtil.get_quote_with_delta(pdStockQuotes, quoteDateObj, 300)
    if retDict["p300s"]:
        retDict["p300s_delta"] = (retDict["p300s"] - retDict["p0"])
    retDict["p600s"] = FileUtil.get_quote_with_delta(pdStockQuotes, quoteDateObj, 600)
    retDict["p900s"] = FileUtil.get_quote_with_delta(pdStockQuotes, quoteDateObj, 900)

    for contract in contractList:
        running_total += 1
        # approach 2
        ### print (contract)
        ### hash_idx = str(row.ConId) + ":" + str(row.Time)
        ### print(index, '->', row, '==>', hash_idx)

        idx = pdOptionQuotesIdx.get(str(contract.conId) + ":" + str(quoteTime))
        # print("<<<<<<<<- " + str(conId) + ":" + str(quoteTime) + " => " + str(idx))

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
                FileUtil.getDateObjFromStr(contract.lastTradeDateOrContractMonth,'YYYYMMDD'))
            if dur == 0 or tv == 0:
                theta =  0
            else:
                theta = (tv / dur) * 100 * 1000 # 100 = cents, 100 = basis point
            # retDict[listLabel[index] + "_" + "symbol"] = res["symbol"]
            retDict[listLabel[index] + "_" + "bid_ask_delta"] = res["bid"] - res["ask"]
            # retDict[listLabel[index] + "_" + "ask"] = res["ask"]
            retDict[listLabel[index] + "_" + "ask_size"] = res["ask_size"]
            # retDict[listLabel[index] + "_" + "bid"] = res["bid"]
            retDict[listLabel[index] + "_" + "bid_size"] = res["bid_size"]
            # retDict[listLabel[index] + "_" + "last"] = res["last"]
            retDict[listLabel[index] + "_" + "last_size"] = res["last_size"]
            # retDict[listLabel[index] + "_" + "strike"] = contract.strike
            if index == 0:
                retDict[listLabel[index] + "_" + "strike_delta"] = quoteLast - contract.strike
            # retDict[listLabel[index] + "_" + "time_value"] = tv
            retDict[listLabel[index] + "_" + "theta"] = theta
            # retDict[listLabel[index] + "_" + "implied_volatility"] = res["implied_volatility"]
        index += 1

    return retDict

def loadBasicData(startingDir):
    global config, pdStockQuotes, pdOptionList, pdOptionList3wC, pdOptionQuotesIdx, expiryList
    symbol = config["stock"]
    zipFilename = startingDir + "/" + symbol + getDateStrFromPath(startingDir) + ".zip"
    startingDirOrig = startingDir
    createdTmpDir = False

    # 1 is there is a zip file?  If so unzip & use tmp dir
    if os.path.exists(zipFilename):
        createdTmpDir = True
        startingDir = startingDir + "/" + FileUtil.getDateTimeStamp(1)
        os.makedirs(startingDir, exist_ok=True)
        unzip_file(startingDir, zipFilename)

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

    # 3. Load variable : expiryList
    expiryList = IBUtil.get_expiry_list(pdStockQuotes[['time']].values[0][0], 3)

    # 4. Load pdOptionList -- options List
    for file in glob.glob(startingDir + "/ol_" + symbol + "*csv"):
        pdOptionList = pd.read_csv(file)

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
        # 6a. For zip file delete temp dir
        try:
            shutil.rmtree(startingDir)
        except OSError as e:
            print("Error: %s : %s" % (startingDir, e.strerror))
    else:
        # 6b. loose files, zip it up  oq_FB211203C00305000_20211201.csv
        FileUtil.zip_and_delete(directory=startingDir, stock_symbol_in_file_name=config["stock"],
                                file_prefix_tuple=('sq_', 'oq_', 'ol_'), zip_file_name=zipFilename)

    # 7. Done!!
    return True


def main(scan_data_dir):
    global pdStockQuotes, pdOptionList, pdOptionQuotesIdx
    global running_missing, running_total, total_lookup, config

    outfile = out_dir + "ml_cp18_" + config["stock"] + getDateStrFromPath(scan_data_dir) + ".csv"
    print(f"\nProcessing {scan_data_dir} => {outfile}")
    if os.path.exists(outfile):
        print(f"\tAssessment File Exist, skipping directory: {outfile}")
        return

    if not loadBasicData(scan_data_dir):
        log.error("Cant find data in this dir: " + scan_data_dir)
        return

    running_total = running_missing = 0
    total_lookup = len(pdStockQuotes) * 18

    # TODO remove this line
    # pdStockQuotes = pdStockQuotes.head(10000)
    # Section
    df = pdStockQuotes.apply(lambda x: expandX(x['time'], x['con_id'], x['last']), axis=1, result_type='expand')

    #pprint(pdStockQuotes.columns)
    #pprint(df.columns)
    #df.set_index('time')

    pdStockQuotes.drop(axis=1, columns=['con_id', 'symbol', 'bid', 'ask', 'last', 'hist_volatility', 'implied_volatility'],
                       inplace=True)
    df.drop(axis=1, columns=['p0', 'p15s', 'p30s', 'p60s', 'p300s', 'p600s', 'p900s'], inplace=True)

    projection = pdStockQuotes.merge(df, on="time", how="outer")
    # for col in projection.columns: print(f"{ctr}: {col}")

    # projection['p60s_delta_quantile'] = projection.qcut('s' + df['p60s_delta'], 7, labels=False)
    ctr = 0
    labels = []
    for v in projection['p60s_delta'].quantile((1 / 7, 2 / 7, 3 / 7, 4 / 7, 5 / 7, 6 / 7, 1)).tolist():
        labels.append(f"q_{ctr}_{v:.2f}")
        ctr += 1
    projection['p60s_bucket_category'] = pd.qcut(df['p60s_delta'], 7, labels=labels)

    # projection['p300s_delta_quantile'] = projection.qcut('s' + df['p300s_delta'], 7, labels=False)
    ctr = 0
    labels = []
    for v in projection['p300s_delta'].quantile((1 / 7, 2 / 7, 3 / 7, 4 / 7, 5 / 7, 6 / 7, 1)).tolist():
        labels.append(f"q_{ctr}_{v:.2f}")
        ctr += 1
    projection['p300s_bucket_category'] = pd.qcut(df['p300s_delta'], 7, labels=labels)


    projection.drop(axis=1, columns=['time', 'p60s_delta', 'p300s_delta'], inplace=True)
    projection.dropna(axis=0, how='any', inplace=True)
    projection.to_csv(outfile, float_format='%.6f', index=False)
    log.info("Done!")
    sys.exit(1)

def collect_args() -> dict:
    """Collect arguments passed into the script

    Returns:
        dict: Arguments Object
    """
    parser = argparse.ArgumentParser(
        description='Collect per second Realtime Data for a stock + 18 related options')

    parser.add_argument('config', help='JSON file that contains all the configuration',
                        default="config.json", type=str)
    parser.add_argument('scan_dir', help='Data file directory to scan.  Added to current path',
                        default="/IBdata/", type=str)
    parser.add_argument('out_dir', help='Directory write output.  Added to current path',
                        default="/ml_cp18/", type=str)
    retDict = parser.parse_args()

    if not retDict.scan_dir.startswith("/"):
        retDict.scan_dir = "/" + retDict.scan_dir
    if not retDict.scan_dir.endswith("/"):
        retDict.scan_dir = retDict.scan_dir + "/"

    if not retDict.out_dir.startswith("/"):
        retDict.out_dir = "/" + retDict.out_dir
    if not retDict.out_dir.endswith("/"):
        retDict.out_dir = retDict.out_dir + "/"
    pprint(retDict)

    return retDict


if __name__ == "__main__":

    pd.set_option('display.max_columns', None)
    args = collect_args()

    config = FileUtil.readConfig(args.config)
    scan_dir = os.getcwd() + args.scan_dir
    out_dir = os.getcwd() + args.out_dir

    print("Scanning: " + scan_dir)
    for rootdir, dirs, files in os.walk(scan_dir):
        for subdir in dirs:
            full_dir = os.path.join(rootdir, subdir)
            search_mask1 = full_dir + "/ol_" + config["stock"] + '*.csv'
            search_mask2 = full_dir + "/" + config["stock"] + '*.zip'
            if glob.glob(search_mask1) or glob.glob(search_mask2):
                main(full_dir)

