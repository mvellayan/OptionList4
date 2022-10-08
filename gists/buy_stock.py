from ib_insync import *
from pprint import pprint
from utils import FileUtil, IBUtil
import sys

def main():

    ib = IB()
    ib.connect('192.168.1.211', "9999", clientId=101)
    stock = Stock('AAPL', 'SMART', 'USD')
    order = MarketOrder('BUY', 5)
    trade = ib.placeOrder(stock, order)

    print(trade)

    def orderFilled(trade, fill):
        print("Stock buy order has filled...........................................")
        print(trade)
        print(fill)

    trade.fillEvent += orderFilled

    ib.sleep(3)

    print('\nOrders size: ',  len(ib.orders()))
    for order in ib.orders():
        print("\tMy stocks buy placed orders are:")
        print("\t", order)

    ib.run()


if __name__ == "__main__":

    main()










