

# 因子定义
# 择时，信号生成
import pandas as pd
import numpy as np
import dataGet_Func as dataGet
import output_file_Func as output


def dmi(df, n=14, m=6):
    """
    Calculate the Directional Movement Index (DMI) and generate trading signals based on the DMI values.

    Args:
        df (pd.DataFrame): DataFrame containing OHLC data for a particular asset.
        n (int): Number of periods to use for rolling calculations. Default is 14.
        m (int): Number of periods to use for calculating ADXR. Default is 6.

    Returns:
        pd.DataFrame: DataFrame containing the calculated DMI values and trading signals.
    """
    # Check for missing values and raise an error if any are found
    if df.isnull().values.any():
        raise ValueError("Input DataFrame contains missing values.")
    # Calculate directional movement
    movement_data = pd.DataFrame()
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
    dmi['date'] = df['date']
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

    # Generate trading signals based on DMI values
    dmi['side'] = np.where((dmi['dmi'] > 0) & (dmi['dmi'] > dmi['dmi'].shift()), 1,
                           np.where((dmi['dmi'] < 0) & (dmi['dmi'] < dmi['dmi'].shift()), 0, 0))
    # Fill NaN values in 'side' column with 0
    dmi.loc[dmi['adxr'].shift(1).isnull(), 'side'] = 0
    # dmi = dmi.dropna().reset_index(drop=True)

    return dmi


# 根据以上指标构建一个多空逻辑，即
# 当前无仓位，_dmi.loc[i,'dmi'] > 0 and _dmi.loc[i,'dmi'] > _dmi.loc[i-1,'dmi']，做多
# 当前持仓，_dmi.loc[i,'dmi'] < 0 and _dmi.loc[i,'dmi'] < _dmi.loc[i-1,'dmi']，平仓
# 可以根据原来的数据，先生成因子，存在一个csv文件或者xlsx文件中



if __name__ == "__main__" :
    # # 先根据相应的逻辑，生成因子
    # TRD_Dalyr = dataGet.read_file("./data", 'TRD_Dalyr.csv')
    # # 修正原始数据的命名
    # TRD_Dalyr = TRD_Dalyr.rename(columns={'Trddt': 'date'})
    # TRD_Dalyr = TRD_Dalyr.rename(columns={'Opnprc': 'open'})
    # TRD_Dalyr = TRD_Dalyr.rename(columns={'Hiprc': 'high'})
    # TRD_Dalyr = TRD_Dalyr.rename(columns={'Loprc': 'low'})
    # TRD_Dalyr = TRD_Dalyr.rename(columns={'Clsprc': 'close'})
    # TRD_Dalyr = TRD_Dalyr.rename(columns={'Dnshrtrd': 'vol'})
    # if not pd.api.types.is_datetime64_any_dtype(TRD_Dalyr.index):
    #     # 将'date'列设置为索引
    #     TRD_Dalyr = TRD_Dalyr.set_index('date')
    # output.write_file(TRD_Dalyr, "./data", 'new_TRD_Dalyr.csv')

    TRD_Dalyr = dataGet.read_file("./data", 'new_TRD_Dalyr.csv')
    DMI_data = dmi(TRD_Dalyr)
    DMI_data = DMI_data.set_index('date')
    output.write_file(DMI_data, "./data", 'DMI_data.csv')
















