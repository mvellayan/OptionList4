import math
import os
import pytz
from datetime import datetime, timedelta, date

import pandas as pd
from ib_insync import *
from .FileUtil import *

def getContractList(ib, config): # -> "[] of stock and option contracts to pull"

    retArray = []  #array of contracts

    stk = Contract( symbol= config["stock"], secType = "STK", exchange = "SMART", currency = "USD")
    retArray.append(stk)
    #contract.conId = sec["ConId"]

    contract = Contract()
    contract.symbol = config["stock"]
    contract.secType = "OPT"
    contract.exchange = "SMART"
    contract.currency = "USD"

    dateStr = datetime.now().astimezone(pytz.timezone('US/Eastern')).strftime("%Y%m%d")
    fileName = getFileName(config["stock"] + "_optionList_" + dateStr, addTimestamp=False)

    if not os.path.exists(fileName):
        x = ib.reqContractDetails(contract)
        df = pd.DataFrame(
            columns=['secType', 'conId', 'symbol', 'lastTradeDateOrContractMonth', 'strike', 'right', 'localSymbol'])
        for obj in x:
            c = obj.contract
            df.loc[len(df)] = [c.secType, c.conId, c.symbol, c.lastTradeDateOrContractMonth,
                               c.strike, c.right, c.localSymbol ]
        df.to_csv(fileName)
    else:
        print("File already exists [" + fileName + "]")

    data = ib.reqMktData(stk)
    while data.last != data.last:
        ib.sleep(0.01)  # Wait until data is in.
    ib.cancelMktData(data)

    optionList = pd.read_csv(fileName)
    #expiryList, quoteLast, optionList, strikeBox=3)
    expiryList = getExpiryList(datetime.now(), config["weeksOut"])
    return retArray.append(filterOptionList(expiryList, data.last,
                                            optionList, config["strikeBox"]))


def filterOptionList(expiryList,  quoteAmt: float,  df, strikeBox: int):

    retArray = []
    df_exp = []

    #Filter by type.  Calls only
    df = df[df['right'] == 'C']
    df['strikeDelta'] = df.strike - quoteAmt
    df['absStrikeDelta'] = abs(df['strikeDelta'])

    df_pos = None
    df_neg = None
    df_res = None
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

    # print(df_res.describe())

    # print('\n\n--------------------- Strike (', quoteAmt, ')---------------')
    df_res = df_res.sort_values(by=['lastTradeDateOrContractMonth', 'strike'], ascending=True)
    for ind in df_res.index:
        # print(df_res["conId"][ind], df_res["strike"][ind],
        #      df_res["lastTradeDateOrContractMonth"][ind], df_res["localSymbol"][ind])
        retArray.append(Contract(conId=df_res["conId"][ind],  secType="OPT", exchange="SMART",
                                 currency="USD", right=df_res["right"][ind], symbol=df_res["localSymbol"][ind],
                                 strike=df_res["strike"][ind], lastTradeDateOrContractMonth =
                                 df_res["lastTradeDateOrContractMonth"][ind]))
    # print('\n Summary: Above Strike (', df_res.shape, ') \n')

    return retArray


def tradingHours():
    now = datetime.now()
    hour = int(now.astimezone(pytz.timezone('US/Eastern')).strftime("%H"))
    if hour in range(9,17): # checking hours for now
        return True
    else:
        print("\n\n\t\t Non-trading hour.[", hour, "] Can't get realtime data. ", now)
        return False


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


def getExpiryList(quoteTimeDate: datetime, noWeeks: int):
    expiryListArr = []
    wDate = quoteTimeDate
    for i in range(noWeeks):
        wDate = wDate + timedelta((4 - wDate.weekday()) % 7)
        expiryList.append(int(wDate.strftime("%Y%m%d")))
        wDate = wDate + timedelta(days=1)
    return expiryListArr
