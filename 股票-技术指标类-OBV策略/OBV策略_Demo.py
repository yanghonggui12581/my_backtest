# coding: utf-8
# Python 3.6


import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('tkAgg')
matplotlib.rcParams['font.sans-serif'] = ['KaiTi']
import matplotlib.pyplot as plt

stock = pd.read_csv('data/TRD_Dalyr.csv', engine='python')
stock.columns = ['date', 'open', 'high', 'low', 'close', 'volume']
close = stock.close
Volume = stock.volume
stock.reset_index(inplace=True)

# 计算OBV
difClose=close.diff()
difClose[0]=0
OBV=(((difClose>=0)*2-1)*Volume).cumsum()
OBV.name='OBV'
OBV.head()
OBV.describe()


smOBV=OBV.rolling(9).mean()

AdjOBV=((close-stock.low)-(stock.high-close)\
         )/(stock.high-stock.low)*Volume
AdjOBV.name='AdjOBV'
AdjOBVd=AdjOBV.cumsum()
AdjOBVd.name='AdjOBVd'

plt.rcParams['figure.figsize']=(20.0,10.0)
ax1=plt.subplot(3,1,1)
close.plot(title='收盘价')
plt.xticks(close.index[1:3],(''))
plt.xlabel('')
ax2=plt.subplot(3,1,2)
OBV.plot(label='OBV',title='累积能量潮与移动能量潮')
smOBV.plot(label='smOBV',linestyle='-.',color='r')
plt.legend(loc='upper left')
plt.xticks(close.index[1:3],(''))
plt.xlabel('')
ax3=plt.subplot(3,1,3)
AdjOBVd.plot(title='成交量多空比率净额')
for ax in ax1,ax2,ax3:
    ax.grid(True)
plt.savefig('result/OBV及成交量多空比率净额.jpg')
import ffn
def trade(obv,price):
    signal=(2*(obv.diff()>0)-1)[1:]
    ret=ffn.to_returns(price)[1:]
    ret.name='ret'
    tradeRet=ret*signal.shift(1)
    tradeRet.name='tradeRet'
    Returns=pd.merge(pd.DataFrame(ret),\
                     pd.DataFrame(tradeRet),\
                    left_index=True,right_index=True).dropna()
    return(Returns)
OBVtrade=trade(OBV,close)
OBVtrade.head()
ret=OBVtrade.ret
tradeRet=OBVtrade.tradeRet
ret.name='BuyAndHold'
tradeRet.name='OBVTrade'
(1+ret).cumprod().plot(label='ret',linestyle='dashed')
(1+tradeRet).cumprod().plot(label='tradeRet')
plt.title('累积OBV交易策略绩效表现')
plt.legend()
plt.savefig('result/累积OBV交易策略绩效表现.jpg')
def backtest(ret,tradeRet):
    def performance(x):
        winpct=len(x[x>0])/len(x[x!=0])
        annRet=(1+x).cumprod().iloc[-1]**(245/len(x))-1
        sharpe=ffn.calc_risk_return_ratio(x)
        maxDD=ffn.calc_max_drawdown((1+x).cumprod())
        perfo=pd.Series([winpct,annRet,sharpe,maxDD],index=['win rate',
                        'annualized return',\
                        'sharpe ratio','maximum drawdown'])
        return(perfo)
    BuyAndHold=performance(ret)
    OBVTrade=performance(tradeRet)
    return(pd.DataFrame({ret.name:BuyAndHold,\
    tradeRet.name:OBVTrade}))
OBVtest=backtest(ret,tradeRet)
smOBVtrade=trade(smOBV,close)

ret=smOBVtrade.ret
ret.name='BuyAndHold'
smtradeRet=smOBVtrade.tradeRet
smtradeRet.name='smOBVTrade'
(1+ret).cumprod().plot(label='ret',linestyle='dashed')
(1+tradeRet).cumprod().plot(label='tradeRet')
plt.title('简单OBV交易策略绩效表现')
plt.legend()
plt.savefig('result/简单OBV交易策略绩效表现.jpg')
test=backtest(ret,smtradeRet)


