import math
import os
from datetime import datetime, timedelta, date

import pandas as pd
from ib_insync import *
from .FileUtil import *

def getContractList(ib, config): # -> "[] of stock and option contracts to pull"

    retArray = []

    stk = Contract( symbol= config["stock"], secType = "STK", exchange = "SMART", currency = "USD")
    retArray.append(stk)
    #contract.conId = sec["ConId"]

    contract = Contract()
    contract.symbol = config["stock"]
    contract.secType = "OPT"
    contract.exchange = "SMART"
    contract.currency = "USD"

    fileName = getFileName(config["stock"] +"_optionList_" + datetime.today().strftime("%Y%m%d"), addTimestamp=False)

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
        print("Reading from cache file [" + fileName + "]")
        df = pd.read_csv(fileName)

    endDate = date.today() + timedelta(days=(7 * config["weeksOut"]))
    # print ( df['lastTradeDateOrContractMonth'].to_string())
    strDate:str = endDate.strftime("%Y%m%d") + ""
    df = df [ (df['lastTradeDateOrContractMonth'].astype(str)  ) <= strDate  ]
    df = df [ df['right'] == 'C']
    data = ib.reqMktData(stk)
    while data.last != data.last:
        ib.sleep(0.01)  # Wait until data is in.
    ib.cancelMktData(data)

    print(df.describe())
    print("Last quote for [" + config["stock"]+ "] was : ", data.last)

    df['strikeDelta'] = df.strike - data.last
    df['absStrikeDelta'] = abs(df['strikeDelta'])
    df_pos = df[df['strikeDelta'] >= 0 ]
    df_neg = df[df['strikeDelta'] < 0]

    df_pos['rank'] = df_pos['absStrikeDelta'].rank(na_option='bottom')
    df_neg['rank'] = df_neg['absStrikeDelta'].rank(na_option='bottom')

    print ('\n\n--------------------- Above Strike (', data.last, ')---------------')
    df_pos = df_pos.sort_values(by = 'rank').head(  config['weeksOut']* config['strikeBox'])
    for ind in df_pos.index:
        print(df_pos["conId"][ind], df_pos["localSymbol"][ind], df_pos["localSymbol"][ind])
        retArray.append(Contract(conId=df_pos["conId"][ind],  secType="OPT", exchange="SMART",
                                 currency="USD", right=df_pos["right"][ind], symbol=df_pos["localSymbol"][ind]))

    print('\n\n--------------------- Below Strike (', data.last, ')---------------')
    df_neg = df_neg.sort_values(by='rank').head(config['weeksOut'] * config['strikeBox'])
    for ind in df_neg.index:
        print(df_neg["conId"][ind], df_neg["localSymbol"][ind], df_neg["localSymbol"][ind])
        retArray.append(Contract(conId=df_neg["conId"][ind],  secType="OPT", exchange="SMART",
                                 currency="USD", right=df_neg["right"][ind], symbol=df_neg["localSymbol"][ind]))
    print('\n Summary: Above Strike (', df_pos.shape, '), Below Strike (', df_neg.shape, ') \n')
    return retArray


def tradingHours():
    now = datetime.now()
    if ((now.hour >= 16 and now.minute > 4) or (now.hour < 9 and now.munute < 25)):
        print("\n\n\t\t Non-trading hours. Can't get realtime data. ", now)
        return False
    return True


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


