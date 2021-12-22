import argparse
import logging
import shutil
from datetime import datetime, timedelta, date
import glob, sys, os
import pandas as pd
import numpy as np
from pprint import pprint
import pytz
from timeit import default_timer as timer
from datetime import timedelta
from xgboost.sklearn import XGBClassifier
import xgboost as xgb
from sklearn.metrics import classification_report, confusion_matrix
import matplotlib.pylab as plt
import seaborn as sns

from utils import FileUtil, IBUtil
from utils.FileUtil import makeDirectory, unzip_file, get_sec_to_expire, getDateStrFromPath

'''
Outline
# 0. parameters
    - model-file (json)
    - test-file (csv)
# 1. Read Files and report
##	 					Model Data 				Test Data
		Timestamp:
		FileName:
		Rows
#
# 2. Print Stat 1: Confusion Matrix Expected vs Actual
		q6	q5	q4	q3	q2	q1	q0
	q6	 .
	q5		.
	q4			.
	q3				.
	q2					.
	q1						.
	q0 							.
#
# 4. Build hashmap of test-file by time, for search performance reasons
# 5. Trade Report Summary
# 6. Trade Report Detail
		Enter, Exit, Count, aStock, mStock, xStock, aw1c1, mw1c1, xw1c1, 
		q6		q5		20		
		q6		q4
		q6		q3	
'''


logging.basicConfig(level=logging.ERROR)
log = logging.getLogger("myLogger")
log.setLevel(logging.INFO)


def plot_confusion_matrix(cm, classes, normalized=True, cmap='bone', fmt='g'):
    plt.figure(figsize=[7, 6])
    norm_cm = cm
    if normalized:
        norm_cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
        sns.heatmap(norm_cm, annot=cm, fmt=fmt, xticklabels=classes, yticklabels=classes, cmap=cmap)

def main(hfile):
    global config
    print(f"\nProcessing {hfile}")
    #  1. read data & add prediction column
    needed_cols = [
        'bid_size', 'ask_size', 'last_size', 'volume', 'bid_ask_delta',
        'c_w1_n3_bid_ask_delta', 'c_w1_n3_ask', 'c_w1_n3_ask_size', 'c_w1_n3_bid', 'c_w1_n3_bid_size',
        'c_w1_n3_last', 'c_w1_n3_last_size', 'c_w1_n3_strike_delta', 'c_w1_n3_time_value', 'c_w1_n3_theta',
        'c_w1_n2_bid_ask_delta', 'c_w1_n2_ask', 'c_w1_n2_ask_size', 'c_w1_n2_bid', 'c_w1_n2_bid_size',
        'c_w1_n2_last', 'c_w1_n2_last_size', 'c_w1_n2_strike_delta', 'c_w1_n2_time_value', 'c_w1_n2_theta',
        'c_w1_n1_bid_ask_delta', 'c_w1_n1_ask', 'c_w1_n1_ask_size', 'c_w1_n1_bid', 'c_w1_n1_bid_size',
        'c_w1_n1_last', 'c_w1_n1_last_size', 'c_w1_n1_strike_delta', 'c_w1_n1_time_value', 'c_w1_n1_theta',
        'c_w1_p1_bid_ask_delta', 'c_w1_p1_ask', 'c_w1_p1_ask_size', 'c_w1_p1_bid', 'c_w1_p1_bid_size',
        'c_w1_p1_last', 'c_w1_p1_last_size', 'c_w1_p1_strike_delta', 'c_w1_p1_time_value', 'c_w1_p1_theta',
        'c_w1_p2_bid_ask_delta', 'c_w1_p2_ask', 'c_w1_p2_ask_size', 'c_w1_p2_bid', 'c_w1_p2_bid_size',
        'c_w1_p2_last', 'c_w1_p2_last_size', 'c_w1_p2_strike_delta', 'c_w1_p2_time_value', 'c_w1_p2_theta',
        'c_w1_p3_bid_ask_delta', 'c_w1_p3_ask', 'c_w1_p3_ask_size', 'c_w1_p3_bid', 'c_w1_p3_bid_size',
        'c_w1_p3_last', 'c_w1_p3_last_size', 'c_w1_p3_strike_delta', 'c_w1_p3_time_value', 'c_w1_p3_theta',
        'c_w2_n3_bid_ask_delta', 'c_w2_n3_ask', 'c_w2_n3_ask_size', 'c_w2_n3_bid', 'c_w2_n3_bid_size',
        'c_w2_n3_last', 'c_w2_n3_last_size', 'c_w2_n3_strike_delta', 'c_w2_n3_time_value', 'c_w2_n3_theta',
        'c_w2_n2_bid_ask_delta', 'c_w2_n2_ask', 'c_w2_n2_ask_size', 'c_w2_n2_bid', 'c_w2_n2_bid_size',
        'c_w2_n2_last', 'c_w2_n2_last_size', 'c_w2_n2_strike_delta', 'c_w2_n2_time_value', 'c_w2_n2_theta',
        'c_w2_n1_bid_ask_delta', 'c_w2_n1_ask', 'c_w2_n1_ask_size', 'c_w2_n1_bid', 'c_w2_n1_bid_size',
        'c_w2_n1_last', 'c_w2_n1_last_size', 'c_w2_n1_strike_delta', 'c_w2_n1_time_value', 'c_w2_n1_theta',
        'c_w2_p1_bid_ask_delta', 'c_w2_p1_ask', 'c_w2_p1_ask_size', 'c_w2_p1_bid', 'c_w2_p1_bid_size',
        'c_w2_p1_last', 'c_w2_p1_last_size', 'c_w2_p1_strike_delta', 'c_w2_p1_time_value', 'c_w2_p1_theta',
        'c_w2_p2_bid_ask_delta', 'c_w2_p2_ask', 'c_w2_p2_ask_size', 'c_w2_p2_bid', 'c_w2_p2_bid_size',
        'c_w2_p2_last', 'c_w2_p2_last_size', 'c_w2_p2_strike_delta', 'c_w2_p2_time_value', 'c_w2_p2_theta',
        'c_w2_p3_bid_ask_delta', 'c_w2_p3_ask', 'c_w2_p3_ask_size', 'c_w2_p3_bid', 'c_w2_p3_bid_size',
        'c_w2_p3_last', 'c_w2_p3_last_size', 'c_w2_p3_strike_delta', 'c_w2_p3_time_value', 'c_w2_p3_theta',
        'c_w3_n3_bid_ask_delta', 'c_w3_n3_ask', 'c_w3_n3_ask_size', 'c_w3_n3_bid', 'c_w3_n3_bid_size',
        'c_w3_n3_last', 'c_w3_n3_last_size', 'c_w3_n3_strike_delta', 'c_w3_n3_time_value', 'c_w3_n3_theta',
        'c_w3_n2_bid_ask_delta', 'c_w3_n2_ask', 'c_w3_n2_ask_size', 'c_w3_n2_bid', 'c_w3_n2_bid_size',
        'c_w3_n2_last', 'c_w3_n2_last_size', 'c_w3_n2_strike_delta', 'c_w3_n2_time_value', 'c_w3_n2_theta',
        'c_w3_n1_bid_ask_delta', 'c_w3_n1_ask', 'c_w3_n1_ask_size', 'c_w3_n1_bid', 'c_w3_n1_bid_size',
        'c_w3_n1_last', 'c_w3_n1_last_size', 'c_w3_n1_strike_delta', 'c_w3_n1_time_value', 'c_w3_n1_theta',
        'c_w3_p1_bid_ask_delta', 'c_w3_p1_ask', 'c_w3_p1_ask_size', 'c_w3_p1_bid', 'c_w3_p1_bid_size',
        'c_w3_p1_last', 'c_w3_p1_last_size', 'c_w3_p1_strike_delta', 'c_w3_p1_time_value', 'c_w3_p1_theta',
        'c_w3_p2_bid_ask_delta', 'c_w3_p2_ask', 'c_w3_p2_ask_size', 'c_w3_p2_bid', 'c_w3_p2_bid_size',
        'c_w3_p2_last', 'c_w3_p2_last_size', 'c_w3_p2_strike_delta', 'c_w3_p2_time_value', 'c_w3_p2_theta',
        'c_w3_p3_bid_ask_delta', 'c_w3_p3_ask', 'c_w3_p3_ask_size', 'c_w3_p3_bid', 'c_w3_p3_bid_size',
        'c_w3_p3_last', 'c_w3_p3_last_size', 'c_w3_p3_strike_delta', 'c_w3_p3_time_value',
        'c_w3_p3_theta'
    ]

    data = pd.read_csv(hfile)

    data = data.dropna(axis=1)
    data.assign(idx=lambda x: x.index)
    try:
        data_X = data[needed_cols]
    except KeyError:
        print(f"can find required values in file {hfile}")
        return

    categories = data.p300s_bucket_category.unique().tolist()
    #  2. load model
    xgb_model = xgb.Booster()
    xgb_model.load_model('ml_notebooks/models/dec19-xgboost-20211220-123201.txt')

    data_X_dmatrix = xgb.DMatrix(data_X)
    y_pred = xgb_model.predict(data_X_dmatrix)
    y_pred_df = pd.DataFrame(y_pred, columns=categories)

    expanded_df = pd.concat( [ data_X, y_pred_df ], axis=1)
    # expanded_df = pd.bind ### similar to concat

    print(expanded_df)

    print(y_pred_df)

    y_pred_df = y_pred_df.apply(lambda x: expandX(x[0], x[1], x[2], x[3], x[4], x[5], x[6], categories),
                    axis=1, result_type='expand')
    print(y_pred_df)

    frog_cm = confusion_matrix(data['p300s_bucket_category'], y_pred_df['prediction'])
    plot_confusion_matrix(frog_cm, classes=categories, cmap='YlGnBu')

    #  3. loop through with trade runs
    #      a. run 1: buy: q6, sell: q4
    #      b. run 1: buy: q4,q5, q6, sell: q3
    #  Runs: Buy Stock, Call 1-6 (7 options)


def expandX(p0, p1, p2, p3, p4, p5, p6, labels):
    arr1 = [p0,  p1, p2, p3, p4, p5, p6]
    label = find_label(arr1, labels)
    retDict = {}
    ctr = 0
    for label in labels:
        retDict[label] = arr1[ctr]
        ctr += 1
    retDict['prediction'] = label
    return retDict


def find_label(prob, labels):
    if len(prob) != len(labels):
        print (f"labels =[{labels}] probabilities=[{prob}]")
        raise Exception("probability list size != labels list size")
    max = 0.0
    ctr = 0
    label = ""
    for p in prob:
        if p > max:
            max = p
            label = labels[ctr]
        ctr += 1
    return label

def collect_args() -> dict:
    """Collect arguments passed into the script

    Returns:
        dict: Arguments Object
    """
    parser = argparse.ArgumentParser(
        description='zips up data for a given stock')
    parser.add_argument('config', help='JSON file that contains all the configuration',
                        default="config.json", type=str)
    parser.add_argument('model_dir', help='Model file directory to scan.  Added to current path',
                        default="/IBdata/", type=str)
    retDict = parser.parse_args()

    if not retDict.model_dir.startswith("/"):
        retDict.model_dir = "/" + retDict.model_dir
    if not retDict.model_dir.endswith("/"):
        retDict.model_dir = retDict.model_dir + "/"

    return retDict


#

if __name__ == "__main__":

    args = collect_args()
    config = FileUtil.readConfig(args.config)
    data_dir = os.getcwd() + args.model_dir

    print("Main Scanning: " + data_dir)

    #search_mask1 = data_dir + "ml_*" + config["stock"] + '*.csv'
    search_mask1 = data_dir + "ml_*.csv"
    for f in glob.glob(search_mask1):
        #print (f)
        main(f)

