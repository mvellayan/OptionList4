import argparse
import itertools
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

def out_write(msg: str):
    out_file = open(results_file, "a")
    out_file.write(msg)
    out_file.close()


def create_xgb_model(in_data_file, X_columns, y_column):
    try:
        xgb_l, no_rows, no_na_rows, df_by_hour = model_020_build_xgb_model.build_xgb_model\
            (in_data_file=in_data_file, X_columns=X_columns, y_column=y_column)
    except Exception("MissingColumns"):
        out_write(
            f"|<div  style='background-color:red'>>Some of the needed cols are missing </div>| {list(set(X_columns))}|\n\n\n")
        return

    row_count_table  = ""
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

    features_table = features.head(12).to_html(float_format='{:3.2f}'.format)

    row_count_table = df_by_hour['time'].to_frame().to_html()
    return xgb_l, features_table, row_count_table, no_rows, no_na_rows


def test_fit(xgb_l, test_file, X_columns, y_column):
    # out_write("<hr style = 'background-color:blue' />")

    test_data = pd.read_csv(test_file, low_memory=False)

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

        # if y[y_column][0] == 'NotEnoughValues':
        #     out_write(f"|<div  style='background-color:red'> NotEnoughValues for y </div> | {y_column} | \n")
        #     return

    except KeyError as e:
        out_write(f'ERROR: {e}')
        out_write(f"|<div  style='background-color:red'>>Missing needed cols</div>| {list(set(X_columns) - set(test_data.columns))}\n\n\n")
        return

    # out_write(f"|X columns|{'<br/>'.join(have_cols)}|\n")
    #out_write(f"|Test row count|<h4>{no_na_rows:,} nn /  {no_rows:,} total rows</h4>|\n")

    pred = xgb_l.predict(X)
    categories = y[y_column].unique().tolist()
    categories.sort()

    accuracy = accuracy_score(y[y_column].ravel(), pred)
    accuracy_str = f"{(accuracy_score(y[y_column].ravel(), pred)):.3f} %"

    # pred_df = pd.DataFrame(pred, columns=categories)
    pred_df = pd.DataFrame(pred, columns=["prediction"])

    cm = confusion_matrix(pred_df['prediction'], y[y_column], labels=categories)
    cm_pd = pd.DataFrame(cm, index=categories, columns=categories)

    cm_pct = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
    cm_pct_pd = pd.DataFrame(cm_pct, index=categories, columns=categories)
    # out_write(f"{cm_pd.to_html()}")
    cm_html = cm_pct_pd.to_html(float_format='{:3.2f}'.format)

    np.set_printoptions(precision=2)
    from numpy import sort

    return no_na_rows, no_rows, accuracy_str, cm_html


results_file = None

def create_table():
    global results_file
    X_sets = list(itertools.combinations(all_X, 4))  # 22c4 =7314; 22c3=1540, 22c5=26,334
    # permute X_cols

    ts = FileUtil.getDateTimeStamp(1)[:6]

    results_file = f"{model_file_list[0][:model_file_list[0].rfind('/')]}/run_{ts}.md"

    row = 0
    col = 0

    for x_set in X_sets:

        if row == 0:
            out_write('<table style="table, th, td { border: 1px solid black; border-radius: 10px;"}><tr><th>Features</th>')
            for c in y_cols:
                out_write(f"<th>{c}</th>")
            out_write("</tr>\n")
            row += 1

        out_write(f"<tr>")
        for y_col in y_cols:
            if col == 0:
                out_write(f"<td>{row}:  <br/> {x_set}</td>")
                col += 1

            xgb_l, features_table, row_count_table, no_rows, no_na_rows = create_xgb_model(
                in_data_file=model_file_list, X_columns=x_set, y_column=y_col)
            # run_no = f"{ts}_{index:03d}"
            no_na_rows, no_rows, accuracy_str, cm_html = test_fit(xgb_l, test_file, X_columns=x_set, y_column=y_col)
            #os.remove(model_file)

            out_write('<td><table style="table, th, td { border: 1px solid black; border-radius: 10px;}">\n')
            out_write(f"<tr>\n\t<td>Modeling Rows:  {no_na_rows:,} nn / {no_rows:,} total</td><td>Accuracy: {accuracy_str} {y_col} </tr>\n")
            out_write(f"<tr>\n\t<td>{features_table}</td>\n\t<td>{cm_html}</td>\n</tr>\n")
            out_write("</table></td>\n\n")
            col += 1
        out_write("</tr>")
        col = 0
        row += 1
    out_write("</table>")
    return


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

    deltas = ['n5s_delta', 'n15s_delta', 'n30s_delta', 'n60s_delta']

    y_cols = [ 'p5s_bucket', 'p15s_bucket', 'p30s_bucket', 'p60s_bucket']

    model_file_list = ['ml_cp18/ml_cp18_AAPL20220104.csv', 'ml_cp18/ml_cp18_AAPL20220106.csv']
    test_file = "ml_cp18/ml_cp18_AAPL20220105-test.csv"

    #n_buckets_short = ['n5s_bucket', 'n15s_bucket', 'n30s_bucket', 'n60s_bucket']
    # n_buckets_long = ['n300s_bucket', 'n600s_bucket']

    # derived lists
    theta_w1 = theta_neg_w1 + theta_pos_w1
    theta_w2 = theta_neg_w2 + theta_pos_w2
    theta_w3 = theta_neg_w3 + theta_pos_w3
    theta_pos = theta_pos_w1 + theta_pos_w2 + theta_pos_w3
    theta_neg = theta_neg_w1 + theta_neg_w2 + theta_neg_w3

    # n_buckets = n_buckets_short + n_buckets_long
    all_X = deltas + theta_neg + theta_pos

    create_table()

