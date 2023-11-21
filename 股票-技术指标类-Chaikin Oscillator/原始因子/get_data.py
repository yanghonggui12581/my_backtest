import pandas as pd
import yfinance as yf
#%%
GOOG=yf.download("GOOG",start="2015-01-01",end="2020-01-01",period="1d")
GOOG.to_csv("./code/data/GOOG.csv")