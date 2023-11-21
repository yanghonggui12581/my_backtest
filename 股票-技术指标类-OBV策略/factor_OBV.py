

# 因子定义
# 择时，信号生成
import pandas as pd
import numpy as np
import dataGet_Func as dataGet
import output_file_Func as output


def calculate_OBV(df):
    # OBV指标的计算方法是：如果当日收盘价高于前一日收盘价，则将当日成交量加到OBV上；
    # 如果当日收盘价低于前一日收盘价，则将当日成交量减去OBV。如果当日收盘价等于前一日收盘价，则OBV保持不变。
    # AdjOBV的计算方法是：首先计算原始的OBV值，然后乘以一个调整因子。调整因子的计算公式为：
    # 调整因子 = （当前股价 - 前一日股价） / 前一日股价

    close = df['close']
    volume = df['volume']
    difClose = close.diff()
    difClose[0] = 0
    OBV = (((difClose >= 0) * 2 - 1) * volume).cumsum()
    df['OBV'] = OBV
    adjobv = ((close - df.low) - (df.high - close)) / (df.high - df.low) * volume
    adjobv_cumsum = adjobv.cumsum()
    df['ADJOBV'] = adjobv_cumsum
    df['OBV_signal'] = df['OBV'].diff()
    # 确认趋势并生成交易信号
    df['Signal'] = None
    df.loc[(df['close'].diff() > 0) & (df['OBV_signal'] > 0), 'Signal'] = 1
    df.loc[(df['close'].diff() < 0) & (df['OBV_signal'] < 0), 'Signal'] = 0

    return df



if __name__ == "__main__" :
    # # 先根据相应的逻辑，生成因子
    # TRD_Dalyr = dataGet.read_file("./data", 'TRD_Dalyr.csv')
    # # 修正原始数据的命名
    # TRD_Dalyr.columns = ['date', 'open', 'high', 'low', 'close', 'volume']
    # if not pd.api.types.is_datetime64_any_dtype(TRD_Dalyr.index):
    #     # 将'date'列设置为索引
    #     TRD_Dalyr = TRD_Dalyr.set_index('date')
    # output.write_file(TRD_Dalyr, "./data", 'TRD_Dalyr.pickle')

    TRD_Dalyr = dataGet.read_file("./data", 'new_TRD_Dalyr.csv')
    OBV_data = calculate_OBV(TRD_Dalyr)
    OBV_data = OBV_data.set_index('date')
    output.write_file(OBV_data, "./data", 'OBV_data.csv')
















