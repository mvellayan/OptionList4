import argparse
import logging
import shutil
from contextlib import redirect_stdout
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
from sklearn.metrics import accuracy_score
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import GridSearchCV

import model_020_build_xgb_model
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


def expandX(row_arr, labels):
    label = find_label(row_arr, labels)
    retDict = {'prediction': label}
    return retDict

def find_label(prob, labels):
    if len(prob) != len(labels):
        print (f"labels =[{labels}] probabilities=[{prob}]")
        raise Exception("probability list size != labels list size")
    max_value = 0.0
    ctr = 0
    label = ""
    for p in prob:
        if p > max_value:
            max_value = p
            label = labels[ctr]
        ctr += 1
    return label


def out_write(msg: str):
    out_file = open(results_file, "a")
    out_file.write(msg)
    out_file.close()


def create_xgb_model(in_data_file, out_model_file, X_columns, y_column):
    try:
        xgb_l, no_rows, no_na_rows, df_by_hour = model_020_build_xgb_model.build_xgb_model\
            (in_data_file=in_data_file, out_model_file=out_model_file, X_columns=X_columns, y_column=y_column)
    except Exception("MissingColumns"):
        out_write(
            f"|<div  style='background-color:red'>>Some of the needed cols are missing </div>| {list(set(X_columns))}|\n\n\n")
        return

    out_write(f"<h1 style='background-color:#b2691f'>Model Specs {datetime.now().strftime('%m-%d-%Y %H:%M:%S')}</h1>\n\n")
    out_write("|Attributes|Values|\n|-|-|\n")
    out_write(f"|Model file(s)|{',</br> '.join(in_data_file)}\n")
    out_write(f"|Model row count|<h4>{no_na_rows:,} nn /  {no_rows:,} total rows</h4>|\n")
    # out_write(f"|X columns|{'<br/>'.join(X_columns)}|\n")
    # out_write(f"|y column|{y_column}|\n")

    # dfs = "<table>"
    # for index, row in df_by_hour.iterrows():
    #     time_int = row["time"].item()
    #     dfs += f"<tr><td>{index}</td><td> {time_int:,} </td></tr>"
    # dfs += "</table>"

    features = pd.DataFrame()
    features['name'] = xgb_l.get_booster().feature_names
    features['importance'] = xgb_l.feature_importances_
    features.columns = ['name', 'importance']
    features.sort_values(by=['importance'], ascending=False, inplace=True)

    ctr = 0
    for i in features.itertuples():
        features.at[i.Index, 'rank'] = 'rank ' + str(round(ctr))
        features.at[i.Index, 'index'] = str(int(i.Index))
        ctr += 1

    out_write("\n\n<table><tr><th>Rows by Hour</th><th>Feature Importance</th></tr>")

    out_write("\n\n<tr><td>")
    out_write(f"{df_by_hour['time'].to_frame().to_html()}\n")

    out_write("\n\n</td><td>")
    out_write(f"y column: <h3>{y_column}</h3>|\n")
    out_write(f"{features.to_html()}")

    i = 1
    str_arr = xgb_l.__str__().split(",")
    for st in str_arr:
        out_write(f" {st.strip()}, &emsp;")
        i += 1
    out_write("\n\n</td></tr></table>\n\n")
    return xgb_l


def test_fit(xgb_l, test_file_ctr_l, test_file_l, X_columns, y_column):
    out_write("<hr style = 'background-color:blue' />")
    out_write(f"<h1 style='background-color:#b2b21f'>Test Data Specs # {test_file_ctr_l}</h1>\n\n")
    out_write("|Attributes|Values|\n|-|-|\n")
    test_data = pd.read_csv(test_file_l, low_memory=False)

    #out_write(f"|Model file(s)|{','.join(in_test_files)}\n")
    out_write(f"|Data file|{test_file_l}\n")

    try:
        have_cols = [value for value in X_columns if value in list(test_data.columns)]
        have_cols = [value for value in X_columns]  # error out, don't/can't use subset of cols
        have_cols.append(y_column)
        X = test_data[have_cols]
        no_rows = X.shape[0]
        X = X.dropna(axis=0, inplace=False)
        no_na_rows = X.shape[0]
        y = X[y_column].to_frame()
        X = X.drop([y_column], axis=1, inplace=False)

        if X.shape[0] == 0:
            out_write(f"|<div  style='background-color:red'>>Zero rows after dropna!</div>| {list(set(X_columns) - set(test_data.columns))}|\n")
            return

        if y[y_column][0] == 'NotEnoughValues':
            out_write(f"|<div  style='background-color:red'> NotEnoughValues for y </div> | {y_column} | \n")
            return

    except KeyError as e:
        print("********************************************************")
        out_write(f"|<div  style='background-color:red'>>Missing needed cols</div>| {list(set(X_columns) - set(test_data.columns))}\n\n\n")
        return

    # out_write(f"|X columns|{'<br/>'.join(have_cols)}|\n")
    out_write(f"|Test row count|<h4>{no_na_rows:,} nn /  {no_rows:,} total rows</h4>|\n")

    pred = xgb_l.predict(X)
    categories = y[y_column].unique().tolist()
    categories.sort()

    out_write(f"|Accuracy| <h4> {accuracy_score(y[y_column].ravel(), pred)}% </h4>|\n\n\n")

    # pred_df = pd.DataFrame(pred, columns=categories)
    pred_df = pd.DataFrame(pred, columns=["prediction"])
    # pred_df['prediction'] = pred_df.apply(lambda x: expandX(x.tolist(), categories), axis=1, result_type='expand')

    cm = confusion_matrix(pred_df['prediction'], y[y_column], labels=categories)
    cm_pd = pd.DataFrame(cm, index=categories, columns=categories)

    cm_pct = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
    cm_pct_pd = pd.DataFrame(cm_pct, index=categories, columns=categories)
    out_write("## Confusion Matrix\n\n")
    out_write("<table><tr><td>")
    out_write(f"{cm_pd.to_html()}")
    out_write("</td><td>")
    out_write(f"{cm_pct_pd.to_html()}")
    out_write("</td></tr></table>")

    np.set_printoptions(precision=2)
    from numpy import sort


results_file = None

def iterate_product(model_file_list, test_file_pattern, X_cols_list, y_col):
    global results_file
    #
    results_file = model_file_list[0].replace(".csv", "_" + FileUtil.getDateTimeStamp(1) + ".md")
    # set file names
    model_file = model_file_list[0].replace(".csv", "_" + FileUtil.getDateTimeStamp(1) + ".json")
    #
    # build model
    xgb_l = create_xgb_model(in_data_file=model_file_list, out_model_file=model_file,
                             X_columns=X_cols_list, y_column=y_col)
    #
    # run through test file(s).
    test_file_ctr = 1
    for test_file in sorted(glob.glob(test_file_pattern)):
        test_fit(xgb_l, test_file_ctr, test_file, X_columns=X_cols_list, y_column=y_col)
        test_file_ctr += 1
    out_write(f"#### Then end for: {model_file}\n\n")
    os.remove(model_file)


def plan_iterate_product():
    X_cols = [
        theta_pos,
        theta_neg,
        theta_pos_w1 + theta_pos_w2,
        theta_pos + theta_neg,

        n_buckets_short,
        n_buckets,
        theta_pos + n_buckets_short,
        theta_pos + theta_neg + n_buckets,
        theta_pos_w1 + theta_pos_w2 + n_buckets,

        theta_w1,
        theta_w2,
        theta_w1 + theta_w2,
        theta_w1 + theta_w2 + theta_w3,
        theta_w1 + theta_w2 + theta_w3 + n_buckets
    ]
    y_cols = [ 'p5s_bucket', 'p15s_bucket', 'p30s_bucket', 'p60s_bucket', 'p300s_bucket', 'p600s_bucket']
    model_file_list = ['ml_cp18/ml_cp18_AAPL20211124.csv', 'ml_cp18/ml_cp18_AAPL20211123.csv']
    test_file_pattern = "ml_cp18/ml_cp18_AAPL202111*.csv"

    index = 1
    for x_col in X_cols:
        for y_col in y_cols:
            print(index, x_col, y_col)
            iterate_product(model_file_list, test_file_pattern, x_col, y_col)
            index += 1
            # if index > 4:
            #     print ("STOPPING at 4 runs.")
            #     return


if __name__ == "__main__":

    # expecting a list of comma serperated files.
    pd.set_option('display.max_rows', 200)
    ## globals
    theta_neg_w1 = ['c_w1_n1_theta', 'c_w1_n2_theta', 'c_w1_n3_theta']
    theta_neg_w2 = ['c_w2_n1_theta', 'c_w2_n2_theta', 'c_w2_n3_theta']
    theta_neg_w3 = ['c_w3_n1_theta', 'c_w3_n2_theta', 'c_w3_n3_theta']

    theta_pos_w1 = ['c_w1_p1_theta', 'c_w1_p2_theta', 'c_w1_p3_theta']
    theta_pos_w2 = ['c_w2_p1_theta', 'c_w2_p2_theta', 'c_w2_p3_theta']
    theta_pos_w3 = ['c_w3_p1_theta', 'c_w3_p2_theta', 'c_w3_p3_theta']

    tv_neg_w1 = ['c_w1_n3_time_value', 'c_w1_n2_time_value', 'c_w1_n1_time_value']
    tv_neg_w2 = ['c_w2_n3_time_value', 'c_w2_n2_time_value', 'c_w2_n1_time_value']
    tv_neg_w3 = ['c_w3_n3_time_value', 'c_w3_n2_time_value', 'c_w3_n1_time_value']

    tv_pos_w1 = ['c_w1_p1_time_value', 'c_w1_p2_time_value', 'c_w1_p3_time_value']
    tv_pos_w2 = ['c_w2_p1_time_value', 'c_w2_p2_time_value', 'c_w2_p3_time_value']
    tv_pos_w3 = ['c_w3_p1_time_value', 'c_w3_p2_time_value', 'c_w3_p3_time_value']

    delta_short = ['n5s_delta', 'n15s_delta', 'n30s_delta', 'n60s_delta']
    delta_long = ['n300s_delta', 'n600s_delta']
    n_buckets_short = ['n5s_bucket', 'n15s_bucket', 'n30s_bucket', 'n60s_bucket']
    n_buckets_long = ['n300s_bucket', 'n600s_bucket']

    # derived lists
    theta_w1 = theta_neg_w1 + theta_pos_w1
    theta_w2 = theta_neg_w2 + theta_pos_w2
    theta_w3 = theta_neg_w3 + theta_pos_w3
    theta_pos = theta_pos_w1 + theta_pos_w2 + theta_pos_w3
    theta_neg = theta_neg_w1 + theta_neg_w2 + theta_neg_w3

    tv_w1 = tv_neg_w1 + tv_pos_w1
    tv_w2 = tv_neg_w2 + tv_pos_w2
    tv_w3 = tv_neg_w3 + tv_pos_w3

    delta = delta_short + delta_long
    n_buckets = n_buckets_short + n_buckets_long

    plan_iterate_product()

