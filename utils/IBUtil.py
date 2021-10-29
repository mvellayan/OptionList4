import errno
import json
import math
import sys

from ib_insync import *

def getContract(sec):
    print("Processing contract: ", sec["ConId"], sec["Symbol"], sec["SecType"])
    contract = Contract()
    contract.symbol = sec["Symbol"]
    contract.conId = sec["ConId"]
    contract.secType = sec["SecType"]
    contract.exchange = "SMART"
    contract.currency = "USD"
    return contract

class MarketData:
    def __init__(self, ticker):
        self.conId = ticker.contract.conId
        self.symbol = ticker.contract.symbol
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

