import csv
import errno
import json
import math
import os
import re
import sys
import schedule
import time
from datetime import datetime
from pprint import pprint
import threading
from threading import Condition, Event
from utils import FileUtil, IBUtil
import random

import pytz
from ib_insync import *

#
# see: https://github.com/erdewit/ib_insync
queues = {}
queues_start_time = datetime.now()
config = {}
condition = Condition()
ib = IB()
exitEvent = threading.Event()


def onPendingTicker(tickers):
    global queues
    condition.acquire()

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
                tkr = queue.get(timeStamp)
                quoteTime = tkr.quoteTime.astimezone(pytz.timezone('US/Eastern')).strftime("%Y%m%d%H%M%S")
                writer.writerow( [tkr.conId, tkr.symbol, quoteTime, tkr.bid,
                                  tkr.bidSize, tkr.ask, tkr.askSize, tkr.last, tkr.lastSize,
                                  tkr.volume, tkr.histVolatility, tkr.impliedVolatility])
        queue.clear()
    condition.release()

def writeJob(arg):
    global ib, queues_start_time, exitEvent
    #print('   writeJob polling start...');
    time.sleep(60)  #run for 60 seconds no matter what 
    while True:
        if (datetime.now() - queues_start_time).total_seconds() >= config["file_flush_seconds"]:
            print(datetime.now().strftime("%Y%m%d%H%M%S") , ": Writing to file.")
            queues_start_time = datetime.now()
            saveDataInCSV()

        #is it time to exit??
        now = datetime.now()
        #print('   writeJob exit checking...', now);
        if (now.hour >= 16 and now.minute > 4):
            print("\n\n\t\tTime to Exit.")
            ib.disconnect()
            exitEvent.set()
            raise NameError('Market Closed.  Exiting...')
        time.sleep(60)


def main(configFileName):
    global config, ib, exitEvent
    config = FileUtil.readConfig(configFileName)

    writeThread = threading.Thread(target=writeJob, args=(1,))
    writeThread.start()

    print("Connecting to ip [", config["tws_host"], "] port[", config["tws_port"], "] clientId [", config["tws_port"], "]")
    try:
        ib.connect(config["tws_host"], config["tws_port"], clientId=config["tws_port"])
    except BaseException as err:
        print(f"Unexpected {err=}, {type(err)=}")
        #raise

    print("Connection Status: ", ib.isConnected())

    contracts = IBUtil.getContractList(ib, config)

    #for idx, c in enumerate(contracts):
    #    print(idx, ':\t', c)

    for con in contracts:
        ib.reqMktData(con, '104,106', False, False)

    ib.sleep(2)
    ib.pendingTickersEvent += onPendingTicker
    ib.run(exitEvent)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\n\nUsage: collect_data.py <config_file.yml>\n\n")
        sys.exit(0)
    else:
        print("using config file [" + sys.argv[1] + "]")

    main(sys.argv[1])
