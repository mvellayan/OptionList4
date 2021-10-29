from ib_insync import *
from pprint import pprint
from lib import FileUtil, IBUtil
import sys

# from ibapi.client import EClient
# from ibapi.wrapper import EWrapper
# from ibapi.common import *
# from ibapi.contract import *
# from ContractSamples import ContractSamples


class TestApp(EClient, EWrapper):
    def __init__(self):
        EClient.__init__(self, self)

    def nextValidId(self, orderId:int):
        print("id", orderId)
        contract = Contract()
        contract.symbol = "IBKR"
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "USD"
        contract.primaryExchange = "NASDAQ"

        self.reqContractDetails(10, contract)

    def error(self, reqId:TickerId, errorCode:int, errorString:str):
        print("Error: ", reqId, "", errorCode, "", errorString)

    def contractDetails(self, reqId:int, contractDetails:ContractDetails):
        print("contractDetail: ", reqId, " ", contractDetails)

    def contractDetailsEnd(self, reqId:int):
        print("end, disconnecting")
        self.disconnect()

def main():
    app = TestApp()

    app.connect("127.0.0.1", 4002, 0)
    app.run()

if __name__ == "__main__":
    main()