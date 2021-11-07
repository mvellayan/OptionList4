import datetime
from datetime import timedelta, date
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


def main():
    global symbol, config, stockQuotes, optionList, optionQuotes

    config = FileUtil.readConfig("config/config-aapl.json")
    loadBasicData("/Users/Muthu/Development/OptionList4/IBdata/2021/11/05")
    stockQuotes.set_index('Time')

    print(datetime.now().strftime("%Y%m%d %H:%M:%S"), ": Starting projection building")
    df = stockQuotes.apply(lambda x: expandX(x['Time'], x['Last']), axis=1, result_type='expand')
    df.set_index('Time')

    print(datetime.now().strftime("%Y%m%d %H:%M:%S"), ": Starting Joining")
    projection = stockQuotes.merge(df, on="Time", how="outer")

    print(datetime.now().strftime("%Y%m%d %H:%M:%S"), ": Writing to File")
    projection.to_csv("/Users/Muthu/Development/OptionList4/IBdata/2021/11/05/outfile.csv")

    print(datetime.now().strftime("%Y%m%d %H:%M:%S"), ": Done!")


'''
    df[[
        'c_w1_n1_Ask', 'c_w1_n1_AskSize', 'c_w1_n1_Bid', 'c_w1_n1_BidSize', 'c_w1_n1_Last', 'c_w1_n1_LastSize',
        'c_w1_n1_impliedVolatility', 'c_w1_n1_strike', 'c_w1_n1_strikeDelta', 'c_w1_n2_Ask', 'c_w1_n2_AskSize',
        'c_w1_n2_Bid', 'c_w1_n2_BidSize', 'c_w1_n2_Last', 'c_w1_n2_LastSize', 'c_w1_n2_impliedVolatility',
        'c_w1_n2_strike', 'c_w1_n2_strikeDelta', 'c_w1_n3_Ask', 'c_w1_n3_AskSize', 'c_w1_n3_Bid', 'c_w1_n3_BidSize',
        'c_w1_n3_Last', 'c_w1_n3_LastSize', 'c_w1_n3_impliedVolatility', 'c_w1_n3_strike', 'c_w1_n3_strikeDelta',
        'c_w1_p1_Ask', 'c_w1_p1_AskSize', 'c_w1_p1_Bid', 'c_w1_p1_BidSize', 'c_w1_p1_Last', 'c_w1_p1_LastSize',
        'c_w1_p1_impliedVolatility', 'c_w1_p1_strike', 'c_w1_p1_strikeDelta', 'c_w1_p2_Ask', 'c_w1_p2_AskSize',
        'c_w1_p2_Bid', 'c_w1_p2_BidSize', 'c_w1_p2_Last', 'c_w1_p2_LastSize', 'c_w1_p2_impliedVolatility', 'c_w1_p2_strike',
        'c_w1_p2_strikeDelta', 'c_w1_p3_Ask', 'c_w1_p3_AskSize', 'c_w1_p3_Bid', 'c_w1_p3_BidSize', 'c_w1_p3_Last',
        'c_w1_p3_LastSize', 'c_w1_p3_impliedVolatility', 'c_w1_p3_strike', 'c_w1_p3_strikeDelta', 'c_w2_n1_Ask',
        'c_w2_n1_AskSize', 'c_w2_n1_Bid', 'c_w2_n1_BidSize', 'c_w2_n1_Last', 'c_w2_n1_LastSize',
        'c_w2_n1_impliedVolatility', 'c_w2_n1_strike', 'c_w2_n1_strikeDelta', 'c_w2_n2_Ask', 'c_w2_n2_AskSize',
        'c_w2_n2_Bid', 'c_w2_n2_BidSize', 'c_w2_n2_Last', 'c_w2_n2_LastSize', 'c_w2_n2_impliedVolatility', 'c_w2_n2_strike',
        'c_w2_n2_strikeDelta', 'c_w2_n3_Ask', 'c_w2_n3_AskSize', 'c_w2_n3_Bid', 'c_w2_n3_BidSize', 'c_w2_n3_Last',
        'c_w2_n3_LastSize', 'c_w2_n3_impliedVolatility', 'c_w2_n3_strike', 'c_w2_n3_strikeDelta', 'c_w2_p1_Ask',
        'c_w2_p1_AskSize', 'c_w2_p1_Bid', 'c_w2_p1_BidSize', 'c_w2_p1_Last', 'c_w2_p1_LastSize',
        'c_w2_p1_impliedVolatility', 'c_w2_p1_strike', 'c_w2_p1_strikeDelta', 'c_w2_p2_Ask', 'c_w2_p2_AskSize',
        'c_w2_p2_Bid', 'c_w2_p2_BidSize', 'c_w2_p2_Last', 'c_w2_p2_LastSize', 'c_w2_p2_impliedVolatility', 'c_w2_p2_strike',
        'c_w2_p2_strikeDelta', 'c_w2_p3_Ask', 'c_w2_p3_AskSize', 'c_w2_p3_Bid', 'c_w2_p3_BidSize', 'c_w2_p3_Last',
        'c_w2_p3_LastSize', 'c_w2_p3_impliedVolatility', 'c_w2_p3_strike', 'c_w2_p3_strikeDelta', 'c_w3_n1_Ask',
        'c_w3_n1_AskSize', 'c_w3_n1_Bid', 'c_w3_n1_BidSize', 'c_w3_n1_Last', 'c_w3_n1_LastSize',
        'c_w3_n1_impliedVolatility', 'c_w3_n1_strike', 'c_w3_n1_strikeDelta', 'c_w3_n2_Ask', 'c_w3_n2_AskSize',
        'c_w3_n2_Bid', 'c_w3_n2_BidSize', 'c_w3_n2_Last', 'c_w3_n2_LastSize', 'c_w3_n2_impliedVolatility', 'c_w3_n2_strike',
        'c_w3_n2_strikeDelta', 'c_w3_n3_Ask', 'c_w3_n3_AskSize', 'c_w3_n3_Bid', 'c_w3_n3_BidSize', 'c_w3_n3_Last',
        'c_w3_n3_LastSize', 'c_w3_n3_impliedVolatility', 'c_w3_n3_strike', 'c_w3_n3_strikeDelta', 'c_w3_p1_Ask',
        'c_w3_p1_AskSize', 'c_w3_p1_Bid', 'c_w3_p1_BidSize', 'c_w3_p1_Last', 'c_w3_p1_LastSize',
        'c_w3_p1_impliedVolatility', 'c_w3_p1_strike', 'c_w3_p1_strikeDelta', 'c_w3_p2_Ask', 'c_w3_p2_AskSize',
        'c_w3_p2_Bid', 'c_w3_p2_BidSize', 'c_w3_p2_Last', 'c_w3_p2_LastSize', 'c_w3_p2_impliedVolatility', 'c_w3_p2_strike',
        'c_w3_p2_strikeDelta', 'c_w3_p3_Ask', 'c_w3_p3_AskSize', 'c_w3_p3_Bid', 'c_w3_p3_BidSize', 'c_w3_p3_Last',
        'c_w3_p3_LastSize', 'c_w3_p3_impliedVolatility', 'c_w3_p3_strike', 'c_w3_p3_strikeDelta']] = \
        df.apply(lambda x: expandX(x['Time'], x['Last']), axis=1)
    print(df)
'''

def expandX(quoteTime, quoteLast):
    global symbol, config, stockQuotes, optionList, optionQuotes

    list = IBUtil.filterOptionList(expiryList, quoteLast, optionList, strikeBox=3)
    # pprint (list)
    listLabel = ["c_w1_n3", "c_w1_n2", "c_w1_n1", "c_w1_p1", "c_w1_p2", "c_w1_p3",
                 "c_w2_n3", "c_w2_n2", "c_w2_n1", "c_w2_p1", "c_w2_p2", "c_w2_p3",
                 "c_w3_n3", "c_w3_n2", "c_w3_n1", "c_w3_p1", "c_w3_p2", "c_w3_p3"]
    retDict = {}

    index = 0
    retDict["Time"] = quoteTime
    for contract in list:
        # print(contract)
        qStr = 'ConId == ' + str(contract.conId) + ' and Time == ' + str(quoteTime)
        res = optionQuotes.query(qStr)
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
        index += 1
    # print("----------------")
    return retDict

def loadBasicData(startingDir):
    global symbol, config, stockQuotes, optionList, optionQuotes

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
    quoteTimeDate = datetime.datetime(int(quoteTimeStr[0:4]), int(quoteTimeStr[4:6]), int(quoteTimeStr[6:8]),
                                         int(quoteTimeStr[8:10]), int(quoteTimeStr[10:12]), int(quoteTimeStr[12:14]))
    wDate = quoteTimeDate
    for i in range(3):
        wDate = wDate + datetime.timedelta((4 - wDate.weekday()) % 7)
        expiryList.append(int(wDate.strftime("%Y%m%d")))
        wDate = wDate + timedelta(days=1)

   # print('time [', quoteTime, quoteTimeStr, quoteTimeDate, "]", expiryList)


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
