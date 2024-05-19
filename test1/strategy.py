# strategy.py

import time
import threading
from trade1 import TradeExecutor
from checkarbitrage import check_arbitrage, get_token_info
from position1 import PositionMonitor
import pandas as pd
import configparser

# 读取配置文件
config = configparser.ConfigParser()
config.read('config.ini')

# 设置API密钥等信息
api_key = config['API']['api_key']
secret_key = config['API']['secret_key']
passphrase = config['API']['passphrase']
flag = config['SETTINGS']['flag']

# 初始化交易执行器
trade_executor = TradeExecutor(api_key, secret_key, passphrase, flag)

# 初始化持仓监控器
position_monitor = PositionMonitor(api_key, secret_key, passphrase, flag)

# 获取潜在套利币种
token_list = ['BTC', 'ETH', 'SOL', 'DOGE', 'PEPE', 'ORDI', 'LTC', 'XRP', 'BCH', 'WLD', 'TRB', 'FIL', 'ARB', 'ETC',
              'TON', 'BNB', 'SHIB', 'NEAR', 'AR', 'AVAX', 'LINK', 'PEOPLE', 'OP', 'MATIC', 'PYTH', 'ADA', 'SUI', 'SATS',
              'TIA', 'FTM', 'CORE', 'WIF', 'JTO', 'ETHFI', 'APT', 'DOT', 'AEVO', 'NOT', 'EOS', 'BIGTIME', 'MKR', 'MERL',
              'RNDR', 'CFX', 'LDO', 'UNI', 'STX', 'BLUR', 'ATOM', 'DYDX']


# 执行套利策略
def execute_trade_strategy():
    while True:
        # 获取当前现金余额
        cash_balance = trade_executor.get_cash_balance()
        if cash_balance is None:
            time.sleep(60)  # 如果获取余额失败，等待1分钟后重试
            continue

        # 检查现有持仓的套利对个数
        current_pairs = position_monitor.get_current_pairs_count()
        print(current_pairs)
        # 获取可套利的套利对
        # results = [check_arbitrage(token) for token in token_list if check_arbitrage(token)]
        # 测使用数据
        results = [
            {"Token": "BTC", "Difference": 2, "Type": "negative", "ContractValue": 0.001},
            {"Token": "ETH", "Difference": 3, "Type": "positive", "ContractValue": 0.01},
            {"Token": "LTC", "Difference": 4, "Type": "negative", "ContractValue": 0.001},
            {"Token": "CFX", "Difference": 5, "Type": "negative", "ContractValue": 10},
            {"Token": "BNB", "Difference": 1, "Type": "negative", "ContractValue": 0.01},
        ]
        arbitrage_set = pd.DataFrame(results, columns=["Token", "Difference", "Type", "ContractValue"])
        portfolio = arbitrage_set.sort_values(by="Difference", ascending=False)

        executed_pairs = set(position_monitor.current_pairs)  # 获取当前已执行的套利对
        print(executed_pairs)

        while current_pairs < 4:
            # 尝试执行套利策略，直到持仓达到四个或遍历完所有组合
            portion_size = cash_balance / 4
            for index, row in portfolio.iterrows():
                if current_pairs >= 4:
                    break

                token_pair = (row['Token'], row['Type'])
                if token_pair in executed_pairs:
                    continue

                mode = row['Type']
                token_info = get_token_info(row['Token'])
                if token_info is None:
                    continue

                success = trade_executor.execute_arbitrage_trade(row['Token'], mode, portion_size, token_info,
                                                                 row['ContractValue'])
                if success:
                    executed_pairs.add(token_pair)  # 将已执行的套利对加入已执行集合

            current_pairs = position_monitor.get_current_pairs_count()
            print("current pairs is",current_pairs)

        time.sleep(30)


if __name__ == "__main__":
    # 启动持仓监控器
    position_monitor.start()

    # 启动套利策略
    strategy_thread = threading.Thread(target=execute_trade_strategy)
    strategy_thread.start()
