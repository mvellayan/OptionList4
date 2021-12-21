import argparse
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
from utils.FileUtil import makeDirectory, unzip_file, get_sec_to_expire, getDateStrFromPath

logging.basicConfig(level=logging.ERROR)
log = logging.getLogger("myLogger")
log.setLevel(logging.INFO)


def main(scan_data_dir):
    global  config
    print(f"\nProcessing {scan_data_dir}")
    zipFilename = scan_data_dir + "/" + config["stock"] + getDateStrFromPath(scan_data_dir) + ".zip"

    # 6b. loose files, zip it up  oq_FB211203C00305000_20211201.csv
    FileUtil.zip_and_delete(directory=scan_data_dir, stock_symbol_in_file_name=config["stock"],
                            file_prefix_tuple=('sq_', 'oq_', 'ol_'), zip_file_name=zipFilename)


def collect_args() -> dict:
    """Collect arguments passed into the script

    Returns:
        dict: Arguments Object
    """
    parser = argparse.ArgumentParser(
        description='zips up data for a given stock')
    parser.add_argument('config', help='JSON file that contains all the configuration',
                        default="config.json", type=str)
    parser.add_argument('data_dir', help='Data file directory to scan.  Added to current path',
                        default="/IBdata/", type=str)
    retDict = parser.parse_args()

    if not retDict.data_dir.startswith("/"):
        retDict.data_dir = "/" + retDict.data_dir
    if not retDict.data_dir.endswith("/"):
        retDict.data_dir = retDict.data_dir + "/"

    return retDict


if __name__ == "__main__":

    args = collect_args()
    config = FileUtil.readConfig(args.config)
    data_dir = os.getcwd() + args.data_dir

    print("Scanning: " + data_dir)
    for rootdir, dirs, files in os.walk(data_dir):
        print (f"{rootdir} {dirs} {files}")
        for subdir in dirs:
            full_dir = os.path.join(rootdir, subdir)
            search_mask1 = full_dir + "/*" + config["stock"] + '*.csv'
            if glob.glob(search_mask1):
                main(full_dir)

