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


if __name__ == "__main__":

    config = FileUtil.readConfig(sys.argv[1])
    data_dir = os.getcwd() + "/" + config["ib"]["data_dir"] + "/"

    print("Scanning: " + data_dir)
    for rootdir, dirs, files in os.walk(data_dir):
        for subdir in dirs:
            full_dir = os.path.join(rootdir, subdir)
            search_mask1 = full_dir + "/*" + config["stock"] + '*.csv'
            if glob.glob(search_mask1):
                main(full_dir)

