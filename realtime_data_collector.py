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
MAX_NUM = 500
condition = Condition()

def onPendingTicker(tickers):
    global queue
    print("============= pending ticker event received ==============")
    condition.acquire()
    if len(queue) == MAX_NUM:
        print("Queue is totally full.")
        saveDataInCSV() 
        condition.wait()
        #condition.notify()
        condition.release()
        print("Notified the producer")
    for t in tickers:
        #print(t.time, t.bid, t.bidSize, t.ask, t.askSize, t.last, t.lastSize, t.prevBidSize, t.prevAskSize, t.volume, t.open, t.high, t.low, t.close, t.ticks)
        data=MarketData(t.time, t.bid, t.bidSize, t.ask, t.askSize, t.last, t.lastSize, t.prevBidSize, t.prevAskSize, t.volume, t.open, t.high, t.low, t.close)
        queue.append(data)
    #time.sleep(10)    

ib.pendingTickersEvent += onPendingTicker

def saveDataInCSV():
    print("saveDataInCSV function get called.")
    global queue
    print(queue)
    # while True:
    #     condition.acquire()
    #     if not queue:
    #         print("Queue is empty")               
    #         condition.notify()
    #         condition.release()
    #         print("Notify onPendingTicker()")
    #         condition.wait()
    #     data = queue.pop(0)
    #     print("data ===> ", data)
    header = ['time','bid','bidSize','ask','askSize','last','lastSize', 'prevBidSize', 'prevAskSize','volume','open','high','low','close']
    marketData = []
    data = []
    with open('livedata_3.csv', 'w', encoding='UTF8', newline='') as f:
        writer = csv.writer(f)

        # write the header
        writer.writerow(header)
         
        while True: 
            if not queue:
                break
            md = queue.pop(0) 
            # write the data
            writer.writerow([md.time,md.bid, md.bidSize, md.ask, md.askSize, md.last, md.lastSize, md.prevBidSize, md.prevAskSize, md.volume, md.open, md.high, md.low, md.close])
    condition.notify()
    condition.release()
    print("Notify onPendingTicker()")
    condition.wait()

ib.run()