from pprint import pprint
import pytz
from timeit import default_timer as timer
from datetime import timedelta

# from utils import FileUtil, IBUtil
# from utils.FileUtil import makeDirectory, unzip_file, get_sec_to_expire, setup_logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

src = 'https://vellayan.s3.amazonaws.com/modeling-data/projection_stock_call_options_AAPL-w1.xlsx'
#src = 'graph/projection_stock_call_options_AAPL-w1.xlsx'
pdxl = pd.read_excel(src,sheet_name="Sheet1", index_col=0, nrows=100)


toGraph = pdxl[['c_w1_n3_timeValue',	'c_w1_n2_timeValue','c_w1_n1_timeValue','c_w1_p1_timeValue','c_w1_p2_timeValue','c_w1_p3_timeValue','c_w2_n3_timeValue','c_w2_n2_timeValue','c_w2_n1_timeValue','c_w2_p1_timeValue','c_w2_p2_timeValue','c_w2_p3_timeValue','c_w3_n3_timeValue','c_w3_n2_timeValue','c_w3_n1_timeValue','c_w3_p1_timeValue','c_w3_p2_timeValue','c_w3_p3_timeValue']].head(100)
toGraph.plot()
#fig,ax=plt.subplots()
#ax2=ax.twinx()
# make a plot with different y-axis using second axis object
#ax2.plot(pdxl['p300'], color="blue", marker="o")
#ax2.set_ylabel("Last, p300", color="blue", fontsize=14)
#
plt.show()
