#https://www.reddit.com/r/algotrading/comments/doq19k/getting_options_chain_from_ib_api_using_ib_insync/
#https://ib-insync.readthedocs.io/recipes.html
#
import datetime
from ib_insync import *
from pprint import  pprint


def main(ib):

    contract = Stock('AAPL', 'SMART', 'USD')
    # reqSecDefOptParams
    # option = Option('AAPL', '20171215', 490, 'P', 'FTA', multiplier=100)
    option = Option("AAPL", "", "", "", "", 100)
    #details = ib.reqContractDetails(contract)
    details = ib.reqSecDefOptParams("AAPL", "" , "STK", 265598)
    pprint(details)

    #barsList = getHistoricStock(ib, contract)
    #allBars = [b for bars in reversed(barsList) for b in bars]
    #df = util.df(allBars)
    #df.to_csv(contract.symbol + '.csv', index=False)



if __name__ == "__main__":
    ib = IB()
    ib.connect('127.0.0.1', 4002, clientId=1)

    main(ib)


