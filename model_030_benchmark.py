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
Outline of functionality:
# 1. Validate parameters
#       load model
#       load test data file
# 2. Build hashmap of test-file by time, for search performance reasons
# 3. Simulate trade & build data model
# 5. Print Stat 1: Confusion Matrix Expected vs Actual
# 6. Report Summary / Detail
'''


logging.basicConfig(level=logging.ERROR)
log = logging.getLogger("myLogger")
log.setLevel(logging.INFO)
pd.set_option('display.max_rows', 15)
pd.set_option('display.width', 150)
pd.set_option('display.max_columns', 10)


def plot_confusion_matrix(cm, classes, normalized=True, cmap='bone', fmt='g'):
    plt.figure(figsize=[7, 6])
    norm_cm = cm
    if normalized:
        norm_cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
        sns.heatmap(norm_cm, annot=cm, fmt=fmt, xticklabels=classes, yticklabels=classes, cmap=cmap)


def expandX(p0, p1, p2, p3, p4, p5, p6, labels):
    arr1 = [p0,  p1, p2, p3, p4, p5, p6]
    label = find_label(arr1, labels)
    retDict = {'prediction': label}
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


def main(test_file, model_file):

    needed_cols = ['bid_size', 'ask_size', 'last_size', 'volume',  'bid_ask_delta',  'c_w1_n3_ask', 'c_w1_n3_bid', 'c_w1_n3_last', 'c_w1_n3_last_size',  'c_w1_n3_time_value',  'c_w1_n3_theta',  'c_w1_n2_ask',  'c_w1_n2_bid',  'c_w1_n2_last',  'c_w1_n2_last_size',  'c_w1_n2_time_value',  'c_w1_n2_theta',  'c_w1_n1_ask',  'c_w1_n1_bid',  'c_w1_n1_last',  'c_w1_n1_last_size',  'c_w1_n1_time_value',  'c_w1_n1_theta',  'c_w1_p1_ask',  'c_w1_p1_bid',  'c_w1_p1_last',  'c_w1_p1_last_size',  'c_w1_p1_time_value',  'c_w1_p1_theta',  'c_w1_p2_ask',  'c_w1_p2_bid',  'c_w1_p2_last',  'c_w1_p2_last_size',  'c_w1_p2_time_value',  'c_w1_p2_theta',  'c_w1_p3_ask',  'c_w1_p3_bid',  'c_w1_p3_last',  'c_w1_p3_last_size',  'c_w1_p3_time_value',  'c_w1_p3_theta',  'c_w2_n3_ask',  'c_w2_n3_bid',  'c_w2_n3_last',  'c_w2_n3_last_size',  'c_w2_n3_time_value',  'c_w2_n3_theta',  'c_w2_n2_ask',  'c_w2_n2_bid',  'c_w2_n2_last',  'c_w2_n2_last_size',  'c_w2_n2_time_value',  'c_w2_n2_theta',  'c_w2_n1_ask',  'c_w2_n1_bid',  'c_w2_n1_last',  'c_w2_n1_last_size',  'c_w2_n1_time_value',  'c_w2_n1_theta',  'c_w2_p1_ask',  'c_w2_p1_bid',  'c_w2_p1_last',  'c_w2_p1_last_size',  'c_w2_p1_time_value',  'c_w2_p1_theta',  'c_w2_p2_ask',  'c_w2_p2_bid',  'c_w2_p2_last',  'c_w2_p2_last_size',  'c_w2_p2_time_value',  'c_w2_p2_theta',  'c_w2_p3_ask',  'c_w2_p3_bid',  'c_w2_p3_last',  'c_w2_p3_last_size',  'c_w2_p3_time_value',  'c_w2_p3_theta',  'c_w3_n3_ask',  'c_w3_n3_bid',  'c_w3_n3_last',  'c_w3_n3_last_size',  'c_w3_n3_time_value',  'c_w3_n3_theta',  'c_w3_n2_ask',  'c_w3_n2_bid',  'c_w3_n2_last',  'c_w3_n2_last_size',  'c_w3_n2_time_value',  'c_w3_n2_theta',  'c_w3_n1_ask',  'c_w3_n1_bid',  'c_w3_n1_last',  'c_w3_n1_last_size',  'c_w3_n1_time_value',  'c_w3_n1_theta',  'c_w3_p1_ask',  'c_w3_p1_bid',  'c_w3_p1_last',  'c_w3_p1_last_size',  'c_w3_p1_time_value',  'c_w3_p1_theta',  'c_w3_p2_ask',  'c_w3_p2_bid',  'c_w3_p2_last',  'c_w3_p2_last_size',  'c_w3_p2_time_value',  'c_w3_p2_theta',  'c_w3_p3_ask',  'c_w3_p3_bid',  'c_w3_p3_last',  'c_w3_p3_last_size',  'c_w3_p3_time_value', 'c_w3_p3_theta', 'p300s_bucket_category']

    # 1.0 load data, model
    data = pd.read_csv(test_file)
    try:
        have_cols = [value for value in needed_cols if value in list(data.columns)]
        X = data [have_cols]
        X.dropna(axis=0, inplace=True)
        Y = X['p300s_bucket_category'].to_frame()
        X.drop(['p300s_bucket_category'], axis=1, inplace=True)

    except KeyError as e:
        print (e)
        have_cols = list(data.columns)
        print(f"can find required values in file {test_file}")
        print(f"missing cols: {set(needed_cols) - set(have_cols)}")
        print(f"needed cols: {needed_cols}")
        print(f"have cols: {have_cols}")
        return

    # 2.0 cleanup ?
    #curPd = curPd[(curPd['time'] % 1000000).between(94500, 154500)]
    # data_X.assign(idx=lambda x: x.index)

    # 3. Run Inference Here
    ##
    categories = data.p300s_bucket_category.unique().tolist()
    categories = categories[:-1]

    xgb_model = xgb.Booster()
    xgb_model.load_model(model_file)
    model_features = xgb_model.feature_names
    print(f"missing cols in model: {set(model_features) - set(X.columns)}")

    X_dmatrix = xgb.DMatrix(X)
    y_pred = xgb_model.predict(X_dmatrix)
    y_pred_df = pd.DataFrame(y_pred, columns=categories)

    y_pred_df['prediction'] = y_pred_df.apply(lambda x:
                                expandX(x[0], x[1], x[2], x[3], x[4], x[5], x[6], categories),
                                axis=1, result_type='expand')
    y_pred_df['prediction_3'] = y_pred_df['prediction'].str[0:3]
    aaa = y_pred_df["prediction_3"].value_counts()

    # expanded_df = pd.concat([X, y_pred_df], axis=1)
    # expanded_df = pd.bind ### similar to concat

    Y['p300s_bucket_category_3'] = Y['p300s_bucket_category'].str[0:3]

    # cm = confusion_matrix(data['p300s_bucket_category'], y_pred_df['prediction'])
    # plot_confusion_matrix(cm, classes=categories, cmap='YlGnBu')
    # 4. print confusion matrix

    bbb = Y["p300s_bucket_category_3"].value_counts()
    cm = confusion_matrix(y_pred_df['prediction_3'], Y['p300s_bucket_category_3'])
    cm_pd = pd.DataFrame(cm, index=categories, columns=categories)

    cm_pct = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
    cm_pct_pd = pd.DataFrame(cm_pct, index=categories, columns=categories)

    print(cm_pd)
    print(cm_pct_pd)

    return
    # 5. Load pdOptionQuotesIdx -- Options Quotes
    pdOptionQuotesIdx = {}
    for index, row in curPd.iterrows():
        hash_idx = str(row.time)
        # print (index, '->', row, '==>', hash_idx)
        pdOptionQuotesIdx[hash_idx] = row


    #  3. loop through with trade runs
    #      a. run 1: buy: q6, sell: q4
    #      b. run 1: buy: q4,q5, q6, sell: q3
    #  Runs: Buy Stock, Call 1-6 (7 options)


if __name__ == "__main__":

    config = FileUtil.readConfig(sys.argv[1])
    model_file = os.getcwd() + "/" + sys.argv[2]
    test_file = os.getcwd() + "/" + sys.argv[3]
    assert os.path.exists(model_file), "Model file does not exist!"
    assert os.path.exists(test_file), "Test file does not exist!"

    main(test_file, model_file)

