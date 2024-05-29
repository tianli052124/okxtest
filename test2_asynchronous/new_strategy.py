import asyncio
import time

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
    await asyncio.sleep(5)
    while True:
        try:
            print("Getting cash balance...")
            cash_balance = await trade_executor.get_cash_balance()
            if cash_balance is None:
                print("Failed to retrieve cash balance. Retrying in 30s")
                await asyncio.sleep(30)
                continue

            print("Getting current pairs count...")
            current_pairs = await position_monitor.get_updated_current_pairs()
            numberofpairs = len(current_pairs)
            if numberofpairs is None:
                print("Failed to retrieve current pairs count. Retrying in 1 minute.")
                await asyncio.sleep(60)
                continue
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

            portion_size = cash_balance / 5
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
            print(f"An error occurred: {e}. Retrying in 1 minute.")
            await asyncio.sleep(60)

async def close_arbitrage():
    threshold_funding_rate = 0.00001
    current_pairs = position_monitor.current_pairs

    for pair in current_pairs:
        token = pair[0]
        mode = pair[1]
        token_info = await arbitrage_checker.get_token_info(token)
        if not token_info:
            continue
        _, feerate, _, _, _ = token_info

        if abs(feerate) < threshold_funding_rate:
            if mode == 'positive':
                await trade_executor.close_position(token + "-USDT-SWAP", 'cross', 'USDT', 'long')
                await trade_executor.close_position(token + "-USDT", 'cross', 'USDT', 'net')
            if mode == 'negative':
                await trade_executor.close_position(token + "-USDT-SWAP", 'cross', 'USDT', 'short')
                await trade_executor.close_position(token + "-USDT", 'cross', 'USDT', 'net')

async def main():

    monitorws = asyncio.create_task(position_monitor.start())
    strategyws = asyncio.create_task(execute_trade_strategy())

    await asyncio.gather(monitorws, strategyws)


if __name__ == "__main__":
    asyncio.run(main())