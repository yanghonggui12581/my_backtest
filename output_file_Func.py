# -*- coding: utf-8 -*-
# 主要功能：文件的保存，结果输出等
import os
import pickle

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import time


def write_file(data, data_dir, file_name, file_type=None, **kwargs):
    """
        输出各种文件格式的通用函数
    :param data: DataFrame, 需要保存为文件的数据
    :param data_dir: str, 文件保存路径
    :param file_name: str, 文件名
    :param file_type: str, 文件类型
    :param kwargs: 其他输出参数
    """
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    file_doc = os.path.join(data_dir, file_name)  # 拼接文件路径
    # 如果未指定文件类型，从文件路径中获取后缀名, 如'RVar_RSkew_RKurt.csv'将最后一个切分的csv作为文件类型
    if file_type is None:
        file_type = os.path.splitext(file_doc)[1][1:].lower()
    else:
        pass
    # 根据文件类型调用相应的写入方法
    if file_type == 'csv':
        data.to_csv(file_doc, **kwargs)
    elif file_type == 'pickle' or file_type == 'pkl':  # 因为pickle文件的后缀名可能是pkl所以设置两个条件
        with open(file_doc, 'wb') as file:
            pickle.dump(data, file)
    elif file_type == 'json':
        data.to_json(file_doc, orient='table', double_precision=15)
    elif file_type == 'bz2':
        data.to_pickle(file_doc, compression='bz2')
    elif file_type == 'parquet':
        data.to_parquet(file_doc)
    elif file_type == 'xlsx':
        with pd.ExcelWriter(file_doc) as writer:
            # 遍历字典中的每个键值对，并将每个DataFrame写入到对应的Sheet中
            for sheet_name, sheet in data.items():
                sheet.to_excel(writer, sheet_name=sheet_name)
    # 此处可继续添加更多文件类型的处理方式
    else:
        # 如果以上文件类型均不符合且通过扩展名获取的文件类型仍不符合，报错。
        raise ValueError("Unsupported file type.")


def output_result(context):
    """
        回测输出结果，将运行完回测的context传入，输出结果到相应的文件中
    :param context: Context对象，因子的各种属性上下文
    :return: result: DataFrame, cal_metric结果
             all_result: dict, 原始表存储字典
    """
    # 建立字典存储所有原始表格，键为portfolio
    all_result = {}
    # 导出Context的result进行修改
    result = context.result
    # 添加运行时长信息
    result["timing"] = context.timing.iloc[-1]["timing"] - context.timing.iloc[0]["timing"]
    # 重命名行索引为"Portfolio"
    result = result.rename_axis('Portfolio')
    # 重置索引
    result = result.reset_index()
    # 拷贝当前列名
    result_columns = list(result.columns)
    # 添加配置信息到输出结果中
    result = result.assign(**{key: str(value) for key, value in context.config.items()})
    # 调整result的列的顺序，先config的键，再result的结果列
    result = result.reindex(columns=list(context.config.keys()) + result_columns)
    # 遍历所有portfolio，输出每个portfolio的结果
    for i in range(context.subportfolio_num + 1):
        all_result.update({"portfolio" + str(i): {}})
        # 每个config的结果放在output_dir中该config下的目录

        # 此处的original_df仅仅表示了在组合中买入某只股票后的持有价值，可以从结果中long和short两个列表互补看出，
        # 因此我觉得应该导出的是组合中的总价值,即context.portfolios[i].account_df['protfolio_value']

        all_result["portfolio" + str(i)]["original_df"] = context.portfolios[i].original_df
        all_result["portfolio" + str(i)]["cross_corr"] = all_result["portfolio" + str(i)]["original_df"]["price"].pct_change().corr()
        if context.config["time_df"]:
            all_result["portfolio" + str(i)]["time_df"] = context.portfolios[i].time_df
        if context.config["security_df"]:
            all_result["portfolio" + str(i)]["security_df"] = context.portfolios[i].security_df
        all_result["portfolio" + str(i)]["order_df"] = context.portfolios[i].order_df
        all_result["portfolio" + str(i)]["account_df"] = context.portfolios[i].account_df
        all_result["portfolio" + str(i)]["position_df"] = context.portfolios[i].position_df
        all_result["portfolio" + str(i)]["subposition_df"] = {}
        for stock in context.portfolios[i].positions_all:
            all_result["portfolio" + str(i)]["subposition_df"][stock] = context.portfolios[i].positions_all[stock].subposition_df
    # 控制是否生成时间序列相关测试结果
    if context.config["time_series_corr"]:
        all_result["time_series_corr"] = context.time_series_corr
    # 控制是否生成运行时间结果
    if context.config["timing"]:
        all_result["timing"] = context.timing
    # 控制是否生成run层的结果
    if context.config["output_run"]:
        write_file(result, context.output_dir, context.factor_name + "_output.csv",  index=False)
        if context.config["time_series_corr"]:
            context.fig, context.ax = plt.subplots()
            sns.heatmap(context.time_series_corr, annot=True, cmap='coolwarm', ax=context.ax)
            context.ax.set_title('time_series_corr')
            context.fig.savefig(os.path.join(context.output_dir, "time_series_corr.png"))
        if context.config["timing"]:
            write_file(context.timing, context.output_dir, context.factor_name + "_timing.csv", index=False)
        for i in range(context.subportfolio_num + 1):
            file_dir = os.path.join(context.output_dir, "portfolio" + str(i))
            # 将original_df输出为pickle和xlsx
            write_file(context.portfolios[i].original_df, file_dir, "portfolio" + str(i) + "_original_df.pickle")
            write_file(context.portfolios[i].original_df, file_dir, "portfolio" + str(i) + "_original_df.xlsx")
            # 将account_df输出为pickle和xlsx
            write_file(context.portfolios[i].account_df, file_dir, "portfolio" + str(i) + "_account_df.pickle")
            write_file(context.portfolios[i].account_df, file_dir, "portfolio" + str(i) + "_account_df.xlsx")
            if context.config["time_df"]:
                # 如果time_df开启，将time_df输出为pickle和xlsx
                write_file(context.portfolios[i].time_df, file_dir, "portfolio" + str(i) + "_time_df.pickle")
                write_file(context.portfolios[i].time_df, file_dir, "portfolio" + str(i) + "_time_df.xlsx")
            if context.config["security_df"]:
                # 如果security_df开启，将time_df输出为pickle和xlsx
                write_file(context.portfolios[i].security_df, file_dir, "portfolio" + str(i) + "_security_df.pickle")
                write_file(context.portfolios[i].security_df, file_dir, "portfolio" + str(i) + "_security_df.xlsx")

            # 为什么要修改timing？
            result["timing"] = time.time()

    return result, all_result


def multirun_output(CONF, result, all_result):
    """
        multirun层回测输出结果
    :param CONF: dict, 配置项，用以控制输出路径
    :param result: DataFrame, cal_metric结果
    :param all_result: dict, 原始表存储字典
    """
    write_file(result, CONF["output_dir"][0], CONF["factor_name"][0]+"_result_all_metric.csv")
    write_file(result, CONF["output_dir"][0], CONF["factor_name"][0] + "_result_all_metric.pickle")
    write_file(all_result, CONF["output_dir"][0], CONF["factor_name"][0] + "_result_all_config.pickle")


def remove_file(file_dir, file_name):
    """
        删除文件的通用函数
    :param file_dir: str, 文件保存路径
    :param file_name: str, 文件名
    """
    # 判断该文件是否存在
    if os.path.exists(os.path.join(file_dir, file_name)):
        # 如果存在，删除文件
        os.remove(os.path.join(file_dir, file_name))


if __name__ == '__main__':
    df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
    df.to_parquet("test.parquet")
    print("done")
"""
    typeList = ['csv', 'pickle', 'json', 'bz2', 'parquet']
    from dataGet_Func import read_file

    for fileType in typeList:
        write_file(data=read_file(data_dir='data/', file_name='2013_002262_trade_pickle4.bz2'),
                   data_dir='test_data/', file_name='fileTest.' + fileType)
        print(fileType + ' successfully written')
    print("done")
"""
