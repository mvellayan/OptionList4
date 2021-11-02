#https://ib-insync.readthedocs.io/recipes.html
import datetime
from ib_insync import *
from pprint import  pprint


def getHistoricStock(ib, contract):
    dt = ''
    barsList = []
    while True:
        bars = ib.reqHistoricalData(
            contract,
            endDateTime=dt,
            durationStr='1 D',
            barSizeSetting='1 min',
            whatToShow='MIDPOINT',
            useRTH=True,
            formatDate=1)
        if not bars:
            break
        barsList.append(bars)
        dt = bars[0].date
        print(dt)
    return  barsList


def getContractDetails(ib, contract):
    cd = ib.reqContractDetails(contract)[0]
    pprint(cd)

    # rules = [
    #     ib.reqMarketRule(ruleId)
    #     for ruleId in cd.marketRuleIds.split(',')]
    # pprint(rules)


def getOptionDetails(ib, contract):
    cd = ib.reqOptionDetails(contract)[0]
    pprint(cd)

def main(ib):

    contract = Stock('TSLA', 'SMART', 'USD')
    getContractDetails(ib, contract)

    getOptionDetails(ib, contract)

    #barsList = getHistoricStock(ib, contract)
    #allBars = [b for bars in reversed(barsList) for b in bars]
    #df = util.df(allBars)
    #df.to_csv(contract.symbol + '.csv', index=False)



if __name__ == "__main__":
    ib = IB()
    ib.connect('127.0.0.1', 4002, clientId=1)

    main(ib)


