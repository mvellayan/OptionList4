import sys
import errno
import glob
import json
import os
import re
import zipfile
import logging

import numpy as np
from datetime import datetime, timedelta
import time

from ib_insync import *

log = logging.getLogger("myLogger")

def readConfig(fileName):
    data = {}
    try:
        # open file and load data
        f = open(fileName, 'r')
        data = json.load(f)
        f.close()
    except OSError:
        log.error('cannot open file', fileName)
        sys.exit(1)
    # verify fields exist
    x = data["tws_port"]
    x = data["file_flush_seconds"]
    x = data["stock"]
    x = data["weeksOut"]
    x = data["strikeBox"]
    return data


def makeDataFileName(inputFileName, addTimestamp=True):
    now = datetime.now()  # current date and time
    year_str = now.strftime("%Y")
    month_str = now.strftime("%m")
    day_str = now.strftime("%d")
    time_str = now.strftime("%H%M%S")
    # making contract name to file name:
    # outputFileName = ''.join(re.findall('[a-zA-Z0-9]+', inputFileName))
    fileName = "./IBdata/" + year_str + "/" + month_str + "/" + day_str + "/" + inputFileName
    fileName.replace(' ', '_', 1)
    fileName.replace(' ', '')
    if addTimestamp:
        fileName += "_" + year_str + month_str + day_str # + "_" + time_str
    fileName += '.csv'
    makeDirectory(fileName)
    print(f"will use filename {fileName}")
    return fileName


def makeDirectory(fileName):
    # log.info(os.path.dirname(fileName))
    # log.info(os.path.exists(os.path.dirname(fileName)))

    if True or (not os.path.exists(os.path.dirname(fileName))):
        try:
            os.makedirs(os.path.dirname(fileName), exist_ok=True)
        except OSError as exc:  # Guard against race condition
            if exc.errno != errno.EEXIST:
                log.error(exc)
                #raise

stock_quote_cache = {}
def get_quote_with_delta(stockQuotes, quoteTime: datetime, delta: int):
    global stock_quote_cache
    lastTrade = None
    for iter in range(3):
        newDate = dateAdd(quoteTime, seconds=(delta+iter))
        lastTrade = stock_quote_cache.get(newDate, -1)
        if lastTrade > -1: return lastTrade
        df = stockQuotes.query("time == " + newDate)
        if df.shape[0] > 0:
            stock_quote_cache[newDate] = lastTrade
            lastTrade = df["last"].iloc[0]
            break
    return lastTrade


def dateAdd(inDate: datetime, minutes: int = 0, seconds: int = 0):
    inDate = inDate + timedelta(minutes=minutes, seconds=seconds)
    return getStrFromDate(inDate, "YYYYMMDDHHMMSS")


def getDateObjFromStr(inTime, in_format="YYYYMMDDHHMMSS"):

    if type(inTime) == np.int64 or  type(inTime) == int: inTime = str(inTime)

    if in_format == "YYYYMMDDHHMMSS":
        return datetime(int(inTime[0:4]), int(inTime[4:6]),
                    int(inTime[6:8]), int(inTime[8:10]),
                    int(inTime[10:12]), int(inTime[12:14]))
    if in_format == "YYYYMMDD":
        return datetime(int(inTime[0:4]), int(inTime[4:6]),
                    int(inTime[6:8]))
    log.error("Unexpected in format: ", in_format)

    assert False


def getStrFromDate(inTime: datetime, in_format: str="YYYYMMDDHHMMSS"):
    returnValue = None
    if in_format == "YYYYMMDDHHMMSS":
        returnValue = inTime.strftime("%Y%m%d%H%M%S")
    elif in_format == "YYYYMMDD":
        returnValue = inTime.strftime("%Y%m%d")
    elif in_format == "YYYY-MM-DD":
        returnValue = inTime.strftime("%Y-%m-%d")
    else:
        assert False

    return returnValue


# Example call
# zip_and_delete('/Users/Muthu/Development/OptionList4/IBdata/2021/11/12/test', 'FB')
def zip_and_delete(directory, stock_symbol_in_file_name,  zip_file_name, file_prefix_tuple=""):
    cwd = os.getcwd()
    os.chdir(os.path.dirname(directory))

    with zipfile.ZipFile(file=zip_file_name, mode="a", compression=zipfile.ZIP_LZMA, allowZip64=True) as zf:
        for root, foo2, filenames in os.walk(os.path.basename(directory)):
            for name in filenames:
                if stock_symbol_in_file_name in name \
                        and name.startswith(file_prefix_tuple) \
                        and name.endswith(".csv") \
                        and not name.endswith(".zip"):
                    name2 = os.path.join(root, name)
                    name2 = os.path.normpath(name2)
                    zf.write(name2, name)
                    os.remove(directory + "/" + name)
                else:
                    log.info("Skipping file: " + name)
    os.chdir(cwd)


def unzip_file(directory, zip_file_name):
    with zipfile.ZipFile(zip_file_name, 'r') as zip_ref:
        zip_ref.extractall(directory)


# send in '/Users/Muthu/Development/OptionList4/IBdata/2021/12/06/ml_cp18_AAPL.csv
# out date 20211206
def getDateStrFromPath(path):
    path_arr = path.split("/")
    path_arr.reverse()

    st = 0
    # search up 3 in path

    for xc in range(0, len(path_arr)-3):
        if len(path_arr[st + xc]) == 2 and path_arr[st].isnumeric():
            day = path_arr[st + xc]
            st = st + xc + 1
            break

    if day == 0:
        raise Exception(f"last 2 components are not integers {path}. Cant find day of month")

    if len(path_arr[st]) == 2 and path_arr[st].isnumeric():
        month = path_arr[st]
        st += 1
    else:
        raise Exception(f"can't find month {path}")

    if len(path_arr[st]) == 4 and path_arr[st].isnumeric():
        year = path_arr[st]
    else:
        raise Exception(f"Cant find year {path}")

    return f"{year}{month}{day}"


def getDateTimeStamp(format_type=1):
    now = datetime.now() # Input Eg:'2021-11-19 10:09:58.306747'
    if format_type == 1:
        # returns 100958306747
        return now.__str__()[-15:].replace(":", '').replace(".", '')
    if format_type == 2:
        # return 20211119101118520959
        return now.__str__().replace(":", '').replace(".", '')\
            .replace("-", '').replace("-", '').replace(" ", '')
    if format_type == 3:
        # 20211119
        return now.__str__()[:10].replace(":", '').replace(".", '')\
            .replace("-", '').replace("-", '').replace(" ", '')
    else:
        log.error("Unexpected.  Assumption violation")
        sys.exit(0)


def get_sec_to_4pm(in_date: datetime):
    assert type(in_date) == datetime, "Expecting data time object, but found " + in_date
    start_date = in_date
    pre_open = start_date.replace(hour=9, minute=30)
    end_date = start_date.replace(hour=16, minute=0)

    if start_date < pre_open: return (60 * 390)
    if start_date > end_date: return 0
    return (end_date - start_date).total_seconds()


def get_sec_to_expire(in_start_date: datetime, in_end_date: datetime):
    sec1 = get_sec_to_4pm(in_start_date)
    start_date_str = getStrFromDate(in_start_date, 'YYYY-MM-DD')
    in_end_date += timedelta(days=1)
    end_date_str = getStrFromDate(in_end_date, 'YYYY-MM-DD')
    if start_date_str == end_date_str:
        return sec1
    else:
        days = np.busday_count(start_date_str,  end_date_str)
        return sec1 + (days-1) * (60 * 390)

def unit_test():
    # Test get_sec_to_4_pm
    time = '2021-10-14T12:08:00'
    time2 = '2021-10-15T01:08:00'

    formatted_time1 = datetime.strptime(time, '%Y-%m-%dT%H:%M:%S')
    formatted_time2 = datetime.strptime(time2, '%Y-%m-%dT%H:%M:%S')

    msg = "Simple Test, how many seconds left in trading day after 12:30 PM"
    x = get_sec_to_4pm(getDateObjFromStr("20211119123000"))
    log.info(msg)
    log.info(x)
    assert 12600 == x, msg


    msg =  "2 dates, seconds to expire, after close  16 30 00  to same date 2021 11 19 12 30 00 (converted to 4pm)"
    x = get_sec_to_expire(getDateObjFromStr("20211119163000"), getDateObjFromStr("20211119123000"))
    log.info(msg)
    log.info(x)
    assert 0 == x, msg


    msg =  "Same day before open  08 30 00  to 2021 11 19 12 30 00 (end is convert to 4 pm)"
    x = get_sec_to_expire(getDateObjFromStr("20211119083000"), getDateObjFromStr("20211119123000"))
    log.info(msg)
    log.info(x)
    assert 23400 == x

    msg =  "Same day before open  08 30 00  to 2021 11 17 12 30 00 (end is convert to 4 pm)"
    x = get_sec_to_expire(getDateObjFromStr("20211117083000"), getDateObjFromStr("20211119123000"))
    log.info(msg)
    log.info(x)
    assert 3*23400 == x

    msg = "Not counting sat & sun"
    x = get_sec_to_expire(getDateObjFromStr("20211117083000"), getDateObjFromStr("20211121123000"))
    log.info(msg)
    log.info(x)
    assert 3*23400 == x

    msg = "Testing everyday of the week"
    assert 0*23400 == get_sec_to_expire(getDateObjFromStr("20211114083000"), getDateObjFromStr("20211114123000"))
    assert 1*23400 == get_sec_to_expire(getDateObjFromStr("20211114083000"), getDateObjFromStr("20211115123000"))
    assert 2*23400 == get_sec_to_expire(getDateObjFromStr("20211114083000"), getDateObjFromStr("20211116123000"))
    assert 3*23400 == get_sec_to_expire(getDateObjFromStr("20211114083000"), getDateObjFromStr("20211117123000"))
    assert 4*23400 == get_sec_to_expire(getDateObjFromStr("20211114083000"), getDateObjFromStr("20211118123000"))
    assert 5*23400 == get_sec_to_expire(getDateObjFromStr("20211114083000"), getDateObjFromStr("20211119123000"))
    assert 5*23400 == get_sec_to_expire(getDateObjFromStr("20211114083000"), getDateObjFromStr("20211120123000"))
    assert 5*23400 == get_sec_to_expire(getDateObjFromStr("20211114083000"), getDateObjFromStr("20211121123000"))
    assert 6*23400 == get_sec_to_expire(getDateObjFromStr("20211114083000"), getDateObjFromStr("20211122123000"))

def compressCSVFiles(dir):
    ctr: int = 0
    for in_file_name in glob.glob(dir + "/*21*_*21*_*.csv"):
        ctr += 1
        out_file_name = in_file_name[0: in_file_name.rfind('_')] + ".csv"
        out_file_exists = os.path.exists(out_file_name)
        in_file = open(in_file_name, "r").readlines()
        if out_file_exists:
            in_file2 = in_file[1:]
            in_file = in_file2
        print(ctr, ": ", in_file_name, "(", len(in_file), ")=>", out_file_name)
        with open(out_file_name, 'a') as out_file:
            for line in in_file:
                out_file.write(line)
        os.remove(in_file_name)
    print("In directory [", dir, "] processed/deleted file count: [", ctr, "]")


if __name__ == "__main__":
    if len(sys.argv) > 1: compressCSVFiles(sys.argv[1])
    # log = setup_logging("FileUtil.log")
    # unit_test()
    pass

