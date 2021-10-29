import csv
import errno
import json
import math
import os
import re
import sys
from datetime import datetime
from pprint import pprint
from threading import Condition
from utils import FileUtil, IBUtil

import pytz
from ib_insync import *

#
# see: https://github.com/erdewit/ib_insync
queues = {}
queues_start_time = datetime.now()
config = {}
condition = Condition()


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
        queue[indexStr] = IBUtil.MarketData(t)
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
        with open(FileUtil.getFileName(symbol), 'w', encoding='UTF8', newline='') as f:
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


def main(configFileName):


    global config
    config = FileUtil.readConfig(configFileName)

    ib = IB()
    ib.connect('127.0.0.1', config["tws_port"], clientId=1)

    stock = Stock('AMD', 'SMART', 'USD')
    for sec in config["contracts"]:
        con = IBUtil.getContract(sec)
        ib.reqMktData(con, '104,106', False, False)
        #pprint(sec)

    ib.sleep(2)
    ib.pendingTickersEvent += onPendingTicker
    ib.run()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\n\nUsage: collect_data.py <config_file.yml>\n\n")
        sys.exit(0)
    else:
        print("using config file [" + sys.argv[1] + "]")

    main(sys.argv[1])
