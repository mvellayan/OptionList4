def get_short_title(model_no):
    model_title= [
        "OTM1_TV10-23_TH1-",
        "ITM1_TV10-23_TH1-",
    ]
    return model_title[model_no - 1]

def get_description(model_no):
    model_title = [
        "Out of the money by $1 or more. TV(-1) TV(1-2.3) Theta (>1)",
        "In the money by $1 or more TV(+1) TV(1-2.3) Theta (>1),"
    ]
    return model_title[model_no-1]

def open_position(model_no, open_stock_bid, open_stock_ask, open_option_bid, open_option_ask, open_tv, open_iv, open_theta, strike):
    if model_no == 1:
        return (open_tv > 2.3) and (open_theta > 1) and (strike-1) > open_stock_ask
    elif model_no == 2:
        return (open_tv > 2.3) and (open_theta > 1) and (strike+1) < open_stock_ask
    else:
        print(model_no, open_stock_bid, open_stock_ask, open_option_bid, open_option_ask, open_tv, open_iv, open_theta, strike)
        assert False, "Unexpected model number in open_position"


def close_position(model_no, close_tv, close_iv, close_theta, strike, net_stock, net_option):

    if model_no in(1,2):
        return close_tv < 1 and (net_stock + net_option > 0)
    else:
        print(model_no, close_tv, close_iv, close_theta, strike, net_stock, net_option)
        assert False, "Unexpected model number in close_position"


    return False