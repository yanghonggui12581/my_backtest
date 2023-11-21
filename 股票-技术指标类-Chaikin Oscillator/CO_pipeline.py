# -*- coding: utf-8 -*-
# 主要功能：CO因子


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
    # 导入生成的因子数据
    g.stock = dataGet.read_file("./data", 'co_data.csv')
    # 依据股票数据生成交易日数据
    trade_cal = pd.to_datetime(g.stock['date']).dt.date
    # 根据trade_cal，将context相应的属性初始化
    context.init_trade_cal(trade_cal)
    g.stock = g.stock.set_index('date')
    # 将索引转换为日期时间索引
    g.stock.index = pd.DatetimeIndex(g.stock.index)
    g.ch_osc = g.stock['ch_osc']
    g.SMA_90 = g.stock['SMA_90']



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
    price = g.stock['close'][context.current_dt]
    # 子账户3：全仓持有标的
    # order_target_percent(),该函数为backtest中进行下单的函数，传入参数依次为context, context.security, price, 1, 3，最后两位依次是买入/卖出百分比、账户名
    if not (context.security in context.portfolios[3].positions):
        backtest.order_target_percent(context, context.security, price, 1, 3)
        # 根据以上指标构建一个多空逻辑，即
        # 当前无仓位，Chaikin Oscillator上穿0，且股价高于90天移动平均，做多
        # 当前持仓，Chaikin Oscillator下穿0，且股价低于90天移动平均，平仓
    current_ch_osc = g.ch_osc[context.current_dt]
    current_SMA_90 = g.SMA_90[context.current_dt]
    current_ch_osc_shift = g.ch_osc.shift(1)[context.current_dt]
    if not pd.isnull(current_ch_osc) and not pd.isnull(current_SMA_90):

        if (current_ch_osc_shift < 0) and (current_ch_osc > 0) & (
                price > current_SMA_90):
            # 如果股票不在子账户1的持仓中，全仓买入
            if context.security not in context.portfolios[1].positions:
                backtest.order_target_percent(context, context.security, price, 1, 1)
            # 如果股票在子账户2的持仓中，清仓
            if context.security in context.portfolios[2].positions:
                backtest.order_target_percent(context, context.security, price, 0, 2)

        if (current_ch_osc_shift > 0) and (current_ch_osc < 0) & (
                price < current_SMA_90):
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
