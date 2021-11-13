from datetime import datetime, timedelta, date
import glob, sys, os
import pandas as pd
from pprint import pprint
import pytz
from timeit import default_timer as timer
from datetime import timedelta

from utils import FileUtil, IBUtil

pdOptionList: pd.DataFrame = None     # Data Frame all options Contracts for the symbol
pdStockQuotes: pd.DataFrame = None    # Data Frame all date/time quotes for the symbol
pdOptionQuotes: pd.DataFrame = None   # Data Frame all date/time quotes for all options
pdOptionQuotesIdx = { }
config = {}                      # parameter config object
expiryList = []                 # list of expiry we are interested in for the given date
running_missing = 0
running_total = 0
total_lookup = 0

def buildIndex(index_col, quoteTime, conId):
    pdOptionQuotesIdx[str(conId) + ":" + str(quoteTime)] = index_col
    #print("Loading- " + str(conId) + ":" + str(quoteTime) + " => " + str(index_col))


def expandX(quoteTime, conId, quoteLast):
    global config, pdStockQuotes, pdOptionList, pdOptionQuotes
    global running_total, running_missing, total_lookup, expiryList
    contractList = IBUtil.filterOptionList(expiryList, quoteLast, pdOptionList, strikeBox=3)
    # pprint (list)
    listLabel = ["c_w1_n3", "c_w1_n2", "c_w1_n1", "c_w1_p1", "c_w1_p2", "c_w1_p3",
                 "c_w2_n3", "c_w2_n2", "c_w2_n1", "c_w2_p1", "c_w2_p2", "c_w2_p3",
                 "c_w3_n3", "c_w3_n2", "c_w3_n1", "c_w3_p1", "c_w3_p2", "c_w3_p3"]
    retDict = {}
    index = 0
    retDict["Time"] = quoteTime

    retDict["p0"] = IBUtil.getLast(pdStockQuotes, quoteTime, 0)
    retDict["p15s"] = IBUtil.getLast(pdStockQuotes, quoteTime, 15)
    retDict["p30s"] = IBUtil.getLast(pdStockQuotes, quoteTime, 30)
    retDict["p60s"] = IBUtil.getLast(pdStockQuotes, quoteTime, 60)
    retDict["p300s"] = IBUtil.getLast(pdStockQuotes, quoteTime, 300)
    retDict["p600s"] = IBUtil.getLast(pdStockQuotes, quoteTime, 600)
    retDict["p900s"] = IBUtil.getLast(pdStockQuotes, quoteTime, 900)

    for contract in contractList:
        running_total += 1
        # apprach 2
        idx = pdOptionQuotesIdx.get(str(contract.conId) + ":" + str(quoteTime))
        # print("<<<<<<<<- " + str(conId) + ":" + str(quoteTime) + " => " + str(idx))

        if idx is None:
            running_missing += 1
            if running_missing % 5000 == 0:
                print("\t", "missing=[", running_missing, round(running_missing/total_lookup, 4), "% ] total=[",
                      running_total, "/", total_lookup, round(running_total/total_lookup, 4), '% ]:',
                      str(conId) + ":" + str(quoteTime), "Missing")
        else:
            # print ( idx, pdOptionQuotes.shape )
            res = pdOptionQuotes.loc[ idx]
            retDict[listLabel[index] + "_" + "Ask"] = res["Ask"]
            retDict[listLabel[index] + "_" + "AskSize"] = res["AskSize"]
            retDict[listLabel[index] + "_" + "Bid"] = res["Bid"]
            retDict[listLabel[index] + "_" + "BidSize"] = res["BidSize"]
            retDict[listLabel[index] + "_" + "Last"] = res["Last"]
            retDict[listLabel[index] + "_" + "LastSize"] = res["LastSize"]
            retDict[listLabel[index] + "_" + "strike"] = contract.strike
            retDict[listLabel[index] + "_" + "strikeDelta"] = quoteLast - contract.strike
            retDict[listLabel[index] + "_" + "impliedVolatility"] = res["impliedVolatility"]
        index += 1

    return retDict


def loadBasicData(startingDir):
    global config, pdStockQuotes, pdOptionList, pdOptionQuotes
    global expiryList
    # 1. get stock symbol
    symbol = config["stock"]

    # 2. Read Each OptionList Files to Panda.
    filePattern = startingDir + "/" + symbol + "*optionList*csv"
    for file in glob.glob(startingDir + "/" + symbol + "*optionList*csv"):
        pdOptionList = pd.read_csv(file)

    # 3. Read All StockQuotes Files to single Panda
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
        print ("No files in the directory?? " + startingDir + "/" + symbol + "_" + "*csv")
        return False
    else:
        print("Found [", pdStockQuotes.shape, "] stocks rows.")

    #print(pdStockQuotes[['Time']].values[0][0])
    quoteTime: int = pdStockQuotes[['Time']].values[0][0]
    quoteTimeStr = str(quoteTime)
    # parse this: 20211105105959
    quoteTimeDate = FileUtil.getDateObj(quoteTimeStr)
    expiryList = IBUtil.getExpiryList(quoteTimeDate, 3)

    # 3. Read All OptionsQuotes Files to single Panda
    for file in glob.glob(startingDir + "/" + symbol + "2" + "*csv"):
        curPd = pd.read_csv(file)
        # Store only 9:25 to 16:10 data for quotes
        curPd = curPd[(curPd['Time'] % 1000000).between(92500, 161000)]
        if pdOptionQuotes is None:
            pdOptionQuotes = curPd
        else:
            pdOptionQuotes = pdOptionQuotes.append(curPd, ignore_index=True)

    return True


def main(dirName):
    global pdStockQuotes, pdOptionList, pdOptionQuotes
    global running_missing, running_total, total_lookup

    if not loadBasicData(dirName):
        print("Cant find data in this dir: ", dirName)
        return

    running_total = running_missing = 0
    total_lookup = len(pdStockQuotes) * 18

    # perform index
    # for index, row in pdOptionQuotes.iterrows():
    pdOptionQuotes['index_col'] = pdOptionQuotes.index
    # print(pdOptionQuotes[['index_col', 'ConId', 'Time']])
    pdOptionQuotes.apply(lambda y: buildIndex( y['index_col'], y['Time'], y['ConId']), axis=1, result_type='expand')

    # Section
    start = timer()
    # print(datetime.now().strftime("%Y%m%d %H:%M:%S"), ": Starting projection building")
    df = pdStockQuotes.apply(lambda x: expandX(x['Time'], x['ConId'], x['Last']), axis=1, result_type='expand')
    df.set_index('Time')
    end = timer()
    print("TIME: Projecting: ",  timedelta(seconds=end - start))

    # Section
    print(datetime.now().strftime("%Y%m%d %H:%M:%S"), ": Starting Joining")
    projection = pdStockQuotes.merge(df, on="Time", how="outer")

    print(datetime.now().strftime("%Y%m%d %H:%M:%S"), ": Writing to File")
    projection.to_csv(dirName + "/projection_stock_call_options.csv")

    print(datetime.now().strftime("%Y%m%d %H:%M:%S"), ": Done!")


if __name__ == "__main__":
    pd.set_option('display.max_columns', None)
    if len(sys.argv) < 2:
        print("\n\nUsage: project.py <config_file.yml>\n\n")
        sys.exit(0)
    else:
        print("using config file [" + sys.argv[1] + "]")

    config = FileUtil.readConfig(sys.argv[1])
    for dir in os.walk("IBdata/"):
        for files in dir[2]:
            if config["stock"] + 'optionList' in files:
                print ("In main loop.  Found/Processing directory: ", dir[0])
                main(dir[0])
                break
                print("Stopping for debugging.  Dir:", dir[2])
