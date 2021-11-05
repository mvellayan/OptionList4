from ib_insync import *
from pprint import pprint
from utils import FileUtil, IBUtil
import sys

def main(configFileName):
    global config
    config = FileUtil.readConfig(configFileName)

    ib = IB()
    ib.connect('127.0.0.1', config["tws_port"], clientId=101)

    stock = Stock('AAPL', 'SMART', 'USD')

    order = MarketOrder('SELL', 5)

    trade = ib.placeOrder(stock, order)

    print(trade)

    def orderFilled(trade, fill):
        print("Stock sell order has filled:")
        print(trade)
        print(fill)

    trade.fillEvent += orderFilled

    ib.sleep(3)

    for order in ib.orders():
        print("My stocks sell placed orders are ............................................")
        print(order)

    ib.run()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\n\nUsage: collect_data.py <config_file.yml>\n\n")
        sys.exit(0)
    else:
        print("using config file [" + sys.argv[1] + "]")

    main(sys.argv[1])



