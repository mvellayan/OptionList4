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

# import xgboost as xgb
from xgboost.sklearn import XGBClassifier

from sklearn.metrics import accuracy_score
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import GridSearchCV

from utils import FileUtil
from utils.FileUtil import print_missing_cols

delta_labels = ["p5s", "p15s", "p30s", "p60s", "p300s", "p600s", "n5s", "n15s", "n30s", "n60s", "n300s", "n600s"]
delta_values = [5, 15, 30, 60, 300, 600, -5, -15, -30, -60, -300, -600]
delta_quarts = [3, 3, 5, 5, 7, 7, 3, 3, 5, 5, 7, 7]
bucket_labels = []
for s in delta_labels:
    bucket_labels.append(s + "_bucket")

# needed_cols = ['bid_size', 'ask_size', 'last_size', 'bid_ask_delta', 'c_w1_n3_ask', 'c_w1_n3_bid', 'c_w1_n3_last', 'c_w1_n3_last_size', 'c_w1_n3_time_value', 'c_w1_n3_theta', 'c_w1_n2_ask', 'c_w1_n2_bid', 'c_w1_n2_last', 'c_w1_n2_last_size', 'c_w1_n2_time_value', 'c_w1_n2_theta', 'c_w1_n1_ask', 'c_w1_n1_bid', 'c_w1_n1_last', 'c_w1_n1_last_size', 'c_w1_n1_time_value', 'c_w1_n1_theta', 'c_w1_p1_ask', 'c_w1_p1_bid', 'c_w1_p1_last', 'c_w1_p1_last_size', 'c_w1_p1_time_value', 'c_w1_p1_theta', 'c_w1_p2_ask', 'c_w1_p2_bid', 'c_w1_p2_last', 'c_w1_p2_last_size', 'c_w1_p2_time_value', 'c_w1_p2_theta', 'c_w1_p3_ask', 'c_w1_p3_bid', 'c_w1_p3_last', 'c_w1_p3_last_size', 'c_w1_p3_time_value', 'c_w1_p3_theta', 'c_w2_n3_ask', 'c_w2_n3_bid', 'c_w2_n3_last', 'c_w2_n3_last_size', 'c_w2_n3_time_value', 'c_w2_n3_theta', 'c_w2_n2_ask', 'c_w2_n2_bid', 'c_w2_n2_last', 'c_w2_n2_last_size', 'c_w2_n2_time_value', 'c_w2_n2_theta', 'c_w2_n1_ask', 'c_w2_n1_bid', 'c_w2_n1_last', 'c_w2_n1_last_size', 'c_w2_n1_time_value', 'c_w2_n1_theta', 'c_w2_p1_ask', 'c_w2_p1_bid', 'c_w2_p1_last', 'c_w2_p1_last_size', 'c_w2_p1_time_value', 'c_w2_p1_theta', 'c_w2_p2_ask', 'c_w2_p2_bid', 'c_w2_p2_last', 'c_w2_p2_last_size', 'c_w2_p2_time_value', 'c_w2_p2_theta', 'c_w2_p3_ask', 'c_w2_p3_bid', 'c_w2_p3_last', 'c_w2_p3_last_size', 'c_w2_p3_time_value', 'c_w2_p3_theta', 'c_w3_n3_ask', 'c_w3_n3_bid', 'c_w3_n3_last', 'c_w3_n3_last_size', 'c_w3_n3_time_value', 'c_w3_n3_theta', 'c_w3_n2_ask', 'c_w3_n2_bid', 'c_w3_n2_last', 'c_w3_n2_last_size', 'c_w3_n2_time_value', 'c_w3_n2_theta', 'c_w3_n1_ask', 'c_w3_n1_bid', 'c_w3_n1_last', 'c_w3_n1_last_size', 'c_w3_n1_time_value', 'c_w3_n1_theta', 'c_w3_p1_ask', 'c_w3_p1_bid', 'c_w3_p1_last', 'c_w3_p1_last_size', 'c_w3_p1_time_value', 'c_w3_p1_theta', 'c_w3_p2_ask', 'c_w3_p2_bid', 'c_w3_p2_last', 'c_w3_p2_last_size', 'c_w3_p2_time_value', 'c_w3_p2_theta', 'c_w3_p3_ask', 'c_w3_p3_bid', 'c_w3_p3_last', 'c_w3_p3_last_size', 'c_w3_p3_time_value', 'c_w3_p3_theta', 'n5s_delta', 'n15s_delta', 'n30s_delta', 'n60s_delta']]
# needed_cols = ['c_w1_n1_time_value', 'c_w1_n1_theta', 'c_w1_n2_time_value', 'c_w1_n2_theta', 'c_w1_n3_time_value', 'c_w1_n3_theta', 'c_w1_p1_time_value', 'c_w1_p1_theta', 'c_w1_p2_time_value', 'c_w1_p2_theta', 'c_w1_p3_time_value', 'c_w1_p3_theta', 'c_w2_n1_time_value', 'c_w2_n1_theta', 'c_w2_n2_time_value', 'c_w2_n2_theta', 'c_w2_n3_time_value', 'c_w2_n3_theta', 'c_w2_p1_time_value', 'c_w2_p1_theta', 'c_w2_p2_time_value', 'c_w2_p2_theta', 'c_w2_p3_time_value', 'c_w2_p3_theta', 'c_w3_n1_time_value', 'c_w3_n1_theta', 'c_w3_n2_time_value', 'c_w3_n2_theta', 'c_w3_n3_time_value', 'c_w3_n3_theta', 'c_w3_p1_time_value', 'c_w3_p1_theta', 'c_w3_p2_time_value', 'c_w3_p2_theta', 'c_w3_p3_time_value', 'c_w3_p3_theta', 'n5s_delta', 'n15s_delta', 'n30s_delta', 'n60s_delta']
needed_cols = ['c_w1_n1_theta',  'c_w1_n2_theta',  'c_w1_n3_theta',  'c_w1_p1_theta',  'c_w1_p2_theta',  'c_w1_p3_theta',  'c_w2_n1_theta',  'n5s_delta', 'n15s_delta', 'n30s_delta', 'n60s_delta']

def build_xgb_model(in_data_file, out_model_file, X_columns, y_column):

    # expecting a list of comma seperated files.
    if type(in_data_file) is not list:
        in_data_file = in_data_file.split(",")

    data = None
    for file in in_data_file:
        assert os.path.exists(file), "Data file does not exist!"
        data_tmp = pd.read_csv(file, low_memory=False)
        if data is None:
            data = data_tmp
        else:
            data = data.append(data_tmp, ignore_index=True)

    try:
        # have_cols = [value for value in X_columns if value in list(data.columns)]
        have_cols = [value for value in X_columns]
        if type(y_column) is list:
            have_cols += y_column
        else:
            have_cols.append(y_column)
        have_cols.append("time")
        X = data[have_cols]
        no_rows = X.shape[0]
        X = X.dropna(axis=0, inplace=False)
        no_na_rows = X.shape[0]
        X['hour'] = X['time'].astype(str).str.slice(0, 10)
        df_by_hour = X.groupby('hour').count()

        y = X[y_column].to_frame()
        X = X.drop([y_column], axis=1, inplace=False)
        X = X.drop(['hour'], axis=1, inplace=False)
        X = X.drop(['time'], axis=1, inplace=False)

        if X.shape[0] == 0:
            print(f"Skipping.  file {in_data_file} No qualified data!")
            raise Exception("No data in file.")

    except KeyError as e:
        print("********************************************************")
        print(e)
        print(f" cant find all cols for file {in_data_file}")
        print_missing_cols(X_columns, list(data.columns))
        raise Exception("MissingColumns.")

    # X_train, X_test, y_train, y_test = train_test_split(X, Y, test_size=0.2, random_state=42)

    # grid search URL: https://towardsdatascience.com/fine-tuning-xgboost-model-257868cf4187
    q_idx = delta_labels.index(y_column.replace("_bucket", ""))
    bin_counts = delta_quarts[q_idx]

    params = {
        'copy_X': True,
        'fit_intercept': False,
        'normalize': True,
        '_kfold': 5,
        # 'objective': 'validation:accuracy',
        'objective': 'multi:softprob',
        'enable_categorical': True,
        '_tuning_objective_metric': 'validation:f1',
        'eval_metric': 'auc',
        # 'eval_metric': 'accuracy,f1',
        # 'eval_metric':'merror',
        # 'eval_metric': 'accuracy,f1X',
        # Muthu params
        'subsample': 0.75,  # Setting it to 0.5 means that XGBoost would randomly sample half of the training data prior to growing trees. and this will prevent overfitting.
        'gamma': 0.0001, # Minimum loss reduction required to make a further partition on a leaf node of the tree. The larger gamma is, the more conservative the algorithm will be
        'alpha': 1.0, # L1 regularization is Lasso Regression wich adds “squared magnitude” of coefficient as penalty term to the loss functi
        'lambda': 0.0, # L2 regularization is Ridge Regression which adds “absolute value of magnitude” of coefficient as penalty term to the loss function.
        'eta': 0.03, # Step size shrinkage used in update to prevents overfitting
        'min_child_weight': 0.005, # Minimum sum of instance weight (hessian) needed in a child the building process will give up further partitioning.
        'num_class': bin_counts,
        # not too sure.
        'max_depth': 10,  # Maximum tree depth for base learners.
        'early_stopping_rounds': 10,  # don't over fit
        'num_round': 100  # num_boost_round == num_boost_round
    }
    # 'colsample_bytree' : 0.5781314251524922,            #on hold
    # 'min_child_weight' : 1.0421388863448751e-05
    # 'num_round': 736,
    # 'subsample' : 0.928443173145351
    # 'Xgamma': 0.10919583822903917   ## what is this??

    xgb = XGBClassifier(**params)
    y_values = y.values
    y_values_ravel = y_values.ravel()
    xgb.fit(X, y_values_ravel)
    # pred = xgb.predict(X_test)
    # categories = y[y_column].unique().tolist()

    # frog_cm = confusion_matrix(y_test, pred)
    # frog_cm_pct = frog_cm.astype('float') / frog_cm.sum(axis=1)[:, np.newaxis]

    # np.set_printoptions(precision=2)
    from numpy import sort

    # features = pd.DataFrame()
    # features['name'] = xgb.get_booster().feature_names
    # features['importance'] = xgb.feature_importances_
    # features.columns =['name', 'importance']
    # features.sort_values(by=['importance'], ascending=False, inplace=True)
    # ctr = 0
    # for i in features.itertuples():
    #     features.at[i.Index, 'rank'] = 'rank ' + str(round(ctr))
    #     features.at[i.Index, 'index'] = str(int(i.Index))
    #      ctr += 1
    #
    # pd.set_option('display.max_rows', 200)
    # with open(results_file, 'w') as out_file:
    #     with redirect_stdout(out_file):
    #         print(f"XGB Model Created at: { datetime.now().strftime('%m-%d-%Y %H:%M:%S')}")
    #         print("\n\n")
    #         print(xgb)
    #         print("\n\n")
    #         print(f"Overall Accuracy: {accuracy_score( y_test, pred ):.3f}")
    #         print("\n\n")
    #         print(classification_report(y_test, pred, target_names=categories))
    #         print("\n\n")
    #         print(frog_cm)
    #         print("\n\n")
    #         print(frog_cm_pct)
    #         print("Column Priority    -------------------------------------------------------")
    #         print(features)
    #         print("-------------------------------------------------------------------------")
    #         # summarize feature importance
    xgb.save_model(out_model_file)
    return xgb, no_rows, no_na_rows, df_by_hour

if __name__ == "__main__":
    config = FileUtil.readConfig(sys.argv[1])
    data_dir = os.getcwd() + "/" + config["ml18"]["data_dir"] + "/"
    search_mask1 = data_dir + "/" + "ml_*.csv"
    print(search_mask1)
    for data_file in glob.glob(search_mask1):
        print(data_file)
        model_file = data_file.replace(".csv", "_p5.json")
        build_xgb_model(in_data_file=data_file,  out_model_file=model_file, X_columns=needed_cols, y_column="p5s_bucket")
        model_file = data_file.replace(".csv", "_p15.json")
        build_xgb_model(in_data_file=[data_file], out_model_file=model_file,  X_columns=needed_cols, y_column="p15s_bucket")
        model_file = data_file.replace(".csv", "_p30.json")
        build_xgb_model(in_data_file=[data_file],  out_model_file=model_file,  X_columns=needed_cols, y_column="p30s_bucket")
        model_file = data_file.replace(".csv", "_p60.json")
        build_xgb_model(in_data_file=[data_file],  out_model_file=model_file,  X_columns=needed_cols, y_column="p60s_bucket")
