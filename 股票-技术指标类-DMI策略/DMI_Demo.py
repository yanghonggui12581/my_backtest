# coding: utf-8
# Python 3.6


import pandas as pd
import numpy as np


def dmi(df, n=14, m=6):
    tr = pd.Series(np.vstack([df.high - df.low, (df.high - df.close.shift()).abs(),
                              (df.low - df.close.shift()).abs()]).max(axis=0), index=df.index)
    trz = tr.rolling(n).sum()
    _m = pd.DataFrame()
    _m['hd'] = df.high - df.high.shift()
    _m['ld'] = df.low.shift() - df.low
    _m['mp'] = _m.apply(lambda x: x.hd if x.hd > 0 and x.hd > x.ld else 0, axis=1)
    _m['mm'] = _m.apply(lambda x: x.ld if x.ld > 0 and x.hd < x.ld else 0, axis=1)
    _m['dmp'] = _m.mp.rolling(n).sum()
    _m['dmm'] = _m.mm.rolling(n).sum()
    _dmi = pd.DataFrame()
    _dmi['date'] = df.date
    _dmi['open'] = df.open
    _dmi['close'] = df.close
    _dmi['pdi'] = 100 * _m.dmp.div(trz)
    _dmi['mdi'] = 100 * _m.dmm.div(trz)
    _dmi['adx'] = ((_dmi.mdi - _dmi.pdi).abs() / (_dmi.mdi + _dmi.pdi) * 100).rolling(m).mean()
    _dmi['adxr'] = (_dmi.adx + _dmi.adx.shift(m)) / 2
    _dmi.set_index(df.index)
    _dmi = _dmi.dropna()

    _dmi['dmi'] = _dmi['pdi'] - _dmi['mdi']
    _dmi['side'] = 0
    _dmi = _dmi.reset_index(drop = True)

    c = len(_dmi)
    for i in range(c):
        if i > 1 and i + 1 < c:
            if _dmi.loc[i,'dmi'] > 0 and _dmi.loc[i,'dmi'] > _dmi.loc[i-1,'dmi']:
                _dmi['side'].values[i] = 1

            if _dmi.loc[i,'dmi'] < 0 and _dmi.loc[i,'dmi'] < _dmi.loc[i-1,'dmi']:
                _dmi['side'].values[i] = 0

    return _dmi


stock = pd.read_csv('./data/TRD_Dalyr.csv', engine='python')
stock.columns = ['date', 'open', 'high', 'low', 'close', 'volume']
df = dmi(stock)
df['ret'] = df.close / df.close.shift(1) - 1
df['position'] = df['side'].shift(1)
# df['position'].fillna(method='ffill', inplace=True)
# df['position'].fillna(0, inplace=True)
# 根据交易信号和仓位计算策略的每日收益率
df.loc[df.index[0], 'capital_ret'] = 0
# 今天开盘新买入的position在今天的涨幅(扣除手续费)
df.loc[df['position'] > df['position'].shift(1), 'capital_ret'] = \
    (df.close / df.open - 1)
# 卖出同理
df.loc[df['position'] < df['position'].shift(1), 'capital_ret'] = \
    (df.open / df.close.shift(1) - 1)
# 当仓位不变时,当天的capital是当天的change * position
df.loc[df['position'] == df['position'].shift(1), 'capital_ret'] = \
    df['ret'] * df['position']
# 计算标的、策略、指数的累计收益率
df['策略净值'] = (df.capital_ret + 1.0).cumprod()
df.to_csv('./result/result.csv', index = False)