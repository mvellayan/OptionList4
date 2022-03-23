model_title = [
    "1: In the money (ITM) > 1  TV [ 2.3, INV ]  TV [ -inf, inf ]  Theta [ 1 - inf ]\nTV [ -inf, 1 ]  and net [ 0, inf ] ",
    "2: Out of the money (OTM) by > 1.  TV [ 2.3, INV ]  TV [ -inf, inf ]  Theta [ 1 - inf ]\nTV [ -inf, 1 ]  and net [ 0, inf ] ",
    "3: Out of the money (OTM) by > 2.  TV [ 2.3, INV ]  TV [ -inf, inf ]  Theta [ 1 - inf ]\nTV [ -inf, 1 ]  and net [ 0, inf ] ",
    "4: Out of the money (OTM) by > 3.  TV [ 2.3, INV ]  TV [ -inf, inf ]  Theta [ 1 - inf ]\nTV [ -inf, 1 ]  and net [ 0, inf ] ",
    "5: Out of the money (OTM) by > 4.  TV [ 2.3, INV ]  TV [ -inf, inf ]  Theta [ 1 - inf ]\nTV [ -inf, 1 ]  and net [ 0, inf ] ",
    "6: Out of the money (OTM) by > 1.  TV [ 2.8, INV ]  TV [ -inf, inf ]  Theta [ 1 - inf ]\nTV [ -inf, 1 ]  and net [ 0, inf ] ",
    "7: Out of the money (OTM) by > 1.  TV [ 1.8, INV ]  TV [ -inf, inf ]  Theta [ 1 - inf ]\nTV [ -inf, 1 ]  and net [ 0, inf ] ",
]

def get_model_count():
    return len(model_title)

def get_description(model_no):
    return model_title[model_no-1]

def open_position(model_no, open_stock_bid, open_stock_ask, open_option_bid, open_option_ask, open_tv, open_iv, open_theta, strike):
    if model_no == 1:
        return (open_tv > 2.3) and (open_theta > 1) and (strike- 1 ) > open_stock_ask
    elif model_no == 2:
        return (open_tv > 2.3) and (open_theta > 1) and (strike + 1) < open_stock_ask
    elif model_no == 3:
        return (open_tv > 2.3) and (open_theta > 1) and (strike + 2) < open_stock_ask
    elif model_no == 4:
        return (open_tv > 2.3) and (open_theta > 1) and (strike + 3) < open_stock_ask
    elif model_no == 5:
        return (open_tv > 2.3) and (open_theta > 1) and (strike + 4) < open_stock_ask
    elif model_no == 6:
        return (open_tv > 2.8) and (open_theta > 1) and (strike+1) < open_stock_ask
    elif model_no == 7:
        return (open_tv > 1.8) and (open_theta > 1) and (strike+1) < open_stock_ask

    else:
        print(model_no, open_stock_bid, open_stock_ask, open_option_bid, open_option_ask, open_tv, open_iv, open_theta, strike)
        assert False, "Unexpected model number in open_position"


def close_position(model_no, close_tv, close_iv, close_theta, strike, net_stock, net_option):

    if model_no in(1, 2, 3, 4, 5, 6, 7):
        return close_tv < 1 and (net_stock + net_option > 0)
    else:
        print(model_no, close_tv, close_iv, close_theta, strike, net_stock, net_option)
        assert False, "Unexpected model number in close_position"


    return False