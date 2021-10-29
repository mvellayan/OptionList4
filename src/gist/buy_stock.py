from ib_insync import *
import json
from pprint import pprint


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
    print(data["tws_port"], data["file_flush_seconds"], data["contracts"])
    print("\n")
    return data


def main():
    global config
    config = readConfig("config/config.json")

    ib = IB()
    ib.connect('127.0.0.1', config["tws_port"], clientId=101)

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

    for order in ib.orders():
        print("My stocks buy placed orders are ............................................")
        print(order)

    ib.run()

if __name__ == "__main__":
    main()



