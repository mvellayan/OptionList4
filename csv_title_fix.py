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


def fix_csv_file(file_name):
    global config, pdStockQuotes, pdOptionList, pdOptionList3wC, pdOptionQuotesIdx, expiryList
    # print(f"\tFix_csv_file {file_name}")

    if "projection" in file_name:
        print(f"skipping projection file {file_name}")
        return

    # 1. read 1st line to determine what to fix
    first_line =""
    with open(file_name) as f:
        first_line = f.readline().rstrip()


    if first_line == "ConId,Symbol,Time,Bid,BidSize,Ask,AskSize,Last,LastSize,Volume,histVolatility,impliedVolatility":
        # 2a. for stock/option, (a) change column name, (b) filter by time 9:30 -4:00
        fix_csv_file_quote(file_name)
    elif first_line == ",secType,conId,symbol,lastTradeDateOrContractMonth,strike,right,localSymbol":
        # 2v. for option_list, (a) change column name, (b) remove 1st column
        fix_csv_file_optionlist(file_name)
    else:
        pass
        # print(f"skipping file {file_name} with this line {first_line}")


def fix_csv_file_quote(file_name):
    tempfile = file_name + ".tmp"
    index = 1
    with open(file_name, "r") as input:
        with open(tempfile, "w") as output:
            for line in input:
                if index == 1:
                    output.write("con_id,symbol,time,bid,bid_size,ask,ask_size,last,last_size,volume,hist_volatility,implied_volatility\n")
                else:
                    output.write(line)
                index += 1
    # print(f"quote file fix from {file_name} to {tempfile}")
    os.remove(file_name)
    os.rename(tempfile, file_name)


def fix_csv_file_optionlist(file_name):
    tempfile = file_name + ".tmp"
    index  = 1
    with open(file_name, "r") as input:
        with open(tempfile, "w") as output:
            for line in input:
                if index == 1:
                    #output.write("con_id,symbol,time,bid,bid_size,ask,ask_size,last,last_size,volume,hist_volatility,implied_volatility")
                    output.write("con_id,symbol,expiry,strike,right\n")
                else:
                    line_arr = line.rstrip('\n').split(",")
                    #2,7,4,5,6
                    output.write( f"{line_arr[2]},{line_arr[7]},{line_arr[4]},{line_arr[5]},{line_arr[6]}\n")
                index += 1

    # print(f"optionlist file fix from {file_name} to {tempfile}")
    os.remove(file_name)
    os.rename(tempfile, file_name)


def process_directory(full_dir_name):
    global pdStockQuotes, pdOptionList, pdOptionQuotesIdx
    global running_missing, running_total, total_lookup, config

    print(f"Processing_directory: {full_dir_name}]")

    # 1. Process csv files in dir dir
    for file in glob.glob(full_dir_name + "/*csv", recursive=False):
        fix_csv_file(file)

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
        print("\n\nUsage: project.py <starting dir>\n\n")
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

