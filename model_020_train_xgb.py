import argparse
import glob
import os
import sys
from datetime import datetime
from contextlib import redirect_stdout

import numpy as np # linear algebra
import pandas as pd # data processing, CSV file I/O (e.g. pd.read_csv)

import matplotlib.pylab as plt
import seaborn as sns

import xgboost as xgb
from xgboost.sklearn import XGBClassifier

from sklearn.metrics import accuracy_score
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import GridSearchCV

# x_cols = ['bid_size',  'ask_size',  'last_size',  'volume',  'bid_ask_delta',  'c_w1_n3_bid_ask_delta',  'c_w1_n3_ask', 'c_w1_n3_ask_size',  'c_w1_n3_bid',  'c_w1_n3_bid_size',  'c_w1_n3_last',  'c_w1_n3_last_size',  'c_w1_n3_strike_delta',  'c_w1_n3_time_value',  'c_w1_n3_theta',  'c_w1_n2_bid_ask_delta',  'c_w1_n2_ask',  'c_w1_n2_ask_size',  'c_w1_n2_bid',  'c_w1_n2_bid_size',  'c_w1_n2_last',  'c_w1_n2_last_size',  'c_w1_n2_strike_delta',  'c_w1_n2_time_value',  'c_w1_n2_theta',  'c_w1_n1_bid_ask_delta',  'c_w1_n1_ask',  'c_w1_n1_ask_size',  'c_w1_n1_bid',  'c_w1_n1_bid_size',  'c_w1_n1_last',  'c_w1_n1_last_size',  'c_w1_n1_strike_delta',  'c_w1_n1_time_value',  'c_w1_n1_theta',  'c_w1_p1_bid_ask_delta',  'c_w1_p1_ask',  'c_w1_p1_ask_size',  'c_w1_p1_bid',  'c_w1_p1_bid_size',  'c_w1_p1_last',  'c_w1_p1_last_size',  'c_w1_p1_strike_delta',  'c_w1_p1_time_value',  'c_w1_p1_theta',  'c_w1_p2_bid_ask_delta',  'c_w1_p2_ask',  'c_w1_p2_ask_size',  'c_w1_p2_bid',  'c_w1_p2_bid_size',  'c_w1_p2_last',  'c_w1_p2_last_size',  'c_w1_p2_strike_delta',  'c_w1_p2_time_value',  'c_w1_p2_theta',  'c_w1_p3_bid_ask_delta',  'c_w1_p3_ask',  'c_w1_p3_ask_size',  'c_w1_p3_bid',  'c_w1_p3_bid_size',  'c_w1_p3_last',  'c_w1_p3_last_size',  'c_w1_p3_strike_delta',  'c_w1_p3_time_value',  'c_w1_p3_theta',  'c_w2_n3_bid_ask_delta',  'c_w2_n3_ask',  'c_w2_n3_ask_size',  'c_w2_n3_bid',  'c_w2_n3_bid_size',  'c_w2_n3_last',  'c_w2_n3_last_size',  'c_w2_n3_strike_delta',  'c_w2_n3_time_value',  'c_w2_n3_theta',  'c_w2_n2_bid_ask_delta',  'c_w2_n2_ask',  'c_w2_n2_ask_size',  'c_w2_n2_bid',  'c_w2_n2_bid_size',  'c_w2_n2_last',  'c_w2_n2_last_size',  'c_w2_n2_strike_delta',  'c_w2_n2_time_value',  'c_w2_n2_theta',  'c_w2_n1_bid_ask_delta',  'c_w2_n1_ask',  'c_w2_n1_ask_size',  'c_w2_n1_bid',  'c_w2_n1_bid_size',  'c_w2_n1_last',  'c_w2_n1_last_size',  'c_w2_n1_strike_delta',  'c_w2_n1_time_value',  'c_w2_n1_theta',  'c_w2_p1_bid_ask_delta',  'c_w2_p1_ask',  'c_w2_p1_ask_size',  'c_w2_p1_bid',  'c_w2_p1_bid_size',  'c_w2_p1_last',  'c_w2_p1_last_size',  'c_w2_p1_strike_delta',  'c_w2_p1_time_value',  'c_w2_p1_theta',  'c_w2_p2_bid_ask_delta',  'c_w2_p2_ask',  'c_w2_p2_ask_size',  'c_w2_p2_bid',  'c_w2_p2_bid_size',  'c_w2_p2_last',  'c_w2_p2_last_size',  'c_w2_p2_strike_delta',  'c_w2_p2_time_value',  'c_w2_p2_theta',  'c_w2_p3_bid_ask_delta',  'c_w2_p3_ask',  'c_w2_p3_ask_size',  'c_w2_p3_bid',  'c_w2_p3_bid_size',  'c_w2_p3_last',  'c_w2_p3_last_size',  'c_w2_p3_strike_delta',  'c_w2_p3_time_value',  'c_w2_p3_theta',  'c_w3_n3_bid_ask_delta',  'c_w3_n3_ask',  'c_w3_n3_ask_size',  'c_w3_n3_bid',  'c_w3_n3_bid_size',  'c_w3_n3_last',  'c_w3_n3_last_size',  'c_w3_n3_strike_delta',  'c_w3_n3_time_value',  'c_w3_n3_theta',  'c_w3_n2_bid_ask_delta',  'c_w3_n2_ask',  'c_w3_n2_ask_size',  'c_w3_n2_bid',  'c_w3_n2_bid_size',  'c_w3_n2_last',  'c_w3_n2_last_size',  'c_w3_n2_strike_delta',  'c_w3_n2_time_value',  'c_w3_n2_theta',  'c_w3_n1_bid_ask_delta',  'c_w3_n1_ask',  'c_w3_n1_ask_size',  'c_w3_n1_bid',  'c_w3_n1_bid_size',  'c_w3_n1_last',  'c_w3_n1_last_size',  'c_w3_n1_strike_delta',  'c_w3_n1_time_value',  'c_w3_n1_theta',  'c_w3_p1_bid_ask_delta',  'c_w3_p1_ask',  'c_w3_p1_ask_size',  'c_w3_p1_bid',  'c_w3_p1_bid_size',  'c_w3_p1_last',  'c_w3_p1_last_size',  'c_w3_p1_strike_delta',  'c_w3_p1_time_value',  'c_w3_p1_theta',  'c_w3_p2_bid_ask_delta',  'c_w3_p2_ask',  'c_w3_p2_ask_size',  'c_w3_p2_bid',  'c_w3_p2_bid_size',  'c_w3_p2_last',  'c_w3_p2_last_size',  'c_w3_p2_strike_delta',  'c_w3_p2_time_value',  'c_w3_p2_theta',  'c_w3_p3_bid_ask_delta',  'c_w3_p3_ask',  'c_w3_p3_ask_size',  'c_w3_p3_bid',  'c_w3_p3_bid_size',  'c_w3_p3_last',  'c_w3_p3_last_size',  'c_w3_p3_strike_delta',  'c_w3_p3_time_value', 'c_w3_p3_theta' ]
from utils import FileUtil

x_cols = ['bid_size', 'ask_size', 'last_size', 'volume',  'bid_ask_delta',  'c_w1_n3_ask', 'c_w1_n3_bid', 'c_w1_n3_last', 'c_w1_n3_last_size',  'c_w1_n3_time_value',  'c_w1_n3_theta',  'c_w1_n2_ask',  'c_w1_n2_bid',  'c_w1_n2_last',  'c_w1_n2_last_size',  'c_w1_n2_time_value',  'c_w1_n2_theta',  'c_w1_n1_ask',  'c_w1_n1_bid',  'c_w1_n1_last',  'c_w1_n1_last_size',  'c_w1_n1_time_value',  'c_w1_n1_theta',  'c_w1_p1_ask',  'c_w1_p1_bid',  'c_w1_p1_last',  'c_w1_p1_last_size',  'c_w1_p1_time_value',  'c_w1_p1_theta',  'c_w1_p2_ask',  'c_w1_p2_bid',  'c_w1_p2_last',  'c_w1_p2_last_size',  'c_w1_p2_time_value',  'c_w1_p2_theta',  'c_w1_p3_ask',  'c_w1_p3_bid',  'c_w1_p3_last',  'c_w1_p3_last_size',  'c_w1_p3_time_value',  'c_w1_p3_theta',  'c_w2_n3_ask',  'c_w2_n3_bid',  'c_w2_n3_last',  'c_w2_n3_last_size',  'c_w2_n3_time_value',  'c_w2_n3_theta',  'c_w2_n2_ask',  'c_w2_n2_bid',  'c_w2_n2_last',  'c_w2_n2_last_size',  'c_w2_n2_time_value',  'c_w2_n2_theta',  'c_w2_n1_ask',  'c_w2_n1_bid',  'c_w2_n1_last',  'c_w2_n1_last_size',  'c_w2_n1_time_value',  'c_w2_n1_theta',  'c_w2_p1_ask',  'c_w2_p1_bid',  'c_w2_p1_last',  'c_w2_p1_last_size',  'c_w2_p1_time_value',  'c_w2_p1_theta',  'c_w2_p2_ask',  'c_w2_p2_bid',  'c_w2_p2_last',  'c_w2_p2_last_size',  'c_w2_p2_time_value',  'c_w2_p2_theta',  'c_w2_p3_ask',  'c_w2_p3_bid',  'c_w2_p3_last',  'c_w2_p3_last_size',  'c_w2_p3_time_value',  'c_w2_p3_theta',  'c_w3_n3_ask',  'c_w3_n3_bid',  'c_w3_n3_last',  'c_w3_n3_last_size',  'c_w3_n3_time_value',  'c_w3_n3_theta',  'c_w3_n2_ask',  'c_w3_n2_bid',  'c_w3_n2_last',  'c_w3_n2_last_size',  'c_w3_n2_time_value',  'c_w3_n2_theta',  'c_w3_n1_ask',  'c_w3_n1_bid',  'c_w3_n1_last',  'c_w3_n1_last_size',  'c_w3_n1_time_value',  'c_w3_n1_theta',  'c_w3_p1_ask',  'c_w3_p1_bid',  'c_w3_p1_last',  'c_w3_p1_last_size',  'c_w3_p1_time_value',  'c_w3_p1_theta',  'c_w3_p2_ask',  'c_w3_p2_bid',  'c_w3_p2_last',  'c_w3_p2_last_size',  'c_w3_p2_time_value',  'c_w3_p2_theta',  'c_w3_p3_ask',  'c_w3_p3_bid',  'c_w3_p3_last',  'c_w3_p3_last_size',  'c_w3_p3_time_value', 'c_w3_p3_theta']

def print_missing_cols(sought_cols, act_columns):
    print("\t missing: ", list(set(sought_cols) - set(act_columns)))
    print("\ttoo many:", list(set(act_columns) - set(sought_cols)))

def run_xg(file_name):
    file_name_json = file_name.replace(".csv", ".json")
    file_text_txt = file_name.replace(".csv", ".txt")

    if os.path.exists(file_name_json):
        print(f"Skipping.  file {file_name_json} exists!")
        return

    data = pd.read_csv(file_name)

    try:
        have_cols = [value for value in x_cols if value in list(data.columns)]
        have_cols.append('p300s_bucket_category')
        X = data [have_cols]
        X = X.dropna()
        Y = X['p300s_bucket_category'].to_frame()
        X.drop(['p300s_bucket_category'], axis=1, inplace=True)
        if X.shape[0] == 0:
            print(f"Skipping.  file {file_name_json} No qualified data!")
            return
    except KeyError as e:
        print("********************************************************")
        print(e)
        print(f" cant find all cols for file {file_name}")
        print_missing_cols(x_cols, list(data.columns))
        return



    X15_train, X15_test, y15_train, y15_test = train_test_split(X, Y, test_size=0.2, random_state=42)

    # From Sagemaker tuning
    parameters = {'_kfold': '5',
              '_tuning_objective_metric': 'validation:accuracy',
              'objective': 'validation:accuracy',

              'alpha': 0.029064625217569095,
              'colsample_bytree': 0.5300674649920706,
              'eta': 0.06785230577839381,
              'eval_metric': 'accuracy,f1',
              'gamma': 8.822571607235765e-06,
              'lambda': 2.236266181542945e-06,
              'max_depth': 8,
              'min_child_weight': 5.3334410483799005e-05,
              'num_class': 9,
              'num_round': 855,
              'objective': 'multi:softprob',
              'subsample': 0.7607022674051444}

    xgb15 = XGBClassifier(objective='multi:softprob', eval_metric='merror',
                      gamma=0.000008822571607235765,  # 8.822571607235765e-06,
                      min_child_weight=5.3334410483799005e-05,
                      num_class=7,
                      # 'lambda'=0.000002236266181542945, #2.236266181542945e-06,
                      max_depth=8
                      )

    xgb15.fit(X15_train, y15_train)

    pred = xgb15.predict(X15_test)

    categories = Y.p300s_bucket_category.unique().tolist()

    frog_cm = confusion_matrix(y15_test, pred)
    frog_cm_pct = frog_cm.astype('float') / frog_cm.sum(axis=1)[:, np.newaxis]

    np.set_printoptions(precision=2)
    from numpy import sort

    features = pd.DataFrame()
    features['name'] = xgb15.get_booster().feature_names
    features['importance'] = xgb15.feature_importances_
    features.columns =['name','importance']
    features.sort_values(by=['importance'], ascending=False, inplace=True)
    print(features.head(20))
    ctr = 0
    for i in features.itertuples():
        features.at[i.Index, 'rank'] = 'rank ' + str(round(ctr))
        features.at[i.Index, 'index'] = str(int(i.Index))
        ctr += 1

    pd.set_option('display.max_rows', 200)
    with open(file_text_txt, 'w') as out_file:
        with redirect_stdout(out_file):
            print(f"XGB Model Created at: { datetime.now().strftime('%m-%d-%Y %H:%M:%S')}")
            print("\n\n")
            print(xgb15)
            print("\n\n")
            print(f"Overall Accuracy: {accuracy_score( y15_test, pred ):.3f}")
            print("\n\n")
            print(classification_report(y15_test, pred, target_names=categories))
            print("\n\n")
            print(frog_cm)
            print("\n\n")
            print(frog_cm_pct)
            print("Column Priority    -------------------------------------------------------")
            print(features)
            print("-------------------------------------------------------------------------")
            # summarize feature importance
    xgb15.save_model(file_name_json)


if __name__ == "__main__":
    config = FileUtil.readConfig(sys.argv[1])
    data_dir = os.getcwd() + "/" + config["ml18"]["data_dir"] + "/"
    search_mask1 = data_dir + "/" + "ml_*.csv"
    print(search_mask1)
    for f in glob.glob(search_mask1):
        print(f)
        run_xg(f)

