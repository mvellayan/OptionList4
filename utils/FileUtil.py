import csv
import errno
import json
import os
import re
import sys
from datetime import datetime
from pprint import pprint

from ib_insync import *

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




def getFileName(inputFileName, addTimestamp = True):
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
