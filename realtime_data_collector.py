from ib_insync import *
from IPython.display import display, clear_output
import pandas as pd
from threading import Thread, Condition
import time
import random
import csv


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

ib = IB()

# use this instead for IB Gateway
#ib.connect('127.0.0.1', 7497, clientId=1)

# us this for TWS (Workstation)
#ib.connect('127.0.0.1', 7497, clientId=1)


ib.connect('127.0.0.1', 4002, clientId=1)

stock = Stock('AMD', 'SMART', 'USD')

md = ib.reqMktData(stock, '', False, False)
ib.sleep(2)

#print(md.time,md.bidSize, md.bid, md.ask, md.askSize, md.high, md.low, md.close)
#print(md.bid, md.bidSize, md.ask, md.askSize, md.last, md.lastSize, md.prevBidSize, md.prevAskSize, md.volume, md.open, md.high, md.low, md.close, md.ticks)

queue = []
MAX_NUM = 1000
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