import csv
import errno
import json
import os
import re
from datetime import datetime
from pprint import pprint
from threading import Condition

from ib_insync import *

#
# see: https://github.com/erdewit/ib_insync
#

queues = {}
queues_start_time = datetime.now()

config = {}
condition = Condition()


class MarketData:
    def __init__(self, contract, time,bid,bidSize,ask,askSize,last,lastSize, prevBidSize, prevAskSize,volume,open,high,low,close):
        self.contract = contract
        self.time = time
        self.bid = bid
        self.bidSize = bidSize
        self.ask = ask
        self.askSize = askSize
        self.last = last
        self.lastSize = lastSize
        self.prevBidSize = prevBidSize
        self.prevAskSize = prevAskSize
        self.volume = volume
        self.open = open
        self.high = high
        self.low = low
        self.close = close

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

def onPendingTicker(tickers):
    global queues, queues_start_time
    condition.acquire()

    if  (datetime.now() - queues_start_time).total_seconds() >= config["file_flush_seconds"]:
        print("Queue limit is reached, writing to file.")
        queues_start_time = datetime.now()
        saveDataInCSV() 
    for t in tickers:
        print("Received [" + t.time.strftime("%Y%m%d%H%M%S.%f") + "] ["+ t.contract.symbol +"]")
        #print(t.time, t.bid, t.bidSize, t.ask, t.askSize, t.last, t.lastSize, t.prevBidSize, t.prevAskSize, t.volume, t.open, t.high, t.low, t.close, t.ticks)
        data = MarketData(t.contract, t.time, t.bid, t.bidSize, t.ask, t.askSize, t.last, t.lastSize, t.prevBidSize, t.prevAskSize, t.volume, t.open, t.high, t.low, t.close)
        if t.contract.symbol in queues:
            queue = queues[t.contract.symbol]
        else:
            queue = []
            queues[t.contract.symbol] = queue
        queue.append(data)
    #time.sleep(10)  
    condition.release()


def getFileName(symbol):
    now = datetime.now()  # current date and time
    year_str = now.strftime("%Y")
    month_str = now.strftime("%m")
    day_str = now.strftime("%d")
    time_str = now.strftime("%H%M%S")
    #making contract name to file name:
    contractName = ''.join(re.findall('[a-zA-Z0-9]+', symbol))
    fileName = "data/" + year_str + "/" + month_str + "/" + day_str + "/" + contractName + "_" + time_str   +'.csv'
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


def saveDataInCSV():
    condition.acquire()
    global queues

    #old_queues = queues
    #queues = {}
    #condition.release()
    #Move all this to new thread ??

    header = ['ConId', 'Symbol', 'Time', 'Bid', 'BidSize', 'Ask', 'AskSize', 'Last', 'LastSize', 'PrevBidSize',
              'PrevAskSize', 'Volume', 'Open', 'High', 'Low', 'Close']
    for symbol, queue in queues.items():
        if len(queue) == 0:
            break
        fileName = getFileName(symbol)
        makeDirectory(fileName)
        with open(fileName, 'w', encoding='UTF8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            while True:
                if not queue:
                    break
                md = queue.pop(0)
                # write the data
                writer.writerow( [ md.contract.conId, md.contract.symbol, md.time.strftime("%Y%m%d%H%M%S.%f"), md.bid, md.bidSize, md.ask, md.askSize, md.last, md.lastSize,
                                   md.prevBidSize,  md.prevAskSize, md.volume, md.open, md.high, md.low, md.close])
    condition.release()


def getContract(sec):
    print("Processing contract: ", sec["ConId"], sec["Symbol"], sec["SecType"] )
    contract = Contract()
    contract.symbol = sec["Symbol"]
    contract.conId = sec["ConId"]
    contract.secType = sec["SecType"]
    contract.exchange = "SMART"
    contract.currency = "USD"
    return contract


def main():
    global config
    config = readConfig("config/config.json")

    ib = IB()
    ib.connect('127.0.0.1', config["tws_port"], clientId=1)

    stock = Stock('AMD', 'SMART', 'USD')
    for sec in config["contracts"]:
        con = getContract(sec)
        ib.reqMktData(con, '', False, False)
        #pprint(sec)

    ib.sleep(2)
    ib.pendingTickersEvent += onPendingTicker
    ib.run()


if __name__ == "__main__":
    main()
