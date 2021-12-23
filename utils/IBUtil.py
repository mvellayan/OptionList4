import logging
import math
import os

import numpy
import pytz
from datetime import datetime, timedelta

import pandas as pd
from ib_insync import *

from utils import FileUtil
from utils.FileUtil import makeDataFileName

log = logging.getLogger("myLogger")

def pull_options_list(ib, config, fileName):

    # contract.conId = sec["ConId"]
    l_contract = Contract(symbol=config["stock"], secType="OPT", exchange="SMART",
                          currency="USD")

    contractList = ib.reqContractDetails(l_contract)
    df = pd.DataFrame(columns=['con_id', 'symbol', 'expiry', 'strike', 'right'])
    df.set_index('con_id')

    # move contractList to panda so we can easily write it to a csv file
    for obj in contractList:
        c = obj.contract
        df.loc[len(df)] = [c.conId, c.localSymbol, c.lastTradeDateOrContractMonth,
                           c.strike, c.right]

    # if file exists, move it
    if os.path.exists(fileName):
        logging.info("File already exists [" + fileName + "]")
        newFileName = fileName + "_" + datetime.now().strftime("%H%M%S")
        logging.info("Moving it to timestamp file: " + newFileName)
        os.rename(fileName, newFileName)

    df.to_csv(fileName, index=False)
    log.info("Option Contracts written to file [" + fileName + "]")


def get_filtered_contract_list(ib, config, quoteAmt: float = 0.0, force_pull=False): # -> "[] of stock and option contracts to pull"
    retArray = []  #array of contracts

    stk = Contract(symbol=config["stock"], secType="STK", exchange="SMART",
                   conId=config["stockContractId"], currency="USD")
    retArray.append(stk)

    fileName = get_options_list_file_name(config)
    if (not os.path.exists(fileName)) or force_pull:
        log.info("Creating new file: [" + fileName + "]")
        pull_options_list(ib, config, fileName)
    else:
        log.info("OptionsList file found.  Using [" + fileName + "]")
    optionList = pd.read_csv(fileName)

    #get last price
    #self, reqId, contract, genericTickList, snapshot, regulatorySnapshot, mktDataOptions):
    if quoteAmt == 0:
        data = ib.reqMktData(contract=stk, snapshot=True)
        ctr = 0
        while data.last != data.last and ctr < 100:
            ib.sleep(0.01)  # Wait until data is in.
            ctr += 1
        quoteAmt = data.last
        log.info("Using last quote:")
        assert quoteAmt > 0, "Expecting quote > 0"
    log.info(quoteAmt)

    # expiryList, quoteLast, optionList, strikeBox=3)
    expiryList = get_expiry_list(datetime.now(), config["weeksOut"], optionList)
    retArray += filter_option_list(expiryList, quoteAmt, optionList, config["strikeBox"])
    return retArray


filter_option_list_cache = {}
def filter_option_list(expiryList, quoteAmt: float, df, strikeBox: int):
    global filter_option_list_cache

    cache_value = filter_option_list_cache.get(quoteAmt, None)
    if cache_value is not None:
        return cache_value

    retArray = []
    df_res = None

    #Filter by type.  Calls only
    df = df[df['right'] == 'C']
    df['strikeDelta'] = df['strike'] - quoteAmt
    df['absStrikeDelta'] = abs(df['strikeDelta'])

    #filter by expiration date
    for i, exp in enumerate(expiryList):
        # df_exp[i] = df[df['expiry'] == exp]
        df_week = df[df['expiry'] == exp]

        df_pos = df_week[df_week['strikeDelta'] >= 0]
        df_w = df_pos.sort_values(['strikeDelta'], ascending=True).head(strikeBox)
        if df_res is None:
            df_res = df_w
        else:
            df_res = df_res.append(df_w)

        df_neg = df_week[df_week['strikeDelta'] < 0]
        df_w = df_neg.sort_values(['strikeDelta'], ascending=False).head(strikeBox)
        df_res = df_res.append(df_w)

    # p(df_res.describe())

    # p('\n\n--------------------- Strike (', quoteAmt, ')---------------')
    df_res = df_res.sort_values(by=['expiry', 'strike'], ascending=True)
    for ind in df_res.index:
        # p(df_res["conId"][ind], df_res["strike"][ind],
        #      df_res["lastTradeDateOrContractMonth"][ind], df_res["localSymbol"][ind])
        retArray.append(Contract(conId=df_res["con_id"][ind],  secType="OPT", exchange="SMART",
                                 currency="USD", right=df_res["right"][ind], symbol=df_res["symbol"][ind],
                                 strike=df_res["strike"][ind], lastTradeDateOrContractMonth =
                                 df_res["expiry"][ind]))
    # p('\n Summary: Above Strike (', df_res.shape, ') \n')

    filter_option_list_cache[quoteAmt] = retArray
    assert len(retArray) == 18, "should be tracking 18 options. =( " + len(retArray) + ")"
    return retArray


def is_trading_hours(now=datetime.now()):
    hour = int(now.astimezone(pytz.timezone('US/Eastern')).strftime("%H"))
    day_of_week = now.weekday()
    if hour in range(9, 17) and day_of_week in range(0, 5): # checking hours and trading date
        return True
    else:
        log.info("Non-trading hour.[" + str (hour) +  "] Can't get realtime data. ")
        log.info(now)
        return False


def get_options_list_file_name(config, dateStr=""):
    if dateStr == "":
        dateStr = datetime.now().astimezone(pytz.timezone('US/Eastern')).strftime("%Y%m%d")
    return makeDataFileName("ol_" + config["stock"] + "_" + dateStr, False)


class MarketData:
    def __init__(self, ticker):
        self.conId = ticker.contract.conId
        self.symbol = ticker.contract.symbol + ""
        self.quoteTime = ticker.time
        self.bid = ticker.bid
        self.bidSize = ticker.bidSize
        self.ask = ticker.ask
        self.askSize = ticker.askSize
        self.last = ticker.last
        self.lastSize = ticker.lastSize
        self.volume = ticker.volume

        if math.isnan(ticker.histVolatility):
            self.histVolatility = ""
        else:
            self.histVolatility = ticker.histVolatility
        if math.isnan(ticker.impliedVolatility):
            self.impliedVolatility = ""
        else:
            self.impliedVolatility = ticker.impliedVolatility


def get_expiry_list(quoteTimeDate, noWeeks: int, pdOptionList):

    expiryListArr = []
    expiry = pdOptionList['expiry'].unique()
    expiry.sort()
    for dts in expiry:
        if dts >= (quoteTimeDate/1000000):
            expiryListArr.append(dts)
        if len(expiryListArr) >= 3:
            break

    assert expiryListArr[0] >= (quoteTimeDate/1000000), "Expiry of option 0st >= quote date "
    assert expiryListArr[1] >= expiryListArr[0], "Expiry of option 1st >= expiry of option 0"
    assert expiryListArr[2] >= expiryListArr[1], "Expiry of option 2st >= expiry of option 1"
    return expiryListArr

    # Old way... should not find 3 fridays in a row.. some are not work days!!!
    if type(quoteTimeDate) == numpy.int64:
        quoteTime: int = quoteTimeDate
        quoteTimeStr = str(quoteTime)
        # parse this: 20211105105959
        quoteTimeDate = FileUtil.getDateObjFromStr(quoteTimeStr)
    elif type(quoteTimeDate) == datetime:
        pass
    else:
        log.info("Unexpected data type for quoteTime: ")
        log.info(type(quoteTimeDate))
        sys.exit(1)

    wDate = quoteTimeDate
    for i in range(noWeeks):
        wDate = wDate + timedelta((4 - wDate.weekday()) % 7)
        expiryListArr.append(int(wDate.strftime("%Y%m%d")))
        wDate = wDate + timedelta(days=1)
    return expiryListArr


if __name__ == "__main__":
    log.info( is_trading_hours())

