import math
import os
import pytz
from datetime import datetime, timedelta, date

import pandas as pd
from ib_insync import *
from utils.FileUtil import makeDataFileName, p


def pull_options_list(ib, config):

    # contract.conId = sec["ConId"]
    l_contract = Contract(symbol=config["stock"], secType="OPT", exchange="SMART",
                          currency="USD")

    contractList = ib.reqContractDetails(l_contract)
    df = pd.DataFrame(columns=['secType', 'conId', 'symbol', 'lastTradeDateOrContractMonth',
                               'strike', 'right', 'localSymbol'])

    # move contractList to panda so we can easily write it to a csv file
    for obj in contractList:
        c = obj.contract
        df.loc[len(df)] = [c.secType, c.conId, c.symbol, c.lastTradeDateOrContractMonth,
                           c.strike, c.right, c.localSymbol]

    fileName = get_options_list_file_name(config)
    # if file exists, move it
    if os.path.exists(fileName):
        p("File already exists [" + fileName + "]")
        newFileName = fileName + "_" + datetime.now().strftime("%H%M%S")
        p("Moving it to timestamp file: " + newFileName)
        os.rename(fileName, newFileName)

    df.to_csv(fileName)
    p("Option Contracts written to file [", fileName, "]")


def get_filtered_contract_list(ib, config, force_pull=False): # -> "[] of stock and option contracts to pull"

    retArray = []  #array of contracts

    stk = Contract(symbol=config["stock"], secType="STK", exchange="SMART",
                   conId=config["stockContractId"], currency="USD")
    retArray.append(stk)

    fileName = get_options_list_file_name(config)
    if (not os.path.exists(fileName)) or force_pull:
        p("Creating new file: [", fileName, "]")
        pull_options_list(ib, config)
    else:
        p("OptionsList file found.  Using [", fileName, "]")
    optionList = pd.read_csv(fileName)

    #get last price
    #self, reqId, contract, genericTickList, snapshot, regulatorySnapshot, mktDataOptions):
    data = ib.reqMktData(contract=stk, snapshot=True)
    while data.last != data.last:
        ib.sleep(0.01)  # Wait until data is in.
    # ib.cancelMktData(42)
    #p(data)
    p("\nUsing last quote:", data.last)

    # expiryList, quoteLast, optionList, strikeBox=3)
    expiryList = get_expiry_list(datetime.now(), config["weeksOut"])
    retArray += filter_option_list(expiryList, data.last, optionList, config["strikeBox"])
    return retArray


def filter_option_list(expiryList, quoteAmt: float, df, strikeBox: int):

    retArray = []
    df_res = None

    #Filter by type.  Calls only
    df = df[df['right'] == 'C']
    df['strikeDelta'] = df['strike'] - quoteAmt
    df['absStrikeDelta'] = abs(df['strikeDelta'])

    #filter by expiration date
    for i, exp in enumerate(expiryList):
        # df_exp[i] = df[df['lastTradeDateOrContractMonth'] == exp]
        df_week = df[df['lastTradeDateOrContractMonth'] == exp]

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
    df_res = df_res.sort_values(by=['lastTradeDateOrContractMonth', 'strike'], ascending=True)
    for ind in df_res.index:
        # p(df_res["conId"][ind], df_res["strike"][ind],
        #      df_res["lastTradeDateOrContractMonth"][ind], df_res["localSymbol"][ind])
        retArray.append(Contract(conId=df_res["conId"][ind],  secType="OPT", exchange="SMART",
                                 currency="USD", right=df_res["right"][ind], symbol=df_res["localSymbol"][ind],
                                 strike=df_res["strike"][ind], lastTradeDateOrContractMonth =
                                 df_res["lastTradeDateOrContractMonth"][ind]))
    # p('\n Summary: Above Strike (', df_res.shape, ') \n')

    return retArray


def is_trading_hours():
    now = datetime.now()
    hour = int(now.astimezone(pytz.timezone('US/Eastern')).strftime("%H"))
    if hour in range(9, 16): # checking hours for now
        return True
    else:
        p("\n\n\t\t Non-trading hour.[", hour, "] Can't get realtime data. ", now)
        return False


def get_options_list_file_name(config):
    dateStr = datetime.now().astimezone(pytz.timezone('US/Eastern')).strftime("%Y%m%d")
    return makeDataFileName(config["stock"] + "_optionList_" + dateStr, False)


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


def get_expiry_list(quoteTimeDate: datetime, noWeeks: int):
    expiryListArr = []
    wDate = quoteTimeDate
    for i in range(noWeeks):
        wDate = wDate + timedelta((4 - wDate.weekday()) % 7)
        expiryListArr.append(int(wDate.strftime("%Y%m%d")))
        wDate = wDate + timedelta(days=1)
    return expiryListArr
