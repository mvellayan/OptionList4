import datetime
import glob
import numpy as np
import pandas as pd
import timeit


df = pd.DataFrame()

def load_data(data_dir: str, data_prefix: str, max_files:int, trades_flag: bool):
    global df
    # Get CSV files list from a folder
    file_str = data_dir + data_prefix + "-*.csv"
    csv_files = glob.glob(file_str)
    csv_files = csv_files[0:max_files]
    print("  loading " + file_str + " file count: " + str(len(csv_files)))
    # Read each CSV file into DataFrame
    # This creates a list of dataframes
    df_list = (pd.read_csv(file) for file in csv_files)
    # Concatenate all DataFrames
    df = pd.concat(df_list, ignore_index=True)
    # Only want to track average to 3 decimal places.  Otherwise, end up with a lot of digits
    if trades_flag:
        df['average'] = df['average'].round(decimals=3)
        # need this column to compute average of averages
        df['_weighted_vol_avg'] = df['volume'] * df['average']

    else:
        df.drop(columns=['average','volume','barCount'], inplace=True)
        df.rename(columns={'open': 'bid_avg', 'high': 'ask_max', 'low': 'bid_min', 'close': 'ask_avg'}, inplace=True)



def dedup():
    global df
    # 1.1 Drop duplicates & check for missing values
    dups = len(df['date'])-len(df['date'].drop_duplicates())
    print("      # of duplicates", dups, ' out of ', len(df), ' or ', round(dups/len(df), 5), '%')
    # Need this col for dedup
    df['date2_str'] = df['date'][::].str.slice(stop=10)
    # Drop duplicate entries
    df.drop_duplicates(subset=['date'], keep='first', inplace=True)

    pd_group_cnt = df.groupby(['date2_str'])['date2_str'].count().to_frame()
    print("      Days with 23,400 Qutoes:")
    print("      ------------------------")
    pd.set_option('display.max_rows', None)
    print(pd_group_cnt.loc[pd_group_cnt['date2_str'] == 23400])

    print("      Days WRONG # Qutoes:")
    print("      --------------------")
    print(pd_group_cnt.loc[pd_group_cnt['date2_str'] != 23400])
    # df = df.drop('date2_str', axis=1)
    df.set_index('date')
    df = df.sort_index()
    pd.set_option('display.max_rows', 10)

# lambda functions

# return 1st value in series
def firstValue(rows):
    return rows.iloc[0]

# return last value in series
def lastValue(rows):
    return rows.iloc[-1]

# return arrow indicator for boxed in values;
#   -1 below lower bound
#    0 inside the box
#   +1 above the max value
def arrow(new_amt, old_amt, box):
    if old_amt == np.nan:
        return np.nan
    if new_amt == np.nan:
        return np.nan
    if (new_amt - old_amt) <= (box * -1):
        return '-1'
    if (new_amt - old_amt) >= box:
        return '1'
    else:
        return '0'

#  lambda function to adds up the last 5 values, excluding the very last value
def sum_last_5(rows):
    # print ("[" , rows[-6:-1], rows[-6:-1].sum(), "]")
    return rows[-6:-1].sum()

#  lambda function returns lowest of the last 5 values, excluding the very last value
def min_last_5(rows):
    return rows.iloc[-6:-1].min()

#  lambda function returns higest of  the last 5 values, excluding the very last value
def max_last_5(rows):
    return rows.iloc[-6:-1].max()


# Store/Save 1 second windows for h1, h2, h3, h4, h5
def one_second_window(prefix: str, window: int, trades: bool):
    global df
    if trades:
        df[prefix + '_high'] = df['high'].rolling(window=window).agg({'maxLast': firstValue})
        df[prefix + '_low'] = df['low'].rolling(window=window).agg({'minLast': firstValue})
        df[prefix + '_barCount'] = df['barCount'].rolling(window=window).agg({'sumLast': firstValue})
        df[prefix + '_volume'] = df['volume'].rolling(window=window).agg({'sumLast': firstValue})
        df[prefix + '_average'] = df['average'].rolling(window=window).agg({'sumLast': firstValue})
    else:
        df[prefix + '_ask_max'] = df['ask_max'].rolling(window=window).agg({'maxLast': firstValue})
        df[prefix + '_bid_min'] = df['bid_min'].rolling(window=window).agg({'minLast': firstValue})
        df[prefix + '_bid_avg'] = df['bid_avg'].rolling(window=window).agg({'sumLast': firstValue})
        df[prefix + '_ask_avg'] = df['ask_avg'].rolling(window=window).agg({'sumLast': firstValue})

# Store/Save 5 second windows for h1, h2, h3, h4, h5
def five_second_window(prefix: str, window: int):
    global df
    df[prefix + '_high_max'] = df['high'].rolling(window=window).agg({'maxLast5': max_last_5})
    df[prefix + '_low_min'] = df['low'].rolling(window=window).agg({'minLast5': min_last_5})

    df[prefix + '_barCount_sum'] = df['barCount'].rolling(window=window).agg({'sumLast5': sum_last_5})
    df[prefix + '_volume_sum'] = df['volume'].rolling(window=window).agg({'sumLast5': sum_last_5})
    df[prefix + '_weighted_vol_avg_sum'] = df['_weighted_vol_avg'].rolling(window=6).agg({'SumLast5': sum_last_5})
    df[prefix + '_average_avg'] = df[prefix + '_weighted_vol_avg_sum'] / df[prefix + '_volume_sum']
    df[prefix + '_average_avg'] = df[prefix + '_average_avg'].round(decimals=3)
    df.drop(columns=[prefix + '_weighted_vol_avg_sum'])


# Compute Future 5 second window summary
def future_avg(prefix:str, window:int):
    global df
    df.set_index('date')
    df = df.sort_index(ascending=False)
    df.reset_index()
    df[ prefix + '_average'] = df['average'].rolling(window=window).agg({'firstValue': firstValue})
    df = df.sort_index(ascending=True)
    df.reset_index()

def future_arrow(prefix:str, field: str, window:int):
    global df
    df[prefix + "_arrow"] = df.apply(lambda x: arrow(x[field], x['average'], window), axis=1)


def rebase(low,
           open,	high,	close,	average,
           h1s_high_max,	h1s_low_min,	h1s_average_avg,
           h2s_high_max,	h2s_low_min,	h2s_average_avg,
           h3s_high_max,	h3s_low_min,	h3s_average_avg,
           h4s_high_max,	h4s_low_min,	h4s_average_avg,
           f5s_average):
   return pd.Series([open - low, 	high - low, close - low, 	average - low,
          h1s_high_max - low, 	h1s_low_min - low, 	h1s_average_avg - low,
          h2s_high_max - low, 	h2s_low_min - low, 	h2s_average_avg - low,
          h3s_high_max - low, 	h3s_low_min - low, 	h3s_average_avg - low,
          h4s_high_max - low, 	h4s_low_min - low, 	h4s_average_avg - low,
          f5s_average - low])
## Compute 5 second window summary

def add_vix_col():
    global df
    csv_files = glob.glob("./contract-VIX/*.csv")
    print("  loading VIX file count: " + str(len(csv_files)))
    # Read each CSV file into DataFrame
    # This creates a list of dataframes
    df_list = (pd.read_csv(file) for file in csv_files)
    # Concatenate all DataFrames
    dfVIX = pd.concat(df_list, ignore_index=True)
    # dedup
    dfVIX.drop_duplicates(subset=['date'], keep='first', inplace=True)
    vixPD2 = dfVIX[['date', 'open']].copy()
    vixPD2.rename(columns={'open': 'vix'}, inplace=True)
    print("  Shapes before merge: ", df.shape, vixPD2.shape)
    df = pd.merge(left=df, right=vixPD2, how="left", on="date", validate="one_to_one")
    print("  After merge: ", df.shape)


def main(data_dir, data_prefix, file_max):
    global df
    bTrades = "TRADES" in data_prefix
    bBidAsk = "BID_ASK" in data_prefix

    result = timeit.timeit(stmt='load_data("' + data_dir + '", "' + data_prefix + '", '
                                + str(file_max) + ', ' + str(bTrades) + ')', globals=globals(), number=1)
    print(f"Loaded Data: {result.__round__(2)} seconds. ", df.shape)

    result = timeit.timeit(stmt='dedup()', globals=globals(), number=1)
    print(f"Dedup Data : {result.__round__(2)} seconds.", df.shape)

    for ctr in range(1, 5):
        prefix = "h"+str(ctr)+"s"
        call = 'one_second_window("' + prefix + '", ' + str(ctr+1) + ', ' + str(bTrades) + ')'
        result = timeit.timeit(stmt=call, globals=globals(), number=1)
        print(f"Computed 1 second window for [{call}]: {result.__round__(2)} seconds.", df.shape)


    # prefix = ["h5s", "h10s", "h15s", "h20s"]
    # window = [ 6, 11, 16, 21]
    # for pre, win in zip(prefix, window):
    #    call = 'five_second_window("' + pre + '",' + str(win) + ')'
    #    result = timeit.timeit(stmt=call, globals=globals(), number=1)
    #    print(f"Computed 5 second window for [{call}]: {result.__round__(2)} seconds.", df.shape)

    if bTrades:
        result = timeit.timeit(stmt='future_avg("f5s", 6)', globals=globals(), number=1)
        print(f"Compute future f5s second: {result.__round__(2)} seconds.", df.shape)

        prefix = ["f5s_10c", "f5s_15c", "f5s_20c", "f5s_25c"]
        window = [0.10, 0.15, 0.20, 0.25]
        for pre, win in zip(prefix, window):
            # future_arrow(pre, "f5s_average", window=win)
            call = 'future_arrow("' + pre + '", "f5s_average", window=' + str(win) + ')'
            # print(funCall)
            result = timeit.timeit(stmt=call, globals=globals(), number=1)
            print(f"Compute future arrow for  {call}] second: {result.__round__(2)} seconds.", df.shape)

        df = df.drop(columns=['_weighted_vol_avg'])
        print(f"   dropped computed col", df.shape)
    else:
        add_vix_col()

    df.to_csv(data_dir + data_prefix + ".csv", index=False)

"""
    df[['open', 'high', 'close', 'average',
        'h1s_high', 'h1s_low', 'h1s_average',
        'h2s_high', 'h2s_low', 'h2s_average',
        'h3s_high', 'h3s_low', 'h3s_average',
        'h4s_high', 'h4s_low', 'h4s_average',
        'f5s_average']] = df.apply(lambda x:
                                  rebase(x['low'], x['open'],	x['high'],	x['close'],	x['average'],
                                         x['h1s_high'],	x['h1s_low'],	x['h1s_average'],
                                         x['h2s_high'],	x['h2s_low'],	x['h2s_average'],
                                         x['h3s_high'],	x['h3s_low'],	x['h3s_average'],
                                         x['h4s_high'],	x['h4s_low'],	x['h4s_average'],
                                         x['f5s_average']), axis=1)

    print(f"   normalized from low value", df.shape)
"""

start_time = datetime.datetime.now()
p_data_dir ="./contract-TSLA/"
#p_data_prefix = "TSLA-BID_ASK"
p_data_prefix = "TSLA-TRADES"
main(p_data_dir, p_data_prefix, 999)
print("\n\nStarted: ", start_time, ' Finished: ', datetime.datetime.now(), ' Dur: ', (datetime.datetime.now() - start_time).total_seconds())