import sys, os, signal
from pprint import pprint
import threading, csv
from threading import Condition
import time
from datetime import datetime

import pytz
from ib_insync import *

from utils import FileUtil, IBUtil

#
# see: https://github.com/erdewit/ib_insync
queues = {}
queues_start_time = datetime.now()
config = {}
condition = Condition()
ib = IB() # IB connection
contracts = [] #array of contracts we are trackng


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
    header = ['ConId', 'Symbol', 'Time', 'Bid', 'BidSize', 'Ask', 'AskSize',
              'Last', 'LastSize', 'Volume', 'histVolatility', 'impliedVolatility']
    for symbol in queues:
        queue = queues.get(symbol)
        #print(symbol, "->")
        #pprint(queue)
        if len(queue) == 0:
            break
        with open(FileUtil.makeDataFileName(symbol), 'w', encoding='UTF8', newline='') as f:
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


def writeQuotesToFile(arg):
    global queues_start_time, contracts
    while True:
        time.sleep(60) # Sleep 1 minute
        if (datetime.now() - queues_start_time).total_seconds() >= config["file_flush_seconds"]:
            print(datetime.now().strftime("%Y%m%d%H%M%S") , ": Writing to file.")
            queues_start_time = datetime.now()
            saveDataInCSV()

        if not ib.isConnected():
            raise NameError('Lost IB Connection  Exiting thread...')
            os.kill(os.getpid(), signal.SIGINT)
        else:
            if not IBUtil.is_trading_hours():
                ib.disconnect()
                os.kill(os.getpid(), signal.SIGINT)
                raise NameError('Market Closed.  Exiting thread...')




def main(configFileName):
    global config
    config = FileUtil.readConfig(configFileName)

    writeThread = threading.Thread(target=writeQuotesToFile, args=(1,))
    writeThread.start()

    print("Connecting to ip [", config["tws_host"], "] port[", config["tws_port"], "] clientId [", config["tws_port"], "]")
    try:
        ib.connect(config["tws_host"], config["tws_port"], clientId=config["tws_port"])
    except BaseException as err:
        print(f"Unexpected {err=}, {type(err)=}")
        raise NameError("Cannot connect to IB")

    print("Connection Status: ", ib.isConnected())

    contracts = IBUtil.get_filtered_contract_list(ib, config)
    pprint(contracts)
    for con in contracts:
        ib.reqMktData(con, '100,104,106', False, False)
    ib.sleep(2)

    ib.pendingTickersEvent += onPendingTicker

    ctr = 0
    while True:
        #ib.run(timeout=6)
        ib.sleep(60)
        if not ib.isConnected():
            print("Lost IB connection. Exiting.")
            os.kill(os.getpid(), signal.SIGINT)
            break
        else:
            if not IBUtil.is_trading_hours():
                ib.disconnect()
                os.kill(os.getpid(), signal.SIGINT)
                break
        ctr += 1
        if ctr > 9:
            print("checking for contract changes.")
            ctr = 0
            # Update contracts: Remove old contracts
            new_contracts = IBUtil.get_filtered_contract_list(ib, config)
            found_changes = False
            for con in contracts:
                if con not in new_contracts:
                    found_changes = True
                    break
            if found_changes:
                print("Contract List changes detected.  New Contracts: ------------------")
                pprint(new_contracts)
                # Update contracts: Remove old contracts not in new list
                for con in contracts:
                    if con not in new_contracts:
                        print("removing contract:", con)
                        ib.cancelMktData(con)
                # Update contracts: add new contracts not in old list
                if con in new_contracts:
                    if con not in contracts:
                        print("adding contract:", con)
                        ib.reqMktData(con, '100,104,106', False, False)
                contracts = new_contracts
            else:
                print("No changes detected.  Using the same contract list")



if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\n\nUsage: collect_data.py <config_file.yml>\n\n")
        sys.exit(0)
    else:
        print("using config file [" + sys.argv[1] + "]")

    main(sys.argv[1])
