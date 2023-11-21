
import os
import pandas as pd
import numpy as np


def RSJ(df, m=13):
    # 需要导入分钟级别的数据
    # pct_change计算相邻值的变化
    ret = df['close'].pct_change()  # 计算股价的变化率
    ret.name = 'ret'  # 为Series指定名称

    # 计算RSJ指标
    rsj = ret.groupby(ret.index.date).apply(
        lambda x: ((x[-m:-1][x[-m:-1] > 0] ** 2).sum() - (x[-m:-1][x[-m:-1] < 0] ** 2).sum()) / (x[-m:-1] ** 2).sum()
    )
    # 将计算得到的rsj存储在一个Series中
    rsj.name = 'rsj'  # 指定Series的名称为'rsj'
    # 确认趋势并生成交易信号
    return rsj

def DMI(df, n=14, m=6):

    # Check for missing values and raise an error if any are found
    if df.isnull().values.any():
        raise ValueError("Input DataFrame contains missing values.")
    # Calculate directional movement
    movement_data = pd.DataFrame(index=df.index)
    movement_data['hd'] = df['high'] - df['high'].shift()
    movement_data['ld'] = df['low'].shift() - df['low']
    movement_data['mp'] = np.where((movement_data['hd'] > 0) & (movement_data['hd'] > movement_data['ld']),
                                   movement_data['hd'], 0)
    movement_data['mm'] = np.where((movement_data['ld'] > 0) & (movement_data['hd'] < movement_data['ld']),
                                   movement_data['ld'], 0)
    movement_data['dmp'] = movement_data['mp'].rolling(n).sum()
    movement_data['dmm'] = movement_data['mm'].rolling(n).sum()
    # Calculate True Range and other DMI components
    dmi = pd.DataFrame(index=df.index)
    dmi['open'] = df['open']
    dmi['close'] = df['close']
    tr = pd.Series(np.vstack([df['high'] - df['low'], (df['high'] - df['close'].shift()).abs(),
                              (df['low'] - df['close'].shift()).abs()]).max(axis=0), index=df.index)
    trz = tr.rolling(n).sum()
    dmi['pdi'] = 100 * movement_data['dmp'].div(trz)
    dmi['mdi'] = 100 * movement_data['dmm'].div(trz)
    dmi['adx'] = ((dmi['mdi'] - dmi['pdi']).abs() / (dmi['mdi'] + dmi['pdi']) * 100).rolling(m).mean()
    dmi['adxr'] = (dmi['adx'] + dmi['adx'].shift(m)) / 2
    dmi['dmi'] = dmi['pdi'] - dmi['mdi']

    # # Generate trading signals based on DMI values
    # dmi['side'] = np.where((dmi['dmi'] > 0) & (dmi['dmi'] > dmi['dmi'].shift()), 1,
    #                        np.where((dmi['dmi'] < 0) & (dmi['dmi'] < dmi['dmi'].shift()), 0, 0))
    # # Fill NaN values in 'side' column with 0
    # dmi.loc[dmi['adxr'].shift(1).isnull(), 'side'] = 0
    # # dmi = dmi.dropna().reset_index(drop=True)

    dmi.loc[dmi['adxr'].shift(1).isnull(), 'dmi'] = None

    return dmi.dmi

def chaikin_oscillator(data, periods_short=3, periods_long=10, high_col='high',
                       low_col='low', close_col='close', vol_col='vol'):
    ac = pd.Series(dtype='float64')  # 创建一个空的Series来存储ac值

    val_last = 0  # 初始化上一个周期的ac值为0

    for index, row in data.iterrows():
        if row[high_col] != row[low_col]:  # 检查最高价和最低价是否相等，避免除以零的情况
            val = val_last + ((row[close_col] - row[low_col]) - (row[high_col] - row[close_col])) / (
                        row[high_col] - row[low_col]) * row[vol_col]
        else:
            val = val_last  # 如果最高价和最低价相等，则当前周期的ac值与上一个周期相同
        ac.at[index] = val  # 将计算得到的ac值存入Series中
        val_last = val  # 更新上一个周期的ac值为当前周期的值

    # 使用指数加权移动平均（Exponential Moving Average，EMA）计算ac的长期和短期移动平均线
    ema_long = ac.ewm(span=periods_long, adjust=False).mean()  # 计算长期EMA
    ema_short = ac.ewm(span=periods_short, adjust=False).mean()  # 计算短期EMA

    # 计算Chaikin Oscillator，并将其存储在数据集的新列'ch_osc'中
    data['ch_osc'] = ema_short - ema_long

    # 计算收盘价的90日简单移动平均线，并将其存储在新列'SMA_90'中
    data['SMA_90'] = data[close_col].rolling(window=90).mean().shift(1)

    return data.ch_osc, data.SMA_90   # 返回更新后的数据集


def OBV(df):
    # OBV指标的计算方法是：如果当日收盘价高于前一日收盘价，则将当日成交量加到OBV上；
    # 如果当日收盘价低于前一日收盘价，则将当日成交量减去OBV。如果当日收盘价等于前一日收盘价，则OBV保持不变。
    # AdjOBV的计算方法是：首先计算原始的OBV值，然后乘以一个调整因子。调整因子的计算公式为：
    # 调整因子 = （当前股价 - 前一日股价） / 前一日股价

    close = df['close']
    volume = df['vol']
    difClose = close.diff()
    difClose.iloc[0] = 0
    OBV = (((difClose >= 0) * 2 - 1) * volume).cumsum()
    df['obv'] = OBV
    adjobv = ((close - df['low']) - (df['high'] - close)) / (df['high'] - df['low']) * volume
    adjobv_cumsum = adjobv.cumsum()
    df['adjobv'] = OBV * adjobv_cumsum

    return df.obv, df.adjobv  # 返回更新后的数据集
