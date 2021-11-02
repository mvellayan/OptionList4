import csv
import errno
import json
import math
import os
import re
import sys
import numpy as np
import pandas as pd

from datetime import datetime
from pprint import pprint
from threading import Condition
from utils import FileUtil, IBUtil

import pytz
from ib_insync import *


contract = Contract()
contract.symbol = "AAPL"
contract.secType = "OPT"
contract.exchange = "SMART"
contract.currency = "USD"

ib = IB()
ib.connect('127.0.0.1', 4002, clientId=10001)

fileName = "data/option_list_" + datetime.today().strftime("%Y%m%d") + '.csv'
if not os.path.exists(fileName):
    x = ib.reqContractDetails(contract)
    print(len(x))
    #arr = np.array()
    df = pd.DataFrame(columns=['secType', 'conId', 'symbol', 'lastTradeDateOrContractMonth', 'strike', 'right', 'localSymbol'])
    for obj in x:
        c = obj.contract
        df.loc[len(df)] = [c.secType, c.conId, c.symbol, c.lastTradeDateOrContractMonth, c.strike, c.right, c.localSymbol ]

    df.to_csv(fileName)
    #header='secType, conId, symbol, lastTradeDateOrContractMonth, strike, right, localSymbol')
else:
    print("cache file [" + fileName + "] already exists")





