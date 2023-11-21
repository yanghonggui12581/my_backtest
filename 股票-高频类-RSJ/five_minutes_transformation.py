import dataGet_Func as dataGet
import pandas as pd

pickle_df = dataGet.read_file("../all_factors/data", "2018_002268_trade_pickle4.bz2")
five_minute_data = pd.DataFrame(columns=['date', 'open', 'close', 'vol'])
interval_start_time = pickle_df['date'].iloc[0]
open_price = pickle_df['price'].iloc[0]
close_price = open_price
volume = 0
for _, row in pickle_df.iterrows():
    timestamp = row['date']
    price = row['price']
    tick_volume = row['vol']

    if timestamp >= interval_start_time + pd.Timedelta(minutes=5):
        # 生成一个区间的数据
        interval_data = pd.DataFrame([[interval_start_time, open_price, close_price, volume]],
                                     columns=['date', 'open', 'close', 'vol'])

        # 将区间数据添加到每五分钟的数据DataFrame中
        five_minute_data = five_minute_data.append(interval_data, ignore_index=True)

        # 更新区间起始时间、开盘价和收盘价
        interval_start_time = timestamp
        open_price = close_price if pd.isna(price) else price
        close_price = open_price
        volume = tick_volume
    else:
        # 更新收盘价和交易量
        close_price = close_price if pd.isna(price) else price
        volume += tick_volume

    # 添加最后一个区间的数据
interval_data = pd.DataFrame([[interval_start_time, open_price, close_price, volume]],
                             columns=['date', 'open', 'close', 'vol'])
five_minute_data = five_minute_data.append(interval_data, ignore_index=True)

five_minute_data.to_pickle("002268_five_minute.bz2", compression='bz2')
