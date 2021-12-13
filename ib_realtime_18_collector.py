import argparse
import json
import os, psutil, sys
import subprocess
from pprint import pprint
from pprint import pformat
import threading, csv
from threading import Condition
import time
from datetime import datetime
import logging

import pytz
from ib_insync import *

from utils import FileUtil, IBUtil

#
# see: https://github.com/erdewit/ib_insync

queues = {}
queues_start_time = datetime.now()
condition = Condition()
ib = IB() # IB connection
contracts = [] #array of contracts we are trackng
global log, config


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
    header = ['con_id', 'symbol', 'time', 'bid', 'bid_size', 'ask', 'ask_size',
              'last', 'last_size', 'volume', 'hist_volatility', 'implied_volatility']
    for symbol in queues:
        queue = queues.get(symbol)
        out_file = FileUtil.makeDataFileName(symbol)
        out_file_exists = os.path.exists(out_file)
        log.info("Saving [" + symbol + "] rows to file [" + out_file + "] row-count [" + str(len(queue))+ "]")
        if len(queue) == 0:
            break
        with open(out_file, 'a', encoding='UTF8', newline='') as f:
            writer = csv.writer(f)
            if not out_file_exists:
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
        log.info(subject + "," + msg)
        output = subprocess.getoutput("~/Development/OptionList4/start.sh")
        msg += "\nRestart results:\n" + output
        email_notification = \
            "aws sns publish " + \
            ' --topic-arn "arn:aws:sns:us-east-1:775579389744:notifyMuthu"' + \
            ' --subject "' + subject + \
            '" --message "' + msg + '"'
        log.info("emailing command: " + email_notification)
        os.system(email_notification)
        sys.exit(0)
    elif not isTradingHours:
        log.info("Not trading hours.  Stopping. " + msg)
        sys.exit(0)
    else:
        # Should not get here.
        log.info(f"Unexpected situation isConnected[{isConnected}] and is_trading_hours[{isTradingHours} {msg}")
        sys.exit(0)
    return False


def writeQuotesToFile(arg):
    global queues_start_time, contracts
    while True:
        time.sleep(60) # Sleep 1 minute
        if (datetime.now() - queues_start_time).total_seconds() >= config["file_flush_seconds"]:
            log.info("writeQuotesToFile for " + config["stock"])
            queues_start_time = datetime.now()
            saveDataInCSV()

        #2nd thread needs to handle this as well.
        check_IB_conneciton_broke(ib, threading.current_thread().name + ': writeQuotesFile Thread.')


def main():
    global config, contracts

    writeThread = threading.Thread(target=writeQuotesToFile, args=(1,), daemon=True)
    writeThread.start()

    log.info("Connecting to ip [" + config["tws_host"] + "] port[" + str(config["tws_port"])
             + "] clientId [" + str(config["tws_port"]) + "]")
    try:
        ib.connect(config["tws_host"], config["tws_port"], clientId=config["tws_port"])
    except BaseException as err:
        log.error(f"Unexpected Error")
        log.error(err)
        raise NameError("Cannot connect to IB")

    log.info("Connection Status: " + str(ib.isConnected()))

    contracts = IBUtil.get_filtered_contract_list(ib, config)
    pprint(contracts)
    log.info(pformat(contracts))
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
            log.info("Found Changes, processing new contract list:")
            pprint(new_contracts)
            log.info(pformat(contracts))
            # Update contracts: Remove old contracts not in new list
            for con in contracts:
                if con not in new_contracts:
                    log.info("removing contract:")
                    log.info(con)
                    ib.cancelMktData(con)
            # Update contracts: add new contracts not in old list
            for con in new_contracts:
                if con not in contracts:
                    log.info("adding contract:")
                    log.info(con)
                    ib.reqMktData(con, '100,104,106', False, False)
            contracts = new_contracts
        else:
            log.info("No changes detected.  Using the same contract list")


def collect_args() -> dict:
    """Collect arguments passed into the script

    Returns:
        dict: Arguments Object
    """
    parser = argparse.ArgumentParser(
        description='Collect per second Realtime Data for a stock + 18 related options')

    parser.add_argument('config', help='JSON file that contains all the configuration',
                        default="config.json", type=str)
    parser.add_argument('--verbose', help='Enable verbose output', action='store_true')
    parser.add_argument('--debug', help='Enable debug output', action='store_true')
    parser.add_argument('--info', help='Enable info level output', action='store_true')

    return parser.parse_args()


if __name__ == "__main__":
    args = collect_args()

    logging.basicConfig(level=logging.ERROR)
    log = logging.getLogger('myLogger')
    log.setLevel(logging.INFO)

    config = FileUtil.readConfig(args.config)
    main()
