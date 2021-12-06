import logging
import shutil
from datetime import datetime, timedelta, date
import glob, sys, os
import pandas as pd
from pprint import pprint
import pytz
from timeit import default_timer as timer
from datetime import timedelta

from utils import FileUtil, IBUtil
from utils.FileUtil import makeDirectory, unzip_file, get_sec_to_expire, setup_logging

logging.basicConfig(level=logging.ERROR)
log = logging.getLogger("myLogger")
log.setLevel(logging.INFO)

pdOptionList: pd.DataFrame = None     # Data Frame all options Contracts for the symbol
pdOptionList3wC: pd.DataFrame = None     # 3 week calls only
pdStockQuotes: pd.DataFrame = None    # Data Frame all date/time quotes for the symbol
pdOptionQuotesIdx = {}
config = {}                      # parameter config object
expiryList = []                 # list of expiry we are interested in for the given date
running_missing = 0
running_total = 0
total_lookup = 0


def fix_csv_file(full_file_name):
    global config, pdStockQuotes, pdOptionList, pdOptionList3wC, pdOptionQuotesIdx, expiryList
    # print(f"\tFix_csv_file {file_name}")

    file_name = full_file_name[full_file_name.rfind('/') + 1:]
    if file_name.startswith("ml_") or file_name.startswith("ol_") or file_name.startswith("sq_") or file_name.startswith("oq_"):
        # print(f"skipping projection file {full_file_name}")
        return

    if "projection_stock_call_options" in file_name:
        new_name = full_file_name.replace("projection_stock_call_options", "ml_cp18")
        os.rename(full_file_name, new_name)
        return

    if "optionList" in full_file_name:
        new_name = full_file_name.replace("optionList", "_")
        new_name = new_name[:new_name.rfind('/')+1] + "ol_" + new_name[new_name.rfind('/')+1:]
        print(f"changing {full_file_name} to {new_name}")
        os.rename(full_file_name, new_name)
        return

    # 1. read 1st line to determine what to fix
    first_line =""
    with open(full_file_name) as f:
        first_line = f.readline().rstrip()
        second_line = f.readline().rstrip()


    if first_line == "ConId,Symbol,Time,Bid,BidSize,Ask,AskSize,Last,LastSize,Volume,histVolatility,impliedVolatility" or \
            first_line == "con_id,symbol,time,bid,bid_size,ask,ask_size,last,last_size,volume,hist_volatility,implied_volatility":
        # rename file w/ sq_ or oq_
        first_line_arr = first_line.split(",")
        if first_line_arr[1] != "symbol":
            raise Exception(f"Unexpected quote file format: {first_line}")
        second_line_arr = second_line.split(",")
        if len(second_line_arr[1]) > 10:
            new_name = full_file_name[:full_file_name.rfind('/') + 1] + "oq_" + full_file_name[full_file_name.rfind('/') + 1:]
        else:
            new_name = full_file_name[:full_file_name.rfind('/') + 1] + "sq_" + full_file_name[full_file_name.rfind('/') + 1:]
        os.rename(full_file_name, new_name)
    elif first_line == ",secType,conId,symbol,lastTradeDateOrContractMonth,strike,right,localSymbol" or \
            first_line == "con_id,symbol,expiry,strike,right":
        new_name = full_file_name[:full_file_name.rfind('/') + 1] + "ol_" + full_file_name[full_file_name.rfind('/') + 1:]
        os.rename(full_file_name, new_name)
    else:
        print(f"skipping file {full_file_name} with this line {first_line}")


def process_directory(full_dir_name):
    global pdStockQuotes, pdOptionList, pdOptionQuotesIdx
    global running_missing, running_total, total_lookup, config

    print(f"Processing_directory: {full_dir_name}]")

    # 1. Process csv files in dir dir
    for file in glob.glob(full_dir_name + "/*csv", recursive=False):
        fix_csv_file(file)

    for file in glob.glob(full_dir_name + "/*csv*", recursive=False):
        # FBoptionList20211126.csv_000650
        # remove redundant copies of optionList.  Their names follow the format FBoptionList20211126.csv_030824
        if "optionList" in file and file[-6:].isnumeric():
            print(f"removing file {file}")
            os.remove(file)

    zip_file_ctr: int = 0
    for zip_file in glob.glob(full_dir_name + "/*zip", recursive=False):
        # 1. expand zip file int to new temp dir
        temp_dir = full_dir_name + "/" + FileUtil.getDateTimeStamp(1) + str(zip_file_ctr)
        zip_file_ctr += 1
        os.makedirs(temp_dir, exist_ok=True)
        unzip_file(temp_dir, zip_file)
        # 2. loop over new dir finding csv files
        file_ctr: int = 0
        for csv_file in glob.glob(temp_dir + "/*csv", recursive=False):
            # 3. Fix csv files in dir
            file_ctr += 1
            fix_csv_file(csv_file)
        print(f"\tfor directory {temp_dir}, processed {file_ctr} files")
        # 4. zip it back up as fixed.zip
        new_zip_file = zip_file.replace(".zip", "_f1204.zip")
        FileUtil.zip_and_delete(directory=temp_dir, file_prefix="", zip_file_name=new_zip_file)
        # 5. delete old zip and rename new zip to old file
        os.remove(zip_file)
        os.rename(new_zip_file, zip_file)
        # 6. delete temporary directory
        #os.remove(temp_dir)
        try:
            shutil.rmtree(temp_dir)
        except OSError as e:
            print("Error: %s : %s" % (temp_dir, e.strerror))


if __name__ == "__main__":

    pd.set_option('display.max_columns', None)

    if len(sys.argv) != 2:
        print("\n\nUsage: file_prefix_fix_1206.py  <starting dir>\n\n")
        sys.exit(0)
    else:
        scan_dir = os.getcwd() + "/" + sys.argv[1]
        print("scanning data directory [" + scan_dir + "]")

    if not os.path.isdir(scan_dir):
        print("Input path does not seem to exist / as a dir ", scan_dir, os.getcwd() + "/" + sys.argv[2])
        sys.exit(0)

    for rootdir, dirs, files in os.walk(scan_dir):
        # process each directory under scan_dir
        for subdir in dirs:
            full_dir = os.path.join(rootdir, subdir)
            process_directory(full_dir)

