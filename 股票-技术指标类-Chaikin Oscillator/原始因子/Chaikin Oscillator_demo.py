"""
Chaikin Oscillator
Params:
    data: pandas DataFrame
	periods_short: period for the shorter EMA (3 days recommended)
	periods_long: period for the longer EMA (10 days recommended)
	high_col: the name of the HIGH values column
	low_col: the name of the LOW values column
	close_col: the name of the CLOSE values column
	vol_col: the name of the VOL values column

Returns:
    copy of 'data' DataFrame with 'ch_osc' column added
"""
#%%
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
#%%获取数据
goog=pd.read_csv("./data/GOOG.csv")
#%%
def chaikin_oscillator(data, periods_short=3, periods_long=10, high_col='High',
                       low_col='Low', close_col='Close', vol_col='Volume'):
    ac = pd.Series([],dtype='float64')
    val_last = 0

    for index, row in data.iterrows():
        if row[high_col] != row[low_col]:
            val = val_last + ((row[close_col] - row[low_col]) - (row[high_col] - row[close_col])) / (
                        row[high_col] - row[low_col]) * row[vol_col]
        else:
            val = val_last
        ac[index]=val
        val_last = val

    ema_long = ac.ewm(ignore_na=False, min_periods=0, com=periods_long, adjust=True).mean()
    ema_short = ac.ewm(ignore_na=False, min_periods=0, com=periods_short, adjust=True).mean()
    data['ch_osc'] = ema_short - ema_long

    data['SMA_90'] = data.Close.rolling(90).mean().shift(1)


    return data

#goog=chaikin_oscillator(goog)
#%%
def Strategy(pdatas, indicator_name,close_name,lossratio=999):

    pdatas = pdatas.copy()

    pdatas=chaikin_oscillator(pdatas)
    pdatas['position'] = 0  # 记录持仓
    pdatas['flag'] = 0  # 记录买卖

    pricein = []
    priceout = []
    price_in = 1
    for i in range(90, pdatas.shape[0] - 1):

    # 当前无仓位，Chaikin Oscillator上穿0，且股价高于90天移动平均，做多
        if (pdatas[indicator_name][i - 1] < 0) & (pdatas[indicator_name][i] > 0) & (pdatas[close_name][i]>pdatas.SMA_90[i]) & (pdatas.position[i] == 0):
            pdatas.loc[i, 'flag'] = 1
            pdatas.loc[i + 1, 'position'] = 1

            date_in = pdatas.Date[i]
            price_in = pdatas.loc[i, close_name]
            pricein.append([date_in, price_in])

        # 当前持仓，下跌超出止损率，止损
        elif (pdatas.position[i] == 1) & (pdatas[close_name][i] / price_in - 1 < -lossratio):
            pdatas.loc[i, 'flag'] = -1
            pdatas.loc[i + 1, 'position'] = 0

            priceout.append([pdatas.Date[i], pdatas.loc[i, close_name]])

        # 当前持仓，Chaikin Oscillator下穿0，且股价低于90天移动平均，平仓
        elif (pdatas[indicator_name][i - 1] > 0) & (pdatas[close_name][i]<pdatas.SMA_90[i]) & (pdatas[indicator_name][i] < 0) & (pdatas.position[i] == 1):
            pdatas.loc[i, 'flag'] = -1
            pdatas.loc[i + 1, 'position'] = 0

            priceout.append([pdatas.Date[i], pdatas.loc[i, close_name]])

        # 其他情况，保持之前仓位不变
        else:
            pdatas.loc[i + 1, 'position'] = pdatas.loc[i, 'position']

    p1 = pd.DataFrame(pricein, columns=['datebuy', 'pricebuy'])
    p2 = pd.DataFrame(priceout, columns=['datesell', 'pricesell'])

    transactions = pd.concat([p1, p2], axis=1)

    pdatas = pdatas.reset_index(drop=True)
    pdatas['ret'] = pdatas[close_name].pct_change(1).fillna(0)
    pdatas['nav'] = (1 + pdatas.ret * pdatas.position).cumprod()
    pdatas['benchmark'] = pdatas[close_name] / pdatas[close_name][0]

    stats, result_peryear = performace(transactions, pdatas)

    return stats, result_peryear, transactions, pdatas

#%%策略评价函数
"""
nav为策略净值，benchmark为基准净值，RS为相对强弱曲线，可以看出，策略表现并不稳定。
"""
def performace(transactions, strategy):
    # strategy = pdatas.copy();
    N = 250

    # 年化收益率
    rety = strategy.nav[strategy.shape[0] - 1] ** (N / strategy.shape[0]) - 1

    # 夏普比
    Sharp = (strategy.ret * strategy.position).mean() / (strategy.ret * strategy.position).std() * np.sqrt(N)

    # 胜率
    VictoryRatio = ((transactions.pricesell - transactions.pricebuy) > 0).mean()

    DD = 1 - strategy.nav / strategy.nav.cummax()
    MDD = max(DD)

    # 策略逐年表现

    strategy['year'] = strategy.Date.apply(lambda x: str(x)[:4])
    nav_peryear = strategy.nav.groupby(strategy.year).last() / strategy.nav.groupby(strategy.year).first() - 1
    benchmark_peryear = strategy.benchmark.groupby(strategy.year).last() / strategy.benchmark.groupby(
        strategy.year).first() - 1

    excess_ret = nav_peryear - benchmark_peryear
    result_peryear = pd.concat([nav_peryear, benchmark_peryear, excess_ret], axis=1)
    result_peryear.columns = ['strategy_ret', 'bench_ret', 'excess_ret']
    result_peryear = result_peryear.T

    # 作图
    xtick = np.round(np.linspace(0, strategy.shape[0] - 1, 7), 0)
    xticklabel = strategy.Date[xtick]

    plt.figure(figsize=(9, 4))
    ax1 = plt.axes()
    plt.plot(np.arange(strategy.shape[0]), strategy.benchmark, 'black', label='benchmark', linewidth=2)
    plt.plot(np.arange(strategy.shape[0]), strategy.nav, 'red', label='nav', linewidth=2)
    plt.plot(np.arange(strategy.shape[0]), strategy.nav / strategy.benchmark, 'orange', label='RS', linewidth=2)

    plt.legend()
    ax1.set_xticks(xtick)
    ax1.set_xticklabels(xticklabel)

    maxloss = min(transactions.pricesell / transactions.pricebuy - 1)
    print('------------------------------')
    print('夏普比为:', round(Sharp, 2))
    print('年化收益率为:{}%'.format(round(rety * 100, 2)))
    print('胜率为：{}%'.format(round(VictoryRatio * 100, 2)))
    print('最大回撤率为：{}%'.format(round(MDD * 100, 2)))
    print('单次最大亏损为:{}%'.format(round(-maxloss * 100, 2)))
    print('月均交易次数为：{}(买卖合计)'.format(round(strategy.flag.abs().sum() / strategy.shape[0] * 20, 2)))

    result = {'Sharp': Sharp,
              'RetYearly': rety,
              'WinRate': VictoryRatio,
              'MDD': MDD,
              'maxlossOnce': -maxloss,
              'num': round(strategy.flag.abs().sum() / strategy.shape[0], 1)}

    result = pd.DataFrame.from_dict(result, orient='index').T

    return result, result_peryear

#%%
if __name__=='__main__':

    stats, result_peryear, transactions, df=Strategy(goog,"ch_osc","Close")
    #%%保存图片和结果
    plt.savefig("./result/Chaikin Oscillator.png")
    plt.show()
    work=pd.ExcelWriter("./result/result.xlsx")
    stats.to_excel(work,sheet_name="stats")
    result_peryear.to_excel(work,sheet_name="result_peryear")
    transactions.to_excel(work,sheet_name="transactions")
    work.save()
    work.close()
    df.to_excel("./result/Chaikin Oscillator.xlsx")