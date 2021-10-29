from ib_insync import *
from pprint import pprint
from lib import FileUtil, IBUtil
import sys


class TestApp():

    def error( reqId, errorCode, errorString):
        print("Error: ", reqId, "", errorCode, "", errorString)

    def contractDetails(reqId, contractDetails):
        print("contractDetail: ", reqId, " ", contractDetails)

    def contractDetailsEnd( reqId):
        print("end, disconnecting")
        self.disconnect()

    def contractDetails( reqId: int, contractDetails: ContractDetails):
        print("contractDetail: ", reqId, " ", contractDetails)

    def contractDetailsEnd( reqId: int):
        print("end.")
        return

    def pull(self, config):
        ib = IB()
        ib.connect('127.0.0.1', config["tws_port"], clientId=101)
        ib.sleep(3)
        stock = Stock('AAPL', 'SMART', 'USD')
        ib.reqContractDetails(stock)
        ib.run(10)


def main(configFileName):
    global config
    config = FileUtil.readConfig(configFileName)
    app = TestApp()
    app.pull(config)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\n\nUsage: collect_data.py <config_file.yml>\n\n")
        sys.exit(0)
    else:
        print("using config file [" + sys.argv[1] + "]")

    main(sys.argv[1])