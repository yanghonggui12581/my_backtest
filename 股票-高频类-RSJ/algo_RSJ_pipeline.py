# -*- coding: utf-8 -*-
# 主要功能：RSJ因子


import concurrent.futures

import os
import pandas as pd

import backtest
import cal_metric
import dataGet_Func as dataGet
import output_file_Func as output
from backtest import Context


class G:
    """
    全局对象 G，用来存储用户的全局数据
    """
    pass


# 创建全局对象g
g = G()


def initialize(context):
    """
        用户输出初始设定，在回测时只会在启动的时候触发一次
    :param context: Context对象，因子的各种属性上下文
    """
    # 调用get_trade_cal函数生成trade_cal交易日历属性，存储在context.data_dir中
    trade_cal = dataGet.get_trade_cal(data_dir=context.data_dir)
    # 将trade_cal转为只含有开盘日期的series
    trade_cal = pd.Series(trade_cal[(trade_cal['is_open'] == 1)]['cal_date'].values)
    # 根据trade_cal，将context相应的属性初始化
    context.init_trade_cal(trade_cal)

    #  ——————————————————————————————以下为因子逻辑——————————————————————————————
    # 读取股票5分钟价格数据存储在全局对象中
    g.stock = dataGet.read_file(context.data_dir, 'hs300.csv').set_index('date')
    # g.stock = dataGet.read_file(context.data_dir, context.security + '_five_minute.bz2').set_index('date')[['close']]
    # 将索引转换为日期时间索引
    g.stock.index = pd.DatetimeIndex(g.stock.index)
    # 计算五分钟收益率
    # pct_change计算相邻值的变化
    # g.stock['ret'] = g.stock['close'].pct_change()
    g.ret = g.stock['close'].pct_change()
    g.ret.name = 'ret'
    # 计算rsj 倒数第13根到倒数第一根，即13:55至14:55
    # 传入的针对时间的config值
    m = context.config['m']
    rsj = g.ret.groupby(g.ret.index.date).apply(
        lambda x: ((x[-m:-1][x[-m:-1] > 0] ** 2).sum() - (x[-m:-1][x[-m:-1] < 0] ** 2).sum()) / (x[-m:-1] ** 2).sum())
    # rsj = g.stock['ret'].groupby(g.stock.index.date).apply(
    #     lambda x: ((x[-m:-1][x[-m:-1] > 0] ** 2).sum() - (x[-m:-1][x[-m:-1] < 0] ** 2).sum()) / (x[-m:-1] ** 2).sum())
    # 将计算得到的rsj存储在g.ret中，并将列名改为'rsj'
    g.rsj = pd.DataFrame(rsj.copy()).rename(columns={'ret': 'rsj'})


def handle_data(context):
    """
        因子具体逻辑实现的函数，每个时刻只被调用一次，在此函数进行下单
    :param context: Context对象，因子的各种属性上下文
    """
    # # 判断是否在交易频率允许的日期，如果不在，直接结束当天交易
    # if not context.is_scheduler():
    #     return
    # #  ——————————————————————————————以下为因子逻辑——————————————————————————————
    # # 判断是否是调仓时刻，如果是，进行调仓。
    # if context.is_select():
    #     pass
    # 调用get_today_data函数读取当天的价格数据
    # 简要分析一下该逻辑，针对于几个不同的账户，采取做多，做空的操作，其中第零个账户是后面三个子组合的组合、第三个账户为全仓不变的账户
    price = dataGet.get_price(context.data_dir, context.current_dt, context.security)
    # 子账户3：全仓持有标的
    # order_target_percent(),该函数为backtest中进行下单的函数，传入参数依次为context, context.security, price, 1, 3，最后两位依次是买入/卖出百分比、账户名
    backtest.order_target_percent(context, context.security, price, 1, 3)
    # 读取一个交易日的rsj值作为current_rsj
    if len(g.rsj[(g.rsj.index == context.current_dt)]['rsj'].values) != 0:
        current_rsj = g.rsj[(g.rsj.index == context.current_dt)]['rsj'].values[0]
        # 如果rsj值小于0
        if current_rsj < 0:
            # 如果股票不在子账户1的持仓中，全仓买入
            if context.security not in context.portfolios[1].positions:
                backtest.order_target_percent(context, context.security, price, 1, 1)
            # 如果股票在子账户2的持仓中，清仓
            if context.security in context.portfolios[2].positions:
                backtest.order_target_percent(context, context.security, price, 0, 2)
        # 如果rsj值大于0
        if current_rsj > 0:
            # 如果股票在子账户1的持仓中，清仓
            if context.security in context.portfolios[1].positions:
                backtest.order_target_percent(context, context.security, price, 0, 1)
            # 如果股票不在子账户2的持仓中，全仓买入
            if context.security not in context.portfolios[2].positions:
                backtest.order_target_percent(context, context.security, price, 1, 2)


def update_value(context, afterTrading=False):
    """
        更新每个portfolio和benchmark的价格和价值，盘前和盘后分别更新一次
    :param context: Context对象，因子的各种属性上下文
    :param afterTrading: bool, 是否是盘后更新，默认为否
    """
    # 遍历每个子账户
    for i in range(context.subportfolio_num + 1):
        # 遍历子账户中的持仓标的
        for stock in context.portfolios[i].positions_all:
            # 读取当前价格数据
            price = dataGet.get_price(context.data_dir, context.current_dt, stock)
            # 将所有指标存储为字典
            attributes = {"price": price}
            # 更新持仓标的的指标
            context.portfolios[i].positions_all[stock].update(context.current_dt, attributes, afterTrading)
    for key in context.benchmark.keys():
        # 存储benchmark每个组成部分的价格
        context.benchmark_return.loc[context.current_dt, key] = dataGet.get_price(context.data_dir, context.current_dt, key)
    # 更新context
    context.update(afterTrading)


def before_trading(context):
    """
        盘前处理函数，每天策略开始交易前会被调用，不能在这个函数中发送订单
    :param context: Context对象，因子的各种属性上下文
    """

    # 调用更新函数更新价值和价格
    update_value(context, False)


def after_trading(context):
    """
        盘后处理函数，每天收盘后会被调用，不能在这个函数中发送订单
    :param context: Context对象，因子的各种属性上下文
    """
    # 调用更新函数更新价值和价格
    update_value(context, True)


def after_all_trading(context):
    """
        回测结束后处理函数，所有回测日期结束后被调用，包含指标计算和结果输出，不能在这个函数中发送订单
    :param context: Context对象，因子的各种属性上下文
    :return: result: DataFrame, cal_metric结果
             all_result: dict, 原始表存储字典
    """
    # 调用回测后更新函数更新context
    context.update_after_all_trading()
    # 调用CalMetric计算评估指标
    context.result = cal_metric.CalMetric().main(returnRatio=context.portfolio_return, period=context.period)
    # 输出结果
    result, all_result = output.output_result(context)

    return result, all_result


if __name__ == "__main__" or os.path.dirname(__file__) == os.getcwd():
    # 如果当前文件被直接执行或者被执行文件和当前文件处于同一目录，则直接导入本地配置
    import config as local_config
else:
    # 否则，使用相对路径导入本地配置
    from . import config as local_config


def run(conf={}):
    """
        回测主运行函数，调用各种处理函数进行每日因子逻辑实现
    :param conf: dict, 单个的配置字典
    :return: result: DataFrame, cal_metric结果
             all_result: dict, 原始表存储字典
             context.config_index: int, 当前运行配置序号
    """
    # 用传入的远端config_super更新本地config
    conf_merge = local_config.update_config(conf, local_config.configs[0])
    # 初始化context
    # 此处的Context来源于backtest包，输入参数为配置和globals
    # 当使用globals()函数时，它会返回一个包含所有全局变量的字典，其中键是变量名，值是对应的值。
    context = Context(conf_merge, globals())
    # 调用initialize进行初始化
    initialize(context)
    # 遍历日期范围
    for date in context.date_range:
        # 更新当前日期
        context.current_dt = date
        # 执行盘前处理操作
        before_trading(context)
        # 执行盘中下单等操作
        handle_data(context)
        # 执行盘后处理操作
        after_trading(context)
    # 执行回测结束后处理操作
    result, all_result = after_all_trading(context)

    return result, all_result, context.config_index


def multi_run(CONF={}):
    """
        多个配置的回测函数，对每个配置调用run()进行回测
    :param CONF: dict, 每个属性包含多个选项的配置字典
    :return: result_output: DataFrame, cal_metric总结果
             multi_run_result: dict, 原始表存储字典
    """
    # 用传入的远端config_super中的CONFIG更新本地CONFIG
    CONF_merge = local_config.update_config(CONF, local_config.CONFIG_factor)
    # 生成配置组合

    # 这里的配置组合为什么只选取了其中前两个？

    configs = local_config.generate_config_combinations(CONF_merge)[0:2]
    # multi_run_result用以记录原始表格
    multi_run_result = {}
    # cal_metric结果存储
    results = []
    # 如果并行
    if CONF_merge["multiProcess_multiRun"] == [True]:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = []
            # 向线程池提交任务
            for i in range(len(configs)):
                configs[i]["config_index"] = i
                futures.append(executor.submit(run, configs[i]))
            # 等待任务完成并获取结果
            for future in concurrent.futures.as_completed(futures):
                # 存放每个进程的run()的输出结果
                result, all_result, index = future.result()
                # 添加cal_metric结果进总的DataFrame
                results.append(result)
                # 添加原始表格
                multi_run_result["config" + str(index)] = all_result
    else:  # 如果非并行
        for i in range(len(configs)):
            # 添加配置项"config_index"为i
            configs[i]["config_index"] = i
            # 运行回测，记录结果
            result, all_result, index = run(configs[i])
            # 添加cal_metric结果
            results.append(result)
            # 添加原始表格
            multi_run_result["config" + str(index)] = all_result
    # 合并cal_metric结果
    result_output = pd.concat(results)
    # 输出multi_run结果
    output.multirun_output(CONF_merge, result_output, all_result)

    return result_output, multi_run_result


if __name__ == "__main__":
    result, all_result = multi_run()
    # 引进远端的config
    import config_super as super_config
    # result, all_result = multi_run(super_config.CONFIG)

    # run(super_config.configs[0])
    # run()
    print("done")
