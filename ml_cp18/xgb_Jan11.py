import os
import sys

import mlflow
import mlflow.xgboost

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from IPython.display import display
from sklearn.feature_selection import mutual_info_regression

from xgboost.sklearn import XGBClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.metrics import recall_score, f1_score, precision_score, precision_recall_fscore_support
from sklearn.metrics import accuracy_score

plt.style.use("seaborn-whitegrid")
plt.rc("figure", autolayout=True)
plt.rc(
    "axes",
    labelweight="bold",
    labelsize="large",
    titleweight="bold",
    titlesize=14,
    titlepad=10,
)


def make_mi_scores(X, y, discrete_features):
    mi_scores = mutual_info_regression(X, y, discrete_features=discrete_features)
    mi_scores = pd.Series(mi_scores, name="MI Scores", index=X.columns)
    mi_scores = mi_scores.sort_values(ascending=False)
    return mi_scores


def load_data(file_list, x_cols_names, y_cols_names, data_type="data"):
    # Load Training Data
    from os.path import exists

    data = None
    ctr = 1
    for file in file_list:

        file_name = os.getcwd() + "/ml_cp18/data/" + file

        data_tmp = pd.read_csv(file_name, low_memory=False)
        mlflow.log_param( data_type + f" file {ctr}", file)
        ctr += 1
        if data is None:
            data = data_tmp
        else:
            data = data.append(data_tmp, ignore_index=True)

    msg = f"raw:  {data.shape}"

    all_cols = x_cols_names + y_cols_names
    data = data [ all_cols ]
    data = data.dropna()
    msg += f" na {data.shape}"

    X_features = data[x_cols]
    y_features = data[y_cols].astype('int')

    mlflow.log_param(data_type + " size", msg)
    return X_features, y_features, data

def run_model(scale_data=True):
    params["feature_names"] = x_cols
    mlflow.log_param('Scaled', scale_data)
    mlflow.log_param('y_col', ', '.join(y_cols))
    mlflow.log_param('X_cols', ', '.join(x_cols))
    mlflow.log_param('XGB Params', params)
    # Create XGB Model
    x_train, y_train, train = load_data(model_file_list, x_cols, y_cols, data_type="Training")

    xgb = XGBClassifier(**params)

    # Load Test Data
    x_test, y_test, test = load_data([test_file], x_cols, y_cols, data_type="Testing")
    import matplotlib.image as mpimg

    fig, ax = plt.subplots()
    sns.set(rc={'figure.figsize': (12, 9)})
    # x_train.plot.hist(alpha=0.5)
    # train.plot.hist(alpha=0.5, grid=False)
    plt.savefig("TrainingHistogram.png")
    #mlflow.log_figure(fig, "TrainingHistogram.png")
    mlflow.log_image(mpimg.imread("TrainingHistogram.png"), "TrainingHistogram.png")
    # plt.show()

    # Standard Scaled X Prediction
    if scale_data:
        scalar = StandardScaler()
        scalar.fit(x_train)
        x_train = pd.DataFrame(scalar.transform(x_train), columns=scalar.get_feature_names(x_train.columns))
        x_test = pd.DataFrame(scalar.transform(x_test), columns=scalar.get_feature_names(x_test.columns))
        #x_train = scalar.transform(x_train)
        #x_test = scalar.transform(x_test)

    fig, ax = plt.subplots()
    sns.set(rc={'figure.figsize': (12, 9)})
    # x_train.plot.hist(alpha=0.5)
    x_train.hist()
    plt.savefig("TrainingHistogramScaled.png")
    mlflow.log_image(mpimg.imread("TrainingHistogramScaled.png"), "TrainingHistogramScaled.png")
    #mlflow.log_figure(fig, "TrainingHistogramScaled.png")
    # plt.show()

    # Train model & predict
    xgb.fit(x_train, y_train[y_cols])
    y_pred = xgb.predict(x_test)

    precision, recall, f1, y_true = precision_recall_fscore_support(y_test[y_cols], y_pred, average=None)
    # from sklearn.metrics import precision_score, recall_score
    ps = precision_score(y_test[y_cols], y_pred)
    rs = recall_score(y_test[y_cols], y_pred)

    #  y_true = y_true.astype('int')

    accuracy = accuracy_score(y_test[ y_cols ], y_pred)
    print(f"accuracy: {accuracy:.3f}")
    mlflow.log_metric('3-Accuracy', accuracy)

    # pd.options.display.float_format = '{:,.3f}'.format

    for idx in range(len(recall)):
        mlflow.log_metrics({f'2-recall-{idx}': recall[idx],
                            f'0-precision-{idx}': precision[idx],
                            f'1-f1-{idx}': f1[idx],
                            f'4-y_true-{idx}': y_true[idx]}, step=idx)
        idx += 1

    # from mlflow.models.signature import infer_signature
    # signature = infer_signature(x_train, xgb.predict(xgb.DMatrix(data=x_train, label=y_train)))
    # mlflow.xgboost.log_model(xgb, "model") #, signature=signature)

    fig, ax = plt.subplots()
    sns.set(rc = {'figure.figsize':(12,9)})
    cm = confusion_matrix(y_test[ y_cols ], y_pred)
    sns.heatmap(cm, annot=True, cmap="YlGnBu",fmt='d')
    fig.savefig("ConfusionMatrix.png")
    mlflow.log_figure(fig, "ConfusionMatrix.png")
    # plt.show()

    cm_pct = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
    sns.heatmap(cm_pct, annot=True, cmap="YlGnBu", fmt=".3f")
    fig.savefig("ConfusionMatrixPct.png")
    mlflow.log_figure(fig, "ConfusionMatrixPct.png")
    # plt.show()

    # feature_importances = pd.DataFrame(xgb.feature_importances_,index=x_train.columns.tolist(),columns=['importance'])
    # feature_importances.sort_values('importance', ascending=False)


if __name__ == "__main__":
    #
    # Define Parameters
    #
    theta_neg_w1 = ['c_w1_n1_theta', 'c_w1_n2_theta', 'c_w1_n3_theta']
    theta_neg_w2 = ['c_w2_n1_theta', 'c_w2_n2_theta', 'c_w2_n3_theta']
    theta_neg_w3 = ['c_w3_n1_theta', 'c_w3_n2_theta', 'c_w3_n3_theta']

    theta_pos_w1 = ['c_w1_p1_theta', 'c_w1_p2_theta', 'c_w1_p3_theta']
    theta_pos_w2 = ['c_w2_p1_theta', 'c_w2_p2_theta', 'c_w2_p3_theta']
    theta_pos_w3 = ['c_w3_p1_theta', 'c_w3_p2_theta', 'c_w3_p3_theta']

    tv_neg_w1 = ['c_w1_n1_time_value', 'c_w1_n2_time_value', 'c_w1_n3_time_value']
    tv_neg_w2 = ['c_w2_n1_time_value', 'c_w2_n2_time_value', 'c_w2_n3_time_value']
    tv_neg_w3 = ['c_w3_n1_time_value', 'c_w3_n2_time_value', 'c_w3_n3_time_value']

    tv_pos_w1 = ['c_w1_p1_time_value', 'c_w1_p2_time_value', 'c_w1_p3_time_value']
    tv_pos_w2 = ['c_w2_p1_time_value', 'c_w2_p2_time_value', 'c_w2_p3_time_value']
    tv_pos_w3 = ['c_w3_p1_time_value', 'c_w3_p2_time_value', 'c_w3_p3_time_value']

    deltas = ['n5s_delta', 'n15s_delta', 'n30s_delta', 'n60s_delta']

    x_cols = [ ]
    x_cols += theta_pos_w1 + theta_pos_w2  + theta_pos_w3  + deltas + theta_neg_w1 + theta_neg_w2 + theta_neg_w3
#   x_cols += tv_pos_w1 + tv_pos_w2 + tv_pos_w3 + deltas + tv_neg_w1 + tv_neg_w2 + tv_neg_w3
#   x_cols += ['c_w1_p2_theta', 'c_w1_p3_theta', 'c_w2_p2_theta', 'c_w2_p3_theta', 'c_w2_n2_time_value', 'c_w3_n2_time_value', 'c_w3_n3_time_value', 'n15s_delta', 'n30s_delta', 'n60s_delta']

    y_cols = ['p30s_bucket']  # ,  'p5s_bucket', 'p30s_bucket', 'p60s_bucket']

    if len(sys.argv) >= 2:
        y_cols = sys.argv[1].replace("'", "").replace('"', "").split(",")

    if len(sys.argv) >= 3:
        x_cols = sys.argv[2].replace("'", "").replace('"', "").split(",")

    bin_counts = 2

    model_file_list = ['ml_cp18_AAPL20220103.csv', 'ml_cp18_AAPL20220104.csv', 'ml_cp18_AAPL20220106.csv', 'ml_cp18_AAPL20220107.csv', 'ml_cp18_AAPL20220110.csv', 'ml_cp18_AAPL20220111.csv', 'ml_cp18_AAPL20220112.csv']
    test_file = "ml_cp18_AAPL20220105.csv"

    #  https://xgboost.readthedocs.io/en/stable/parameter.html
    params = {
            'copy_X': True,
            'fit_intercept': False,
            'normalize': True,
            '_kfold': 2,
            # 'objective': 'validation:accuracy',
            # 'objective': 'multi:softprob',
            # 'objective': 'binary:logistic',
            'enable_categorical': False,
            '_tuning_objective_metric': 'validation:f1',
            'eval_metric': 'auc',
            # 'tree_method': 'gpu_hist',
            # 'eval_metric': 'accuracy,f1',
            # 'eval_metric':'merror',
            # 'eval_metric': 'accuracy,f1X',
            # Muthu params
            #'subsample': 0.75,  # Setting it to 0.5 means that XGBoost would randomly sample half of the training data prior to growing trees. and this will prevent overfitting.
            'gamma': 0.001,  # Minimum loss reduction required to make a further partition on a leaf node of the tree. The larger gamma is, the more conservative the algorithm will be
            'alpha': 0.0,  # L1 regularization is Lasso Regression wich adds “squared magnitude” of coefficient as penalty term to the loss functi
            'lambda': 1.0,  # L2 regularization is Ridge Regression which adds “absolute value of magnitude” of coefficient as penalty term to the loss function.
            'eta': 0.03,  # Step size shrinkage used in update to prevents overfitting
            'min_child_weight': 0.05,  # Minimum sum of instance weight (hessian) needed in a child the building process will give up further partitioning.
            # 'num_class': bin_counts,
            # not too sure.
            'max_depth': 10,  # Maximum tree depth for base learners.
            # 'early_stopping_rounds': 50,  # don't over fit
            'num_round': 100,  # num_boost_round == num_boost_round
            'use_label_encoder': False # UserWarning: The use of label encoder in XGBClassifier is deprecated...
        }
    #
    #  Call Main
    #

    mlflow.set_experiment("xgb-binary-" + y_cols[0])
    mlflow.start_run()
    mlflow.xgboost.autolog()
#    with mlflow.start_run() as run:
#        run_model(scale_data=True)

    run_model(scale_data=False)

    mlflow.end_run()