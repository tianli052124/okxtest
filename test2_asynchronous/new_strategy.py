# new_strategy.py

import asyncio
from datetime import datetime, time as dtime


import pandas as pd
import configparser
from new_trade import TradeExecutor  # 异步版本的TradeExecutor
from new_position import PositionMonitor  # 异步版本的PositionMonitor
from arbitragechecker import ArbitrageChecker  # 异步版本的ArbitrageChecker

# 读取配置文件
config = configparser.ConfigParser()
config.read('config.ini')

# 设置API密钥等信息
api_key = config['API']['api_key']
secret_key = config['API']['secret_key']
passphrase = config['API']['passphrase']
flag = config['SETTINGS']['flag']

# 初始化异步交易执行器
trade_executor = TradeExecutor(api_key, secret_key, passphrase, flag)

# 初始化异步持仓监控器
position_monitor = PositionMonitor(api_key, secret_key, passphrase, flag)

# 初始化异步套利检查器
arbitrage_checker = ArbitrageChecker(api_key, secret_key, passphrase, flag)

# 获取潜在套利币种
token_list = ['BTC', 'ETH', 'SOL', 'DOGE', 'PEPE', 'ORDI', 'LTC', 'XRP', 'BCH', 'WLD', 'TRB', 'FIL', 'ARB', 'ETC',
              'TON', 'BNB', 'SHIB', 'NEAR', 'AR', 'AVAX', 'LINK', 'PEOPLE', 'OP', 'MATIC', 'PYTH', 'ADA', 'SUI', 'SATS',
              'TIA', 'FTM', 'CORE', 'WIF', 'JTO', 'ETHFI', 'APT', 'DOT', 'AEVO', 'NOT', 'EOS', 'BIGTIME', 'MKR', 'MERL',
              'RNDR', 'CFX', 'LDO', 'UNI', 'STX', 'BLUR', 'ATOM', 'DYDX']

async def execute_trade_strategy():
    try:
        print("Getting cash balance...")
        cash_balance = await trade_executor.get_cash_balance()
        if cash_balance is None:
            print("Failed to retrieve cash balance.")
            return

        print("Getting current pairs count...")
        current_pairs = await position_monitor.get_updated_current_pairs()
        numberofpairs = len(current_pairs)
        if numberofpairs is None:
            print("Failed to retrieve current pairs count.")
            return
        print(f"Current pairs count: {numberofpairs}")

        data = {
            "Token": ["BTC", "ETH", "XRP", "LTC", "ADA"],
            "Difference": [0.05, 0.03, 0.07, 0.02, 0.04],
            "Type": ["positive", "negative", "positive", "negative", "positive"],
            "ContractValue": [0.001, 0.01, 100, 0.001, 1]
        }

        # Create the DataFrame
        arbitrage_set = pd.DataFrame(data, columns=["Token", "Difference", "Type", "ContractValue"])

        portfolio = arbitrage_set.sort_values(by="Difference", ascending=False)

        portion_size = cash_balance / 4

        for a in current_pairs:
            basetoken = a[0]
            if basetoken in portfolio['Token'].values:
                portfolio = portfolio[portfolio['Token'] != basetoken]

        for index, row in portfolio.iterrows():
            if numberofpairs >= 3:
                break

            mode = row['Type']
            print(f"Getting token info for {row['Token']}...")
            token_info = await arbitrage_checker.get_token_info(row['Token'])
            if token_info is None:
                print(f"Failed to get token info for {row['Token']}. Skipping this token.")
                continue

            print(f"Executing arbitrage trade for {row['Token']}...")
            success = await trade_executor.execute_arbitrage_trade(
                row['Token'], mode, portion_size, token_info[3], row['ContractValue']
            )

            if success:
                print(f"Arbitrage trade executed successfully for {row['Token']}")
                current_pairs = await position_monitor.get_updated_current_pairs()  # 更新 current_pairs
                numberofpairs = len(current_pairs)  # 更新 numberofpairs

    except Exception as e:
        print(f"An error occurred: {e}")


async def close_arbitrage(close_time_end):
    current_pairs = await position_monitor.get_updated_current_pairs()

    for pair in current_pairs:
        token = pair[0]
        mode = pair[1]
        token_info = await arbitrage_checker.get_token_info(token)
        if not token_info:
            continue
        _, feerate, _, _, _ = token_info

        now = datetime.now().time()
        close_time_limit = (datetime.combine(datetime.today(), close_time_end) - pd.Timedelta(minutes=5)).time()
        if now >= close_time_limit:
            print(f"Closing position for {token} due to end of closing window.")
            if mode == 'positive':
                await trade_executor.close_position(token + "-USDT-SWAP", 'cross', 'USDT', 'long')
                await trade_executor.close_position(token + "-USDT", 'cross', 'USDT', 'net')
            if mode == 'negative':
                await trade_executor.close_position(token + "-USDT-SWAP", 'cross', 'USDT', 'short')
                await trade_executor.close_position(token + "-USDT", 'cross', 'USDT', 'net')


async def scheduler():
    loop = asyncio.get_event_loop()
    while True:
        now = datetime.now().time()

        # 定义交易时间段
        trade_windows = [
            (dtime(23, 15), dtime(23, 55)),
            (dtime(7, 15), dtime(7, 55)),
            (dtime(15, 15), dtime(15, 55))
        ]

        # 定义平仓时间段
        close_windows = [
            (dtime(0, 15), dtime(0, 45)),
            (dtime(8, 15), dtime(8, 45)),
            (dtime(16, 15), dtime(16, 45))
        ]

        for start, end in trade_windows:
            if start <= now <= end:
                await execute_trade_strategy()

        for start, end in close_windows:
            if start <= now <= end:
                await close_arbitrage(end)

        await asyncio.sleep(60)  # 每分钟检查一次



if __name__ == "__main__":
    asyncio.run(scheduler())