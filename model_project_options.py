import shutil
from datetime import datetime, timedelta, date
import glob, sys, os
import pandas as pd
from pprint import pprint
import pytz
from timeit import default_timer as timer
from datetime import timedelta

from utils import FileUtil, IBUtil
from utils.FileUtil import p, makeDirectory, unzip_file, get_sec_to_expire

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
    retDict["Time"] = quoteTime
    quoteDateObj = FileUtil.getDateObjFromStr(quoteTime)
    retDict["p0"] = FileUtil.get_quote_with_delta(pdStockQuotes, quoteDateObj, 0)
    retDict["p15s"] = FileUtil.get_quote_with_delta(pdStockQuotes, quoteDateObj, 15)
    retDict["p30s"] = FileUtil.get_quote_with_delta(pdStockQuotes, quoteDateObj, 30)
    retDict["p60s"] = FileUtil.get_quote_with_delta(pdStockQuotes, quoteDateObj, 60)
    retDict["p300s"] = FileUtil.get_quote_with_delta(pdStockQuotes, quoteDateObj, 300)
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
            tv = ((res["Ask"] + res["Bid"])/2) - (quoteLast - contract.strike)
            dur = get_sec_to_expire(
                FileUtil.getDateObjFromStr(quoteTime),
                FileUtil.getDateObjFromStr(contract.lastTradeDateOrContractMonth,'YYYYMMDD'))
            theta = (tv / dur) * 100 * 1000 # 100 = cents, 100 = basis point
            retDict[listLabel[index] + "_" + "Ask"] = res["Ask"]
            retDict[listLabel[index] + "_" + "AskSize"] = res["AskSize"]
            retDict[listLabel[index] + "_" + "Bid"] = res["Bid"]
            retDict[listLabel[index] + "_" + "BidSize"] = res["BidSize"]
            retDict[listLabel[index] + "_" + "Last"] = res["Last"]
            retDict[listLabel[index] + "_" + "LastSize"] = res["LastSize"]
            retDict[listLabel[index] + "_" + "strike"] = contract.strike
            retDict[listLabel[index] + "_" + "strikeDelta"] = quoteLast - contract.strike
            retDict[listLabel[index] + "_" + "timeValue"] = tv
            retDict[listLabel[index] + "_" + "theta"] = theta
            retDict[listLabel[index] + "_" + "impliedVolatility"] = res["impliedVolatility"]
        index += 1

    return retDict

def loadBasicData(startingDir):
    global config, pdStockQuotes, pdOptionList, pdOptionList3wC, pdOptionQuotesIdx, expiryList
    symbol = config["stock"]
    zipFilename = startingDir + "/" + symbol + ".zip"
    startingDirOrig = startingDir
    createdTmpDir = False

    # 1 is there is a zip file?  If so unzip & use tmp dir
    if os.path.exists(zipFilename):
        createdTmpDir = True
        startingDir = startingDir + "/" + FileUtil.getDateTimeStamp(1)
        os.makedirs(startingDir, exist_ok=True)
        unzip_file(startingDir, zipFilename)

    # 2. Load pdStockQuotes -- Stock Quotes
    for file in glob.glob(startingDir + "/" + symbol + "_" + "*csv"):
        curPd = pd.read_csv(file)
        # Store only 9:25 to 16:10 data for quotes
        curPd = curPd[(curPd['Time'] % 1000000).between(92500, 161000)]
        if pdStockQuotes is None:
            pdStockQuotes = curPd
        else:
            pdStockQuotes = pdStockQuotes.append(curPd, ignore_index=True)

    # No files in the directory
    if pdStockQuotes is None:
        p("No files in the directory?? " + startingDir + "/" + symbol + "_" + "*csv")
        return False
    else:
        p("Found [", pdStockQuotes.shape, "] stocks rows.")

    # 3. Load variable : expiryList
    expiryList = IBUtil.get_expiry_list(pdStockQuotes[['Time']].values[0][0], 3)

    # 4. Load pdOptionList -- options List
    for file in glob.glob(startingDir + "/" + symbol + "*optionList*csv"):
        pdOptionList = pd.read_csv(file)

    # 4.b load pdOptionList3wC
    # filtering now for performance improvement.
    pdOptionList3wC = pdOptionList[pdOptionList['right'] == 'C']
    pdOptionList3wC = pdOptionList3wC[pdOptionList3wC['lastTradeDateOrContractMonth'] <= expiryList[-1]]

    # 5. Load pdOptionQuotesIdx -- Options Quotes
    for file in glob.glob(startingDir + "/" + symbol + "2" + "*csv"):
        curPd = pd.read_csv(file)
        # Store only 9:25 to 16:10 data for quotes
        curPd = curPd[(curPd['Time'] % 1000000).between(92500, 161000)]
        for index, row in curPd.iterrows():
            hash_idx = str(row.ConId) + ":" + str(row.Time)
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
        # 6b. loose files, zip it up
        FileUtil.zip_and_delete(startingDir, config["stock"])

    # 7. Done!!
    return True


def main(dirName):
    global pdStockQuotes, pdOptionList, pdOptionQuotesIdx
    global running_missing, running_total, total_lookup

    if not loadBasicData(dirName):
        p("Cant find data in this dir: ", dirName)
        return

    running_total = running_missing = 0
    total_lookup = len(pdStockQuotes) * 18

    # Section
    start = timer()
    pdStockQuotes = pdStockQuotes.head(1000)
    df = pdStockQuotes.apply(lambda x: expandX(x['Time'], x['ConId'], x['Last']), axis=1, result_type='expand')

    df.set_index('Time')
    end = timer()
    p("TIME: Projecting: ",  timedelta(seconds=end - start))

    # Section
    p(" Starting Joining")
    projection = pdStockQuotes.merge(df, on="Time", how="outer")

    outfile = dirName + "/projection_stock_call_options_" + config["stock"] + ".csv"
    p(" Writing to File [", outfile, "]")
    projection.to_csv(outfile, float_format='%.6f')

    p("Done!")


if __name__ == "__main__":
    pd.set_option('display.max_columns', None)
    if len(sys.argv) < 2:
        p("\n\nUsage: project.py <config_file.yml>\n\n")
        sys.exit(0)
    else:
        p("using config file [" + sys.argv[1] + "]")

    config = FileUtil.readConfig(sys.argv[1])

    main("/Users/Muthu/Development/OptionList4/IBdata/2021/11/18")
    # for directory in os.walk("IBdata/"):
    #     for files in directory[2]:
    #         if config["stock"] + 'optionList' in files:
    #             p("In main loop.  Found/Processing directory: ", directory[0])
    #             main(directory[0])
