from pprint import pprint
import sys

from ib_insync import *

from utils import FileUtil, IBUtil

#
# see: https://github.com/erdewit/ib_insync
from utils.IBUtil import get_options_list_file_name

config = {}
ib = IB()

def main(config):

    print(f"Connecting to ip [{config['tws']['host']}] port[{config['tws']['port']}]")
    try:
        ib.connect(config['tws']['host'], config['tws']['port'], clientId=config['tws']['port'])
    except BaseException as err:
        print(f"Unexpected {err=}, {type(err)=}")
        raise NameError("Cannot connect to IB")

    print("Connection Status: ", ib.isConnected())

    IBUtil.pull_options_list(ib, config, get_options_list_file_name(config))



if __name__ == "__main__":

    config = FileUtil.readConfig(sys.argv[1])

    main(config)
