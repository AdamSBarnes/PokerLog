import pandas as pd



def highlight_negative_return(val):
    if val < 1:
        return "background-color: lightcoral"
    else:
        return ""
