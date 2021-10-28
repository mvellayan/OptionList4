import csv
import errno
import json
import os
import re
from datetime import datetime
from pprint import pprint
from threading import Condition
import math

import pytz
from ib_insync import *

#
# see: https://github.com/erdewit/ib_insync
queues = {}
queues_start_time = datetime.now()
config = {}
condition = Condition()


def readConfig(fileName):
    data = {}
    try:
        # open file and load data
        f = open(fileName, 'r')
        data = json.load(f)
        print("\n\nINFO: Parameter File:")
        pprint(data)
        f.close()
    except OSError:
        print('cannot open file', fileName)
        sys.exit(1)
    # verify fields exist
    print("\nINFO: parameters Check:")
    print(data["tws_port"], data["file_flush_seconds"], data["contracts"])
    print("\n")
    return data


def getContract(sec):
    print("Processing contract: ", sec["ConId"], sec["Symbol"], sec["SecType"])
    contract = Contract()
    contract.symbol = sec["Symbol"]
    contract.conId = sec["ConId"]
    contract.secType = sec["SecType"]
    contract.exchange = "SMART"
    contract.currency = "USD"
    return contract


def getFileName(symbol):
    now = datetime.now()  # current date and time
    year_str = now.strftime("%Y")
    month_str = now.strftime("%m")
    day_str = now.strftime("%d")
    time_str = now.strftime("%H%M%S")
    #making contract name to file name:
    contractName = ''.join(re.findall('[a-zA-Z0-9]+', symbol))
    fileName = "data/" + year_str + "/" + month_str + "/" + day_str + "/" + contractName + "_" \
               + year_str + month_str + day_str + "_" + time_str +'.csv'
    makeDirectory(fileName)
    return fileName


def makeDirectory(fileName):
    if not os.path.exists(os.path.dirname(fileName)):
        try:
            os.makedirs(os.path.dirname(fileName))
        except OSError as exc:  # Guard against race condition
            if exc.errno != errno.EEXIST:
                print ("ERROR")
                print ( exc )
                #raise

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


def onPendingTicker(tickers):
    global queues, queues_start_time
    condition.acquire()

    if  (datetime.now() - queues_start_time).total_seconds() >= config["file_flush_seconds"]:
        print("Writing to file.")
        queues_start_time = datetime.now()
        saveDataInCSV()

    for t in tickers:
        indexStr = t.time.strftime("%Y%m%d%H%M%S")
        # print("Received [" + t.time.strftime("%Y%m%d%H%M%S.%f") + "] [" + indexStr + "]", t)
        if t.contract.symbol in queues:
            queue = queues[t.contract.symbol]
        else:
            queue = {}
            queues[t.contract.symbol] = queue
        queue[indexStr] = MarketData(t)
    condition.release()


def saveDataInCSV():
    condition.acquire()
    global queues

    #old_queues = queues
    #queues = {}
    #condition.release()
    #Move all this to new thread ??

    header = ['ConId', 'Symbol', 'Time',
              'Bid', 'BidSize', 'Ask', 'AskSize',
              'Last', 'LastSize',
              'Volume', 'histVolatility', 'impliedVolatility']
    for symbol in queues:
        queue = queues.get(symbol)
        #print(symbol, "->")
        #pprint(queue)
        if len(queue) == 0:
            break
        with open(getFileName(symbol), 'w', encoding='UTF8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            for timeStamp in queue:
                ticker = queue.get(timeStamp)
                quoteTime = ticker.quoteTime.astimezone(pytz.timezone('US/Eastern')).strftime("%Y%m%d%H%M%S")
                # print(timeStamp, "->>", quoteTime, ticker)
                writer.writerow( [ticker.conId, ticker.symbol, quoteTime, ticker.bid,
                                  ticker.bidSize, ticker.ask, ticker.askSize, ticker.last, ticker.lastSize,
                                  ticker.volume, ticker.histVolatility, ticker.impliedVolatility])
        queue.clear()
    condition.release()


def main():
    global config
    config = readConfig("config/config.json")

    ib = IB()
    ib.connect('127.0.0.1', config["tws_port"], clientId=1)

    stock = Stock('AMD', 'SMART', 'USD')
    for sec in config["contracts"]:
        con = getContract(sec)
        ib.reqMktData(con, '104,106', False, False)
        #pprint(sec)

    ib.sleep(2)
    ib.pendingTickersEvent += onPendingTicker
    ib.run()


if __name__ == "__main__":
    main()
