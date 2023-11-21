import concurrent.futures
import os
import factors as fc
import pandas as pd
import numpy as np


def RSJ_Positio(df, m=13):
    rsj = fc.RSJ(df, m)
    position = pd.DataFrame(index=rsj.index, columns=['position']).fillna(0)
    position.loc[rsj < 0] = 1
    position.loc[rsj > 0] = 0
    return position

def DMI_Position(df, n=14, m=6):
    dmi = fc.DMI(df, n, m)
    position = pd.DataFrame(index=dmi.index, columns=['position']).fillna(0)
    position.loc[(dmi > 0) & (dmi > dmi.shift())] = 1
    position.loc[(dmi < 0) & (dmi < dmi.shift())] = 0
    return position

def CO_Position(df, periods_short=3, periods_long=10):
    ch_osc, SMA_90 = fc.chaikin_oscillator(df, periods_short, periods_long)
    position = pd.DataFrame(index=ch_osc.index, columns=['position']).fillna(0)
    position.loc[(ch_osc > 0) & (ch_osc.shift() < 0) & (df.close > SMA_90)] = 1
    position.loc[(ch_osc < 0) & (ch_osc.shift() > 0) & (df.close < SMA_90)] = 0
    return position

def OBV_Position(df):
    obv, adjobv = fc.OBV(df)
    position = pd.DataFrame(index=obv.index, columns=['position']).fillna(0)
    position.loc[(df.close.diff() > 0) & (obv.diff() > 0)] = 1
    position.loc[(df.close.diff() < 0) & (obv.diff() < 0)] = 0
    return position