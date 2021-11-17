import errno
import json
import os
import re
from datetime import datetime, timedelta

from ib_insync import *

def p(*args):
    print(datetime.now().strftime("%Y%m%d %H:%M:%S") + ": ", *args)

def readConfig(fileName):
    data = {}
    try:
        # open file and load data
        f = open(fileName, 'r')
        data = json.load(f)
        # print("\n\nINFO: Parameter File:")
        # pprint(data)
        f.close()
    except OSError:
        print('cannot open file', fileName)
        sys.exit(1)
    # verify fields exist
    # print("\nINFO: parameters Check:")
    # testing:
    x = data["tws_port"]
    x = data["file_flush_seconds"]
    x = data["stock"]
    x = data["weeksOut"]
    x = data["strikeBox"]
    print("\n")
    return data


def makeDataFileName(inputFileName, addTimestamp = True):
    now = datetime.now()  # current date and time
    year_str = now.strftime("%Y")
    month_str = now.strftime("%m")
    day_str = now.strftime("%d")
    time_str = now.strftime("%H%M%S")
    #making contract name to file name:
    outputFileName = ''.join(re.findall('[a-zA-Z0-9]+', inputFileName))
    fileName = "./IBdata/" + year_str + "/" + month_str + "/" + day_str + "/" + outputFileName
    if addTimestamp:
        fileName += "_"  + year_str + month_str + day_str + "_" + time_str
    fileName += '.csv'
    makeDirectory(fileName)
    return fileName


def makeDirectory(fileName):
    if not os.path.exists(os.path.dirname(fileName)):
        try:
            os.makedirs(os.path.dirname(fileName))
        except OSError as exc:  # Guard against race condition
            if exc.errno != errno.EEXIST:
                print ("ERROR")
                print ( exc )
                #raise

def get_quote_with_delta(stockQuotes, quoteTime, delta: int):
    last = None
    for iter in range(3):
        df = stockQuotes.query("Time == " + dateAdd(quoteTime, seconds=(delta+iter)))
        if df.shape[0] > 0:
            last = df["Last"].iloc[0]
            break
    return last


def dateAdd(inDate: str, minutes: int = 0, seconds: int = 0):
    dateObj :datetime = getDateObj(inDate)
    dateObj = dateObj + timedelta(minutes=minutes, seconds=seconds)
    return dateObj.strftime("%Y%m%d%H%M%S")


def getDateObj(inTime):  #input can be string or int

    if type(inTime) == int:
        inTime = str(inTime)
    elif type(inTime) == str:
        pass
    else:
        print("Unexpected parameter type: ", type(inTime))
        sys.exit(0)

    return datetime(int(inTime[0:4]), int(inTime[4:6]),
                    int(inTime[6:8]), int(inTime[8:10]),
                    int(inTime[10:12]), int(inTime[12:14]))


