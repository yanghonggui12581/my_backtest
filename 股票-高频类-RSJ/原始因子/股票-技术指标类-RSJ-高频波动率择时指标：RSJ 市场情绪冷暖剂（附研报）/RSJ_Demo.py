
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

start_date = '2018-11-23'
end_date = '2021-05-25'
index_code = '000300.XSHG'
# 获取指数5分钟数据
# stock = get_price(index_code,start_date=start_date,end_date=pd.to_datetime(end_date)+datetime.timedelta(days=1),frequency='5min',fields=['close'])
stock = pd.read_csv('data/hs300.csv')
stock = stock.set_index('date')[['close']]
stock.index = pd.DatetimeIndex(stock.index)
# 计算5分钟收益率
stock['ret'] = stock['close'].pct_change()
# 获取指数日数据
# stock_day = get_price(index_code,start_date=start_date,end_date=end_date,frequency='D',fields=['close'])
# stock_day.to_csv('data/stock_day.csv')
stock_day = pd.read_csv('data/stock_day.csv',index_col=0)
# 计算未来一天的收益率


# 计算rsj 倒数第13根到倒数第一根，即13:55至14:55
m=13
rsj = stock['ret'].groupby(stock.index.date).apply(
        lambda x: ((x[-m:-1][x[-m:-1] > 0]**2).sum()-(x[-m:-1][x[-m:-1] < 0]**2).sum())/(x[-m:-1]**2).sum())

# stock_day['rsj'] = rsj.values
rsj.index = list(str(i) for i in rsj.index)
stock_day = pd.merge(stock_day, pd.DataFrame(rsj).rename(columns={'ret': 'rsj'}), left_index=True, right_index=True)
stock_day['future_ret'] = stock_day['close'].pct_change(1).shift(-1)
stock_day['symbol'] = (stock_day['rsj'] < 0).astype('int')

result = dict()
result['long'] = ((stock_day['future_ret']*(-1)*np.sign(stock_day['rsj'].fillna(0)).replace(1, 0))+1).cumprod()
result['short'] = ((stock_day['future_ret']*(-1)*np.sign(stock_day['rsj'].fillna(0)).replace(-1, 0))+1).cumprod()
result['long_short'] = ((stock_day['future_ret']*(-1)*np.sign(stock_day['rsj'].fillna(0)))+1).cumprod()
result['original'] = (stock_day['future_ret']+1).cumprod()
result = pd.DataFrame(result)
result1=result.pct_change()
result.to_csv("result/output.csv")
N = 252
df_nav = result.dropna(axis=0, how='all')
yret = df_nav.iloc[-1] ** (N / len(df_nav))-1
Sharp = df_nav.pct_change().mean() / df_nav.pct_change().std() * np.sqrt(N)
df0 = df_nav.shift(1).fillna(1)
MDD = (1 - df0 / df0.cummax()).max()
Calmar = yret / MDD

df_nav.columns = [result.columns[i]
              + '\nyret:' + "%.2f%%" % (yret[i] * 100)
              + '  Sharp:{}'.format(round(Sharp[i], 2))
              + '\nMDD:' + "%.2f%%" % (MDD[i] * 100)
              + '  Calmar:{}'.format(round(Calmar[i], 2))
              for i in range(result.shape[1])
              ]
df_nav.plot(figsize=(10, 8), title=index_code)
plt.legend(bbox_to_anchor=(1.05, 0), loc=3, borderaxespad=0)
plt.savefig('result/回测结果.png')
plt.show()

