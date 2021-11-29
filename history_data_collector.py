import os
import sys
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
from utils.FileUtil import setup_logging

## Globals
queues = {}
quote_date_str = str()
quote_date = datetime.now()
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
    header = ['ConId', 'Symbol', 'Time', 'Bid', 'BidSize', 'Ask', 'AskSize',
              'Last', 'LastSize', 'Volume', 'histVolatility', 'impliedVolatility']
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
        exit(0)
    elif not isTradingHours:
        log.info("Not trading hours.  Stopping. " + msg)
        if isConnected:
            ib.disconnect()
        exit(0)
        #os.kill(os.getpid(), signal.SIGINT)
        return True
    else:
        # Should not get here.
        log.info("Unexpected situation isConnected[")
        log.inof(isConnected)
        log.infor("] and is_trading_hours[")
        log.info(isTradingHours)
        log.info(msg)
        exit(0)

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
    global config, contracts, quote_date_str, quote_date

    writeThread = threading.Thread(target=writeQuotesToFile, args=(1,))
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

    # 1. get stock qutotes for the day and save to file
    ### this does not work =(
    stk = Contract(symbol=config["stock"], secType="STK", exchange="SMART",
                   conId=config["stockContractId"], currency="USD")

    bars = ib.reqHistoricalData(stk, endDateTime=quote_date_str + " 16:00:00", durationStr="1 D",
                            barSizeSetting="1 secs",
                            whatToShow="MIDPOINT, HISTORICAL_VOLATILITY, OPTION_IMPLIED_VOLATILITY",
                            useRTH=True,  # regular Trading Hours only = True
                            formatDate=1, keepUpToDate=False)
    print("bars =", bars)

    sys.exit(1)

    # 2. get option quotes for the day and save to file
    # 3. get filtered option list for the day
    #     use existing funciton IBUtil.get_filtered_contract_list(ib, config, quoteAmt = each of the quote amount)
    #     then collect a unique set of contracts
    # 4. get option quotes for the day for each of the filterd unique contract


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

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("\t\tUsage: collect_data.py <config_file.yml> <yyyy-mm-dd>\n\n")
        sys.exit(0)
    else:
        print("\tusing config file [" + sys.argv[1] + "]")

    config = FileUtil.readConfig(sys.argv[1])
    quote_date_str = sys.argv[2]
    quote_date = FileUtil.getDateObjFromStr(sys.argv[2], "YYYYMMDD")


    log_dir = ""
    if os.path.isdir("/logs"):
            log_dir = "/logs/"
    elif os.path.isdir("logs"):
        log_dir = "logs/"
    fn = log_dir + config["stock"] + "history_data_collector.log"
    print("Passing in fn = [" + fn + "]")
    log = setup_logging(fn)
    FileUtil.setLog(log)
    IBUtil.setLog(log)

    log.error("Starting with arguments: ")
    log.info(sys.argv)
    main()



