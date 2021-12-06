import argparse
import json
import os
import sys
import subprocess
from pprint import pprint
from pprint import pformat
import threading, csv
from threading import Condition
import time
from datetime import datetime, timedelta
import logging

import pytz
from ib_insync import *

from utils import FileUtil, IBUtil

log = logging.getLogger("myLogger")

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
        log.info(isConnected)
        log.info("] and is_trading_hours[")
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


def main(dt):
    global config, contracts, quote_date_str, quote_date

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

    #https://ib-insync.readthedocs.io/recipes.html
    barsList = []
    st :str = dt + " 16:00:00"
    while True:
        bars = ib.reqHistoricalData(
            stk,
            endDateTime=st,
            durationStr='1 D',
            barSizeSetting='5 secs',
            whatToShow='MIDPOINT',
            useRTH=True,
            formatDate=1,
            keepUpToDate=False)
        if not bars:
            break
        barsList.append(bars)
        dt = bars[0].date

    # save to CSV file
    allBars = [b for bars in reversed(barsList) for b in bars]
    #df = util.df(allBars)
    print("len=", len(barsList))
    i = 0
    for b in barsList:
        print ("\t", i , ":", b)
        i += 1
    sys.exit(1)

    bars = ib.reqHistoricalData(stk, endDateTime=quote_date_str + " 16:00:00", durationStr="1 D",
                            barSizeSetting="1 secs",
                            whatToShow="MIDPOINT, HISTORICAL_VOLATILITY, OPTION_IMPLIED_VOLATILITY",
                            useRTH=True,  # regular Trading Hours only = True
                            formatDate=1, keepUpToDate=False)
    print("bars =", bars)



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


def collect_args() -> dict:
    """Collect arguments passed into the script

    Returns:
        dict: Arguments Object
    """
    parser = argparse.ArgumentParser(
        description='Collect per second Historic Data for a stock + 18 related options')

    parser.add_argument('config', help='JSON file that contains all the configuration',
                        default="config.json", type=str)
    parser.add_argument('dates',
                        help='Date or DateRage to pull data. eg: YYYYMMDD or YYYYMMDD,YYYYMMDD',
                        default=FileUtil.getStrFromDate(datetime.now(), "YYYYMMDD"), type=str)
    parser.add_argument('--verbose', help='Enable verbose output', action='store_true')
    parser.add_argument('--debug', help='Enable debug output', action='store_true')
    parser.add_argument('--info', help='Enable info level output', action='store_true')

    return parser.parse_args()



if __name__ == "__main__":

    logging.basicConfig(level=logging.ERROR)
    log = logging.getLogger('myLogger')
    log.setLevel(log.info)

    log = logging.getLogger('myLogger')
    log.setLevel(logging.INFO)
    args = collect_args()

    config = FileUtil.readConfig(args.config)

    quote_date_str = args.dates.split(',')
    quote_date = []

    if len(quote_date_str) == 1:
        quote_date.append(FileUtil.getDateObjFromStr(quote_date_str[0], "YYYYMMDD"))
    elif len(quote_date_str) == 2:
        cur_date = FileUtil.getDateObjFromStr(quote_date_str[0], "YYYYMMDD")
        end_date = FileUtil.getDateObjFromStr(quote_date_str[1], "YYYYMMDD")
        ctr = 0;
        while cur_date <= end_date and ctr < 31:
            quote_date.append(cur_date)
            cur_date += timedelta(days=1)
            ctr += 1
    else:
        raise Exception("Unexpected data parameter.  should be 1 date or 2 dates (start-end)")

    main("20211130")
