# strategy.py

import asyncio
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
            current_pairs = position_monitor.current_pairs
            numberofpairs = len(current_pairs)
            if numberofpairs is None:
                print("Failed to retrieve current pairs count. Retrying in 1 minute.")
                time.sleep(60)
                continue
            print(f"Current pairs count: {numberofpairs}")

            # # 获取可套利的套利对
            # results = []
            # for token in token_list:
            #     arbitrage_info = arbitrage_checker.check_arbitrage(token)
            #     if arbitrage_info:
            #         results.append(arbitrage_info)
            # if not results:
            #     print("No arbitrage opportunities found. Retrying in 1 minute.")
            #     time.sleep(60)
            #     continue

            data = {
                "Token": ["BTC", "ETH", "XRP", "LTC", "ADA"],
                "Difference": [0.05, 0.03, 0.07, 0.02, 0.04],
                "Type": ["positive", "negative", "positive", "negative", "positive"],
                "ContractValue": [0.001, 0.01, 100, 0.001, 1]
            }

            # Create the DataFrame
            arbitrage_set = pd.DataFrame(data, columns=["Token", "Difference", "Type", "ContractValue"])

            # arbitrage_set = pd.DataFrame(results, columns=["Token", "Difference", "Type", "ContractValue"])
            portfolio = arbitrage_set.sort_values(by="Difference", ascending=False)

            portion_size = cash_balance / 5
            for a in current_pairs:
                basetoken = a[0]
                if basetoken in portfolio['Token'].values:
                    portfolio = portfolio[portfolio['Token'] != basetoken]

            for index, row in portfolio.iterrows():
                if numberofpairs >= 3:
                    break

                mode = row['Type']
                token_info = arbitrage_checker.get_token_info(row['Token'])
                if token_info is None:
                    print(f"Failed to get token info for {row['Token']}. Skipping this token.")
                    continue

                success = trade_executor.execute_arbitrage_trade(
                    row['Token'], mode, portion_size, token_info, row['ContractValue']
                )

                if success:
                    numberofpairs += 1

        except Exception as e:
            print(f"An error occurred: {e}. Retrying in 1 minute.")
            time.sleep(30)


def close_arbitrage():
    threshold_funding_rate = 0.00001  # Define your threshold funding rate here
    current_pairs = position_monitor.current_pairs  # Assuming this function returns a set of current pairs

    for pair in current_pairs:
        token = pair[0]  # Extract the token name from the pair
        mode = pair[1]
        token_info = arbitrage_checker.get_token_info(token)
        if not token_info:
            continue
        _, feerate, _, _, _ = token_info

        if abs(feerate) < threshold_funding_rate:
            if mode == 'positive':
                trade_executor.close_position(token+"-USDT-SWAP", 'cross', 'USDT', 'long')
                trade_executor.close_position(token+"-USDT", 'cross', 'USDT', 'net')
            if mode == 'negative':
                trade_executor.close_position(token+"-USDT-SWAP", 'cross', 'USDT', 'short')
                trade_executor.close_position(token+"-USDT", 'cross', 'USDT', 'net')




if __name__ == "__main__":
    # 启动持仓监控器
    position_monitor.start()
    time.sleep(10)

    # 启动套利策略
    strategy_thread = threading.Thread(target=execute_trade_strategy)
    strategy_thread.start()

