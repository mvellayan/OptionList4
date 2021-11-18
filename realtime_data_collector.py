import os
import sys
import subprocess
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
from utils.FileUtil import p

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
        # p("Received [" + t.time.strftime("%Y%m%d%H%M%S.%f") + "] [" + indexStr + "]", t)
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
        #p(symbol, "->")
        #p(queue)
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


def check_IB_conneciton_broke(ib, msg: str):
    isTradingHours = IBUtil.is_trading_hours()
    isConnected = ib.isConnected()
    if isConnected and isTradingHours:
        # we are good. Praise the Lord!
        return False
    elif ((not isConnected) and isTradingHours):
        subject = "Lost connection during trading hours.  Will Restart"
        p(subject, msg)
        output = subprocess.getoutput("~/Development/OptionList4/start.sh")
        msg += "\nRestart results:\n" + output
        email_notification = \
            "aws sns publish " + \
            ' --topic-arn "arn:aws:sns:us-east-1:775579389744:notifyMuthu"' + \
            ' --subject "' + subject + \
            '" --message "' + msg + '"'
        p("emailing command: ", email_notification)
        os.system(email_notification)
        exit(0)
    elif not isTradingHours:
        p("Not trading hours.  Stopping. " + msg)
        if isConnected:
            ib.disconnect()
        exit(0)
        #os.kill(os.getpid(), signal.SIGINT)
        return True
    else:
        # Should not get here.
        p("Unexpected situation isConnected[" + isConnected + "] and is_trading_hours[" + isTradingHours + "]")
        p(msg)
        exit(0)

    return False


def writeQuotesToFile(arg):
    global queues_start_time, contracts
    while True:
        time.sleep(60) # Sleep 1 minute
        if (datetime.now() - queues_start_time).total_seconds() >= config["file_flush_seconds"]:
            p("Writing to file.")
            queues_start_time = datetime.now()
            saveDataInCSV()

        #2nd thread needs to handle this as well.
        check_IB_conneciton_broke(ib, threading.current_thread().name + ': writeQuotesFile Thread.')


def main(configFileName):
    global config, contracts
    config = FileUtil.readConfig(configFileName)

    writeThread = threading.Thread(target=writeQuotesToFile, args=(1,))
    writeThread.start()

    p("Connecting to ip [", config["tws_host"], "] port[", config["tws_port"], "] clientId [", config["tws_port"], "]")
    try:
        ib.connect(config["tws_host"], config["tws_port"], clientId=config["tws_port"])
    except BaseException as err:
        p(f"Unexpected {err=}, {type(err)=}")
        raise NameError("Cannot connect to IB")

    p("Connection Status: ", ib.isConnected())

    contracts = IBUtil.get_filtered_contract_list(ib, config)
    pprint(contracts)
    for con in contracts:
        ib.reqMktData(con, '100,104,106', False, False)
    ib.sleep(2)

    ib.pendingTickersEvent += onPendingTicker

    ctr = 0
    while True:
        # ib.run(timeout=6)
        ib.sleep(60)  #seconds
        check_IB_conneciton_broke(ib, threading.current_thread().name + ': Main loop thead.')
        ctr += 1

        # Update contracts: Remove old contracts
        new_contracts = IBUtil.get_filtered_contract_list(ib, config, (ctr % 15 == 0))

        found_changes = False
        for con in new_contracts:
            if con not in contracts:
                found_changes = True
                break

        if found_changes:
            p("Found Changes, processing new contract list:")
            pprint(new_contracts)
            # Update contracts: Remove old contracts not in new list
            for con in contracts:
                if con not in new_contracts:
                    p("removing contract:", con)
                    ib.cancelMktData(con)
            # Update contracts: add new contracts not in old list
            for con in new_contracts:
                if con not in contracts:
                    p("adding contract:", con)
                    ib.reqMktData(con, '100,104,106', False, False)
            contracts = new_contracts
        else:
            p("No changes detected.  Using the same contract list")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        p("\t\tUsage: collect_data.py <config_file.yml>\n\n")
        sys.exit(0)
    else:
        p("\tusing config file [" + sys.argv[1] + "]")

    main(sys.argv[1])
