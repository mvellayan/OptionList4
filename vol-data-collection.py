from datetime import datetime
import time

from ib_insync import *
PARAM_STOCK = 'AAPL'

def writeToFile():
    global barsList, contract
    if len(barsList) == 0:
        return
    allBars = [b for bars in reversed(barsList) for b in bars]
    df = util.df(allBars)
    df.to_csv(contract.symbol + str(round(time.time())) + '.csv', index=False)
    barsList = []
    print("      Written to file.  Next dt = ", endDateTime )



ib = IB()
ib.connect('127.0.0.1', 7496, clientId=1)

contract = Stock(PARAM_STOCK, 'SMART', 'USD')
#contract = Contract(conId=13455763, symbol="VIX",secType="IND", exchange="CBOE", currency="USD", includeExpired=False)
endDateTime: datetime = datetime(2022, 9, 12, 14, 29, 55, 0) #  2022-08-25 12:59:59
endDateTime = ''
barsList = []
ctr_total = 0
MAX_DAYS = 200
while ctr_total < (13 * MAX_DAYS):  # 7 30min dur * MAX_DAYS days
    ctr_total += 1
    print(datetime.now(), 'Starting Request: ctr_total', ctr_total,  'next timestamp', endDateTime)
    bars = ib.reqHistoricalData(
        contract,
        endDateTime=endDateTime,
        durationStr='1800 S',
        barSizeSetting='1 secs',
        whatToShow='TRADES',  # 'MIDPOINT',
        useRTH=True,
        formatDate=1)
    if not bars:
        print("empty data returned for endDateTime",endDateTime)
        print("exiting =(")
        writeToFile()
        exit()
    barsList.append(bars)
    print("      Return count: ", len(bars), " for endDateTime: ", endDateTime, ' Next endDateTime: ', bars[0].date)
    endDateTime = bars[0].date
    ib.sleep(15)
    # flush to file every so often
    if (ctr_total % 10) == 0:
        writeToFile()
# final write to file
writeToFile()