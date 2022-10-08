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

import seaborn as sns


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


def plot_variance(pca, width=8, dpi=100):
    # Create figure
    fig, axs = plt.subplots(1, 2)
    n = pca.n_components_
    grid = np.arange(1, n + 1)
    # Explained variance
    evr = pca.explained_variance_ratio_
    axs[0].bar(grid, evr)
    axs[0].set(
        xlabel="Component", title="% Explained Variance", ylim=(0.0, 1.0)
    )
    # Cumulative Variance
    cv = np.cumsum(evr)
    axs[1].plot(np.r_[0, grid], np.r_[0, cv], "o-")
    axs[1].set(
        xlabel="Component", title="% Cumulative Variance", ylim=(0.0, 1.0)
    )
    # Set up figure
    fig.set(figwidth=8, dpi=100)
    return axs

def make_mi_scores(X, y, discrete_features):
    mi_scores = mutual_info_regression(X, y, discrete_features=discrete_features)
    mi_scores = pd.Series(mi_scores, name="MI Scores", index=X.columns)
    mi_scores = mi_scores.sort_values(ascending=False)
    return mi_scores



# 110 cols of 267 cols
x_cols = [ 'bid',  'bid_size', 'ask',  'ask_size', 'last', 'last_size', 'hist_volatility',  'implied_volatility',
'n5s',  'n15s', 'n30s', 'n60s', 'n300s',    'n600s',
'n5s_delta',    'n15s_delta',   'n30s_delta',   'n60s_delta',   'n300s_delta',  'n600s_delta',
'c_w1_n3_ask',  'c_w1_n3_bid',  'c_w1_n3_last', 'c_w1_n3_time_value',   'c_w1_n3_theta',    'c_w1_n3_implied_volatility',
'c_w1_n2_ask',  'c_w1_n2_bid',  'c_w1_n2_last', 'c_w1_n2_time_value',   'c_w1_n2_theta',    'c_w1_n2_implied_volatility',
'c_w1_n1_ask',  'c_w1_n1_bid',  'c_w1_n1_last', 'c_w1_n1_time_value',   'c_w1_n1_theta',    'c_w1_n1_implied_volatility',
'c_w1_p1_ask',  'c_w1_p1_bid',  'c_w1_p1_last', 'c_w1_p1_time_value',   'c_w1_p1_theta',    'c_w1_p1_implied_volatility',
'c_w1_p2_ask',  'c_w1_p2_bid',  'c_w1_p2_last', 'c_w1_p2_time_value',   'c_w1_p2_theta',    'c_w1_p2_implied_volatility',
'c_w1_p3_ask',  'c_w1_p3_bid',  'c_w1_p3_last', 'c_w1_p3_time_value',   'c_w1_p3_theta',    'c_w1_p3_implied_volatility',
'c_w2_n3_ask',  'c_w2_n3_bid',  'c_w2_n3_last', 'c_w2_n3_time_value',   'c_w2_n3_theta',    'c_w2_n3_implied_volatility',
'c_w2_n2_ask',  'c_w2_n2_bid',  'c_w2_n2_last', 'c_w2_n2_time_value',   'c_w2_n2_theta',    'c_w2_n2_implied_volatility',
'c_w2_n1_ask',  'c_w2_n1_bid',  'c_w2_n1_last', 'c_w2_n1_time_value',   'c_w2_n1_theta',    'c_w2_n1_implied_volatility',
'c_w2_p1_ask',  'c_w2_p1_bid',  'c_w2_p1_last', 'c_w2_p1_time_value',   'c_w2_p1_theta',    'c_w2_p1_implied_volatility',
'c_w2_p2_ask',  'c_w2_p2_bid',  'c_w2_p2_last', 'c_w2_p2_time_value',   'c_w2_p2_theta',    'c_w2_p2_implied_volatility',
'c_w2_p3_ask',  'c_w2_p3_bid',  'c_w2_p3_last', 'c_w2_p3_time_value',   'c_w2_p3_theta',    'c_w2_p3_implied_volatility',
'c_w3_n3_ask',  'c_w3_n3_bid',  'c_w3_n3_last', 'c_w3_n3_time_value',   'c_w3_n3_theta',    'c_w3_n3_implied_volatility',
'c_w3_n2_ask',  'c_w3_n2_bid',  'c_w3_n2_last', 'c_w3_n2_time_value',   'c_w3_n2_theta',    'c_w3_n2_implied_volatility',
'c_w3_n1_ask',  'c_w3_n1_bid',  'c_w3_n1_last', 'c_w3_n1_time_value',   'c_w3_n1_theta',    'c_w3_n1_implied_volatility',
'c_w3_p1_ask',  'c_w3_p1_bid',  'c_w3_p1_last', 'c_w3_p1_time_value',   'c_w3_p1_theta',    'c_w3_p1_implied_volatility',
'c_w3_p2_ask',  'c_w3_p2_bid',  'c_w3_p2_last', 'c_w3_p2_time_value',   'c_w3_p2_theta',    'c_w3_p2_implied_volatility',
'c_w3_p3_ask',  'c_w3_p3_bid',  'c_w3_p3_last', 'c_w3_p3_time_value',   'c_w3_p3_theta',    'c_w3_p3_implied_volatility'
]

# x_cols = ['volume', 'c_w1_p3_theta','c_w1_p2_theta','c_w3_n2_theta','c_w2_p3_theta','c_w3_p1_theta','c_w2_n1_theta','c_w3_n1_theta','c_w3_n3_theta','c_w2_n2_theta','c_w2_p1_theta','c_w2_p2_theta','c_w1_n1_theta','c_w1_p1_theta','c_w3_p3_theta','c_w2_n3_theta','c_w3_p2_theta', 'c_w1_n2_theta','c_w1_n3_theta','implied_volatility','hist_volatility']
y_cols = ['p30s_bucket']  # ,  'p5s_bucket', 'p30s_bucket', 'p60s_bucket']
bin_counts = 5

file_list = ['ml_cp18/ml_cp18_AAPL20220103.csv','ml_cp18/ml_cp18_AAPL20220104.csv', 'ml_cp18/ml_cp18_AAPL20220105.csv', 'ml_cp18/ml_cp18_AAPL20220106.csv', 'ml_cp18/ml_cp18_AAPL20220107.csv',]
file_list_train = file_list[:-1]
file_list_test = file_list[-1:]



import os
data = None
for file in file_list:
    file = "../" + file
    assert os.path.exists(file), "Data file does not exist!"
    data_tmp = pd.read_csv(file, low_memory=False)
    if data is None:
        data = data_tmp
    else:
        data = data.append(data_tmp, ignore_index=True)
print ('loaded data', data.shape)
data = data.dropna()
print ('after dropna', data.shape)


# Get the numeric cols to scale
numeric_cols = []
for i, v in data.dtypes.items():
    # print(f'index: {i} and value: {v}')
    if v != 'object': numeric_cols.append(i)
#print(numeric_cols)
data_numbers = data [ numeric_cols ]
print(data_numbers.shape)
x_cols_numeric = data_numbers.columns
print (x_cols_numeric)


scalar = StandardScaler()
scalar.fit(data_numbers)
data_scaled = scalar.transform(data_numbers)


from sklearn.decomposition import PCA
pca = PCA().fit(data_scaled)
pca_transformed = pca.transform(data_scaled)
plt.plot(np.cumsum(pca.explained_variance_ratio_))
plt.xlim(0,7,1)
plt.xlabel('Number of components')
plt.ylabel('Cumulative explained variance')


np.set_printoptions(suppress=True, precision=4)
print(pca.explained_variance_ratio_)
np.set_printoptions()  # reset print options