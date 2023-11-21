# -*- coding: utf-8 -*-
# 主要功能：文件的读取


import codecs
import datetime
import os
import pickle

import pandas as pd
import tushare as ts
import yaml

from output_file_Func import write_file

# tushare pro接口
token = 'e7d5fc2af55a0f46a41f28ef9b81468b83c55a30e64fecd8360fe1ad'
pro = ts.pro_api(token)


def read_file(data_dir, file_name, file_type=None, **kwargs):
    """
        主函数，算法执行流程。
    :param data_dir:
    :param file_name: str, 文件名;
    :param file_type: str, 文件类型，默认为空，从后缀名获取文件类型，也可指定文件类型：
    :param **kwargs, 其他参数传递给特定文件类型的读取方法;
    :return: data, DataFrame: 读取文件为DataFrame.
    """
    file_doc = os.path.join(data_dir, file_name)  # 拼接文件路径
    # 如果未指定文件类型，从文件路径中获取后缀名, 如'RVar_RSkew_RKurt.csv'将最后一个切分的csv作为文件类型
    if file_type is None:
        file_type = os.path.splitext(file_doc)[1][1:].lower()
    else:
        pass
    # 根据文件类型调用相应的读取方法
    if file_type == 'csv':
        # pandas读取csv，可设定index_col等参数
        data = pd.read_csv(file_doc, **kwargs)
    elif file_type == 'pickle' or file_type == 'pkl':  # 因为pickle文件的后缀名可能是pkl所以设置两个条件
        # pandas读取pickle
        with open(file_doc, 'rb') as file:
            data = pickle.load(file)
    elif file_type == 'json':
        # pandas读取json，可设置orient和double_precision等参数
        data = pd.read_json(file_doc, **kwargs)
    elif file_type == 'bz2':
        # pandas读取pickle，压缩方式bz2
        data = pd.read_pickle(file_doc, **kwargs)
    elif file_type == 'parquet':
        # pandas 读取parquet文件
        data = pd.read_parquet(file_doc)
    # 此处可继续添加更多文件类型的处理方式
    elif file_type =='yml' or 'yaml':
        with codecs.open(file_doc, encoding='utf-8') as f:
            return yaml.safe_load(f)
    else:
        # 如果以上文件类型均不符合且通过扩展名获取的文件类型仍不符合，报错。
        raise ValueError("Unsupported file type.")

    return data


def get_trade_cal(data_dir="data/"):
    """
        获取交易日历
    :param data_dir: str, 数据目录路径，默认为 "data/"
    :return: trade_cal, DataFrame, 交易日历数据，包含日期和当天是否开盘
    """
    # 如果交易日历数据文件不存在，则获取交易日历数据并存储到文件
    if not os.path.exists(os.path.join(data_dir, "trade_cal.pickle")):
        # tushare交易日历接口获取数据
        trade_cal = pro.trade_cal()
        # 按照日期进行升序排序
        trade_cal = trade_cal.sort_values(by='cal_date', ascending=True)
        # 将日期列格式转换为 %Y%m%d 格式的日期，并仅保留日期部分
        trade_cal['cal_date'] = pd.to_datetime(trade_cal['cal_date'], format="%Y%m%d").dt.date
        # 将 'pretrade_date' 列的日期格式转换为 %Y%m%d 格式的日期，并仅保留日期部分
        trade_cal['pretrade_date'] = pd.to_datetime(trade_cal['pretrade_date'], format="%Y%m%d").dt.date
        # 将 trade_cal 数据存储到文件 "trade_cal.pickle" 中
        write_file(data=trade_cal, data_dir=data_dir, file_name="trade_cal.pickle")
    else:
        # 如果交易日历数据文件存在，则从文件中读取数据
        trade_cal = read_file(data_dir, file_name="trade_cal.pickle")

    return trade_cal


def get_stock_list(data_dir, list_status='L', fields=['ts_code', 'symbol', 'name', 'area', 'industry', 'list_date']):
    """
        获取股票列表
    :param data_dir: str, 数据目录路径，默认为 "data/"
    :param list_status: str, 上市状态，L上市 D退市 P暂停上市，默认为'L'
    :param fields: list, 获得的信息列
    :return: DataFrame, 上市股票列表和基本信息
    """
    if not os.path.exists(os.path.join(data_dir, 'stock_list.pickle')):
        # 如果股票列表数据文件不存在，则调取tushare获取股票列表数据并存储到文件
        stock_list = pro.stock_basic(
            exchange='',
            list_status=list_status,
            fields=fields)
        write_file(data=stock_list, data_dir=data_dir, file_name='stock_list.pickle')
    else:
        # 如果股票列表数据文件存在，则从文件中读取数据
        stock_list = read_file(data_dir, file_name='stock_list.pickle')

    return stock_list


def attribute_history(data_dir, current_dt, trade_cal, security, count, fields=['open', 'close', 'high', 'low', 'vol']):
    """
        获取历史数据
    :param security: str, 股票代码
    :param current_dt: datetime.date, 当前日期
    :param count: int, 获取当前节点向前多少天的历史数据
    :param fields: Tuple, 需要获取历史数据的哪些列，默认包括开盘价、收盘价、最高价、最低价、交易量
    :return: DataFrame, 包含历史价格和交易量数据
    """
    # end_date: 需要获取的历史数据的最后一天
    end_date = (current_dt - datetime.timedelta(days=1))
    # datetime.timedelta(days=1): 标准化的1天时间范围
    start_date = trade_cal[((trade_cal['is_open'] == 1)
                            & (trade_cal['cal_date'] <= end_date))][-count:].iloc[0, :]['cal_date']
    # 获取从end_date 向前数count个交易日的回测开始日期.这里有问题就是现在的tushare接口是日期倒序排列的所以需要改动

    return attribute_datarange_history(data_dir=data_dir, security=security, start_date=start_date,
                                       end_date=end_date, fields=fields)


def get_tushare_daily(data_dir, security, save=True, start_date=None, end_date=None):
    """
        调取tushare每日行情接口读取日线数据
    :param data_dir: str, 数据目录路径，默认为 "data/"
    :param security: str, 股票代码，需要读取日线数据的股票
    :param save: 是否存储数据，默认为True
    :return: tushare_daily, DataFrame, 包含该股票所有可获取的日线数据
    """
    security = security.replace(".XSHE", ".SZ").replace(".XSHG", ".SH")
    # 如果数据文件不存在，则根据股票代码或指数代码调取tushare接口，根据不同的类型，判断不同的tushare接口
    if not os.path.exists(os.path.join(data_dir, security.replace(".", "_") + ".pickle")):
        # 如果是指数，通过tushare指数日线数据接口调取
        if security == '000300.SH':
            tushare_daily = pro.index_daily(ts_code=security, start_date=start_date, end_date=end_date)
        # 如果是可转债，通过tushare可转债日线数据接口调取
        elif 110000 < int(security.split(".")[0]) < 130000:
            tushare_daily = pro.cb_daily(ts_code=security, start_date=start_date, end_date=end_date)
        # 如果是个股，调用tushare股票日线数据获取
        else:
            tushare_daily = pro.daily(ts_code=security, start_date=start_date, end_date=end_date)
        # 按照 'trade_date' 列的值进行升序排序
        tushare_daily = tushare_daily.sort_values(by='trade_date', ascending=True)
        # 将 'trade_date' 列的日期格式转换为 %Y%m%d 格式的日期，并仅保留日期部分
        tushare_daily['trade_date'] = pd.to_datetime(tushare_daily['trade_date'], format="%Y%m%d")
        # 将 'trade_date' 列设置为数据的索引
        tushare_daily = tushare_daily.set_index('trade_date')
        # 将 tushare_daily 数据存储到文件 "security.pickle" 中
        if save:
            write_file(data=tushare_daily, data_dir=data_dir, file_name=security.replace(".", "_") + ".pickle")
    else:
        # 如果日线数据文件存在，则从文件中读取数据
        tushare_daily = read_file(data_dir=data_dir, file_name=security.replace(".", "_") + ".pickle")

    return tushare_daily


def get_tushare_monthly(data_dir, security, save=True):
    # 如果数据文件不存在，则根据股票代码或指数代码调取tushare接口，根据不同的类型，判断不同的tushare接口
    if not os.path.exists(os.path.join(data_dir, security + ".pickle")):
        # 如果是指数，通过tushare指数日线数据接口调取
        if security == '000300':
            tushare_monthly = pro.index_monthly(ts_code=security + '.SH')
        # 如果是个股，调用tushare股票日线数据获取
        elif int(security) >= 600000:
            tushare_monthly = pro.monthly(ts_code=security + '.SH')
        elif int(security) < 100000:
            tushare_monthly = pro.monthly(ts_code=security + '.SZ')
        # 按照 'trade_date' 列的值进行升序排序
        tushare_monthly = tushare_monthly.sort_values(by='trade_date', ascending=True)
        # 将 'trade_date' 列的日期格式转换为 %Y%m%d 格式的日期，并仅保留日期部分
        tushare_monthly['trade_date'] = pd.to_datetime(tushare_monthly['trade_date'], format="%Y%m%d").dt.date
        # 将 'trade_date' 列设置为数据的索引
        tushare_monthly = tushare_monthly.set_index('trade_date')
        # 将 tushare_daily 数据存储到文件 "security.pickle" 中
        if save:
            write_file(data=tushare_monthly, data_dir=data_dir, file_name=security + ".pickle")
    else:
        # 如果日线数据文件存在，则从文件中读取数据
        tushare_monthly = read_file(data_dir=data_dir, file_name=security + ".pickle")

    return tushare_monthly


def attribute_datarange_history(data_dir, security, start_date, end_date, frequency='daily',
                                fields=['open', 'close', 'high', 'low', 'vol'], save=True):
    """
        获取历史数据区间的具体价格信息
        :param data_dir: str, 数据目录路径，默认为 "data/"
    :param security: str, 股票代码，需要读取区间日线数据的股票
    :param start_date: str，开始日期，输入形式：'20180101'
    :param end_date: str，结束日期，输入形式：'20181231'
    :param frequency:
    :param fields: Tuple, 需要获取历史数据的哪些列，默认包括开盘价、收盘价、最高价、最低价、交易量
    :return: DataFrame，区间内特定列的数据
    """
    if isinstance(start_date, str):
        start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
    if isinstance(end_date, str):
        end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
    if frequency == 'daily':
        # 调用 get_tushare_daily() 函数获取指定股票的交易数据，然后根据给定的起始日期和结束日期选择相应的数据行
        trade_data = get_tushare_daily(data_dir, security, save=save).loc[start_date:end_date, :]
    elif frequency == 'monthly':
        trade_data = get_tushare_monthly(data_dir, security, save=save).loc[start_date:end_date, :]
    return trade_data[fields]


def get_today_data(data_dir, date, security):
    """
        获取今日价格数据
    :param data_dir: str, 数据目录路径
    :param date: str，日期，输入形式：'20180101'
    :param security: str, 股票代码，需要读取当日数据的股票
    :return: today_data, Series, 包含当日股票数据
    """
    try:
        data_daily = get_tushare_daily(data_dir, security)
        try:
            today_data = data_daily.loc[date, :]
        except KeyError:
            data_daily.index = pd.to_datetime(data_daily.index)
            today_data = data_daily.loc[date, :]
    except KeyError:
        today_data = pd.Series()

    return today_data
    # 可被调用 amount(操作股票的数量
    # 下单函数
    # Todo: https://www.ricequant.com/doc/rqalpha-plus/api/api/order_api.html#order-value


def get_portfolio(func):
    def wrapper(data_dir, current_dt, security):
        if isinstance(security, list):
            prices = pd.Series(name='price')
            for stock in security:
                price = func(data_dir, current_dt, stock)
                prices[stock] = price
            return prices
        else:
            return func(data_dir, current_dt, security)
    return wrapper


@get_portfolio
def get_price(data_dir, current_dt, security):
    today_data = get_today_data(data_dir, current_dt, security)
    # 如果当天数据为空，代表停牌，价格等于0
    if len(today_data) == 0:
        price = 0
    else:
        # 使用开盘价作为股票当前价格
        price = today_data['close']
    return price


@get_portfolio
def get_capacity(data_dir, current_dt, security, period=252):
    """
        获取股票交易容量，计算方法：个股过去半年日均成交额的10%
    :param data_dir: str, 数据目录路径
    :param current_dt: datetime.date, 当前日期
    :param security: str, 股票代码
    :param period: int, 周期天数，默认252
    :return: capacity: float, 当天的股票容量
    """
    # 获取交易日历
    trade_cal = get_trade_cal(data_dir=data_dir)
    # 调用attribute_history获取过去半年的交易数据
    today_data = attribute_history(data_dir, current_dt, trade_cal, security, count=int(period / 2))
    # 计算半年的交易量的平均值
    capacity = today_data['vol'].mean()

    return capacity


if __name__ == '__main__':
    df=attribute_datarange_history(data_dir="data/", security='000001', start_date="2015-01-01", end_date="2021-12-30",
                                   frequency='monthly', save=False)
    print("done")
