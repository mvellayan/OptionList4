from pprint import pprint
import sys

from ib_insync import *

from utils import FileUtil, IBUtil

#
# see: https://github.com/erdewit/ib_insync
config = {}
ib = IB()

def main(configFileName):
    global config
    config = FileUtil.readConfig(configFileName)

    print("Connecting to ip [", config["tws_host"], "] port[", config["tws_port"], "] clientId [", config["tws_port"], "]")
    try:
        ib.connect(config["tws_host"], config["tws_port"], clientId=config["tws_port"])
    except BaseException as err:
        print(f"Unexpected {err=}, {type(err)=}")
        raise NameError("Cannot connect to IB")

    print("Connection Status: ", ib.isConnected())

    IBUtil.pull_options_list(ib, config)



if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\n\nUsage: collect_data.py <config_file.yml>\n\n")
        sys.exit(0)
    else:
        print("using config file [" + sys.argv[1] + "]")

    main(sys.argv[1])
