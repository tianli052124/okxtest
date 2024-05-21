# strategy.py

import time
import threading
import pandas as pd
import configparser
from trade1 import TradeExecutor
from position1 import PositionMonitor
from checkarbitrage import ArbitrageChecker


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

# 初始化套利检查器
arbitrage_checker = ArbitrageChecker(api_key, secret_key, passphrase, flag)

# 获取潜在套利币种
token_list = ['BTC', 'ETH', 'SOL', 'DOGE', 'PEPE', 'ORDI', 'LTC', 'XRP', 'BCH', 'WLD', 'TRB', 'FIL', 'ARB', 'ETC',
              'TON', 'BNB', 'SHIB', 'NEAR', 'AR', 'AVAX', 'LINK', 'PEOPLE', 'OP', 'MATIC', 'PYTH', 'ADA', 'SUI', 'SATS',
              'TIA', 'FTM', 'CORE', 'WIF', 'JTO', 'ETHFI', 'APT', 'DOT', 'AEVO', 'NOT', 'EOS', 'BIGTIME', 'MKR', 'MERL',
              'RNDR', 'CFX', 'LDO', 'UNI', 'STX', 'BLUR', 'ATOM', 'DYDX']


# 执行套利策略
def execute_trade_strategy():
    while True:
        try:
            # 获取当前现金余额
            cash_balance = trade_executor.get_cash_balance()
            if cash_balance is None:
                print("Failed to retrieve cash balance. Retrying in 1 minute.")
                time.sleep(30)  # 如果获取余额失败，等待30秒后重试
                continue

            # 检查现有持仓的套利对个数
            current_pairs = position_monitor.get_current_pairs_count()
            if current_pairs is None:
                print("Failed to retrieve current pairs count. Retrying in 1 minute.")
                time.sleep(60)
                continue
            print(f"Current pairs count: {current_pairs}")

            # 获取可套利的套利对
            results = []
            for token in token_list:
                arbitrage_info = arbitrage_checker.check_arbitrage(token)
                if arbitrage_info:
                    results.append(arbitrage_info)
            if not results:
                print("No arbitrage opportunities found. Retrying in 1 minute.")
                time.sleep(60)
                continue

            arbitrage_set = pd.DataFrame(results, columns=["Token", "Difference", "Type", "ContractValue"])
            portfolio = arbitrage_set.sort_values(by="Difference", ascending=False)
            print(portfolio)

            executed_pairs = set(position_monitor.current_pairs)  # 获取当前已执行的套利对
            print(f"Executed pairs: {executed_pairs}")

            for index, row in portfolio.iterrows():
                if current_pairs >= 4:
                    break

                token_pair = (row['Token'], row['Type'])
                if token_pair in executed_pairs:
                    continue

                mode = row['Type']
                token_info = arbitrage_checker.get_token_info(row['Token'])
                if token_info is None:
                    print(f"Failed to get token info for {row['Token']}. Skipping this token.")
                    continue

                portion_size = cash_balance / (4 - current_pairs)
                success = trade_executor.execute_arbitrage_trade(
                    row['Token'], mode, portion_size, token_info, row['ContractValue']
                )
                if success:
                    executed_pairs.add(token_pair)  # 将已执行的套利对加入已执行集合
                    current_pairs += 1  # 更新持仓对个数
                    print(f"Executed trade: {token_pair}, new current pairs count: {current_pairs}")
                else:
                    print(f"Failed to execute trade: {token_pair}")

            time.sleep(10)

        except Exception as e:
            print(f"An error occurred: {e}. Retrying in 1 minute.")
            time.sleep(30)

if __name__ == "__main__":
    # 启动持仓监控器
    position_monitor.start()
    time.sleep(10)

    # 启动套利策略
    strategy_thread = threading.Thread(target=execute_trade_strategy)
    strategy_thread.start()

