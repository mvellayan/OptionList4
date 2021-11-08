from datetime import datetime, timedelta, date
import glob, sys
import pandas as pd
from pprint import pprint
import pytz
from utils import FileUtil, IBUtil

optionList: pd.DataFrame = None     # Data Frame all options Contracts for the symbol
stockQuotes: pd.DataFrame = None    # Data Frame all date/time quotes for the symbol
optionQuotes: pd.DataFrame = None   # Data Frame all date/time quotes for all options
symbol: str = ""                 # symbol we are working with.  Param from config
config = {}                      # parameter config object
expiryList = []                 # list of expiry we are interested in for the given date
running_missing = 0
running_total = 0

def main():
    global symbol, config, stockQuotes, optionList, optionQuotes
    global running_missing, running_total

    config = FileUtil.readConfig("config/config-aapl.json")
    loadBasicData("/Users/Muthu/Development/OptionList4/IBdata/2021/11/05")
    stockQuotes.set_index('Time')
    running_missing = 0
    running_total = 0

    print(datetime.now().strftime("%Y%m%d %H:%M:%S"), ": Starting projection building")
    df = stockQuotes.apply(lambda x: expandX(x['Time'], x['Last']), axis=1, result_type='expand')
    df.set_index('Time')

    print(datetime.now().strftime("%Y%m%d %H:%M:%S"), ": Starting Joining")
    projection = stockQuotes.merge(df, on="Time", how="outer")

    print(datetime.now().strftime("%Y%m%d %H:%M:%S"), ": Writing to File")
    projection.to_csv("/Users/Muthu/Development/OptionList4/IBdata/2021/11/05/outfile.csv")

    print(datetime.now().strftime("%Y%m%d %H:%M:%S"), ": Done!")



def expandX(quoteTime, quoteLast):
    global symbol, config, stockQuotes, optionList, optionQuotes
    global running_total, running_missing, expiryList
    list = IBUtil.filterOptionList(expiryList, quoteLast, optionList, strikeBox=3)
    # pprint (list)
    listLabel = ["c_w1_n3", "c_w1_n2", "c_w1_n1", "c_w1_p1", "c_w1_p2", "c_w1_p3",
                 "c_w2_n3", "c_w2_n2", "c_w2_n1", "c_w2_p1", "c_w2_p2", "c_w2_p3",
                 "c_w3_n3", "c_w3_n2", "c_w3_n1", "c_w3_p1", "c_w3_p2", "c_w3_p3"]
    retDict = {}
    index = 0
    retDict["Time"] = quoteTime

    retDict["p0"] = IBUtil.getLast(stockQuotes, quoteTime, 0)
    retDict["p15s"] = IBUtil.getLast(stockQuotes, quoteTime, 15)
    retDict["p30s"] = IBUtil.getLast(stockQuotes, quoteTime, 30)
    retDict["p60s"] = IBUtil.getLast(stockQuotes, quoteTime, 60)
    retDict["p300s"] = IBUtil.getLast(stockQuotes, quoteTime, 300)
    retDict["p600s"] = IBUtil.getLast(stockQuotes, quoteTime, 600)
    retDict["p900s"] = IBUtil.getLast(stockQuotes, quoteTime, 900)

    for contract in list:
        # print(contract)

        qStr = 'ConId == ' + str(contract.conId) + ' and Time == ' + str(quoteTime)
        res = optionQuotes.query(qStr)
        # No Performance diff using eval instead of query.  query is cleaner language
        # qStr = 'optionQuotes.ConId == ' + str(contract.conId) + '& optionQuotes.Time == ' + str(quoteTime)
        # res = pd.eval(' optionQuotes[ ' + qStr + ' ]')

        running_total += 1
        if res.shape[0] > 0:
            dct = res.head(1).to_dict(orient="records")[0];
            # print(dct)
            retDict[listLabel[index] + "_" + "Ask"] = dct["Ask"]
            retDict[listLabel[index] + "_" + "AskSize"] = dct["AskSize"]
            retDict[listLabel[index] + "_" + "Bid"] = dct["Bid"]
            retDict[listLabel[index] + "_" + "BidSize"] = dct["BidSize"]
            retDict[listLabel[index] + "_" + "Last"] = dct["Last"]
            retDict[listLabel[index] + "_" + "LastSize"] = dct["LastSize"]
            retDict[listLabel[index] + "_" + "strike"] = contract.strike
            retDict[listLabel[index] + "_" + "strikeDelta"] = quoteLast - contract.strike
            retDict[listLabel[index] + "_" + "impliedVolatility"] = dct["impliedVolatility"]
        else:
            running_missing += 1
            print("\t", "missing=[", running_missing, "] total=[", running_total, ']:', qStr, "Missing")
        index += 1
    # print("----------------")
    return retDict

def loadBasicData(startingDir):
    global symbol, config, stockQuotes, optionList, optionQuotes
    global expiryList
    # 1. get stock symbol
    symbol = config["stock"]  # symbol we are working with.  Param from config

    # 2. Read Each OptionList Files to Panda.
    # TODO get startingDir from parameter?
    filePattern = startingDir + "/" + symbol + "*optionList*csv"
    for file in glob.glob(startingDir + "/" + symbol + "*optionList*csv"):
        optionList = pd.read_csv(file)

    # 3. Read All StockQuotes Files to single Panda
    for file in glob.glob(startingDir + "/" + symbol + "_" + "*csv"):
        curPd = pd.read_csv(file)
        if stockQuotes is None:
            stockQuotes = curPd
        else:
            stockQuotes = stockQuotes.append(curPd, ignore_index=True)

    quoteTime: int = stockQuotes[['Time']].values[0][0]
    quoteTimeStr = str(quoteTime)
    # parse this: 20211105105959
    quoteTimeDate = FileUtil.getDateObj(quoteTimeStr)
    expiryList = IBUtil.getExpiryList(quoteTimeDate, 3)

    # 3. Read All StockQuotes Files to single Panda
    for file in glob.glob(startingDir + "/" + symbol + "2" + "*csv"):
        curPd = pd.read_csv(file)
        if optionQuotes is None:
            optionQuotes = curPd
        else:
            optionQuotes = optionQuotes.append(curPd, ignore_index=True)


if __name__ == "__main__":
    # if len(sys.argv) < 2:
    #     print("\n\nUsage: model_projection_options <directory>\n\n")
    #     sys.exit(0)
    # else:
    #     print("using config file [" + sys.argv[1] + "]")
    pd.set_option('display.max_columns', None)
    main()
