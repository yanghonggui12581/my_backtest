

# 因子定义
# 择时，信号生成
import pandas as pd
import numpy as np
import dataGet_Func as dataGet
import output_file_Func as output


def chaikin_oscillator(data, periods_short=3, periods_long=10, high_col='High',
                       low_col='Low', close_col='Close', vol_col='Volume'):
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

    # 修正原始数据的命名
    # data = data.rename(columns={'Date': 'date'})
    # data = data.rename(columns={'Close': 'close'})

    return data  # 返回更新后的数据集

# 根据以上指标构建一个多空逻辑，即
# 当前无仓位，Chaikin Oscillator上穿0，且股价高于90天移动平均，做多
# 当前持仓，Chaikin Oscillator下穿0，且股价低于90天移动平均，平仓
# 可以根据原来的数据，先生成因子，存在一个csv文件或者xlsx文件中



if __name__ == "__main__" :
    # 先根据相应的逻辑，生成因子
    # GOOG = dataGet.read_file("./data", 'co_data.csv')
    # if not pd.api.types.is_datetime64_any_dtype(GOOG.index):
    #     # 将'date'列设置为索引
    #     GOOG = GOOG.set_index('date')
    # output.write_file(GOOG, "./data", 'GOOG.pickle', index=False)

    goog = dataGet.read_file("./data", 'GOOG.csv')
    co_data = chaikin_oscillator(goog)
    output.write_file(co_data, "./data", 'co_data.csv')
















