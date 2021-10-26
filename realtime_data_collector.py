from ib_insync import *
from IPython.display import display, clear_output
import pandas as pd
from threading import Thread, Condition
import time
import random
import csv
import json
from pprint import pprint


class MarketData:
    def __init__(self,time,bid,bidSize,ask,askSize,last,lastSize, prevBidSize, prevAskSize,volume,open,high,low,close):
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
    print(data["tws_port"], data["file_max_rows"], data["contracts"])
    print("\n")
    return data


ib = IB()
config = readConfig("config/config.json")

ib.connect('127.0.0.1', config["tws_port"], clientId=1)

stock = Stock('AMD', 'SMART', 'USD')

md = ib.reqMktData(stock, '', False, False)
ib.sleep(2)

#print(md.time,md.bidSize, md.bid, md.ask, md.askSize, md.high, md.low, md.close)
#print(md.bid, md.bidSize, md.ask, md.askSize, md.last, md.lastSize, md.prevBidSize, md.prevAskSize, md.volume, md.open, md.high, md.low, md.close, md.ticks)

queue = []
MAX_NUM = 100
condition = Condition()

def onPendingTicker(tickers):
    global queue
    print("Pending ticker event received.")
    condition.acquire()
    if len(queue) == MAX_NUM:
        print("Queue is totally full.")
        saveDataInCSV() 
    for t in tickers:
        #print(t.time, t.bid, t.bidSize, t.ask, t.askSize, t.last, t.lastSize, t.prevBidSize, t.prevAskSize, t.volume, t.open, t.high, t.low, t.close, t.ticks)
        data=MarketData(t.time, t.bid, t.bidSize, t.ask, t.askSize, t.last, t.lastSize, t.prevBidSize, t.prevAskSize, t.volume, t.open, t.high, t.low, t.close)
        queue.append(data)
    #time.sleep(10)  
    condition.release()  

ib.pendingTickersEvent += onPendingTicker

def saveDataInCSV():
    condition.acquire()
    global queue
    header = ['Time','Bid','BidSize','Ask','AskSize','Last','LastSize', 'PrevBidSize', 'PrevAskSize','Volume','Open','High','Low','Close']
    marketData = []
    data = []
    fileName = (str(int(time.time()))+'.csv')
    with open(fileName, 'w', encoding='UTF8', newline='') as f:
        writer = csv.writer(f)

        # write the header
        writer.writerow(header) 
        while True: 
            if not queue:
                break
            md = queue.pop(0) 
            # write the data
            writer.writerow([md.time,md.bid, md.bidSize, md.ask, md.askSize, md.last, md.lastSize, md.prevBidSize, md.prevAskSize, md.volume, md.open, md.high, md.low, md.close])
    condition.release()

ib.run()