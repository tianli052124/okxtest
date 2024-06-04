# new_strategy.py

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

unpaired_positions_time = {}

async def execute_trade_strategy():
    # 获取现金余额
    cash_balance = None
    while cash_balance is None:
        try:
            print("Getting cash balance...")
            cash_balance = await trade_executor.get_cash_balance()

        except Exception as e:
            print(f"Failed to get cash balance: {e}. Retrying in 1 minute.")
            await asyncio.sleep(30)


    await asyncio.sleep(30)
    print("Getting current pairs count...")
    current_pairs = position_monitor.get_updated_current_pairs()
    numberofpairs = len(current_pairs)

    while True:
        try:
            portion_size = cash_balance / 8
            while numberofpairs < 4:
                print("Getting arbitrage set...")
                portfolio = await arbitrage_checker.get_arbitrage_set()
                for a in current_pairs:
                    token_in_pairs = a[0]
                    if token_in_pairs in portfolio['Token'].values:
                        portfolio = portfolio[portfolio['Token'] != token_in_pairs]

                for index, row in portfolio.iterrows():
                    token_info = await arbitrage_checker.get_token_info(row['Token'])
                    if token_info is None:
                        print(f"Failed to get token info for {row['Token']}. Skipping this token.")
                        continue
                    print(f"Executing arbitrage trade for {row['Token']}...")
                    await trade_executor.open_arbitrage_trade(row['Token'], row['Type'], portion_size, token_info[3], row['ContractValue'], token_info[5])
                    await asyncio.sleep(5)
                    current_pairs = position_monitor.get_updated_current_pairs()  # 更新 current_pairs
                    numberofpairs = len(current_pairs)  # 更新 numberofpairs
                await asyncio.sleep(5)
            #检查有没有需要平仓的套利组合
            positions = position_monitor.positions_df
            for index,row in positions.iterrows():
                if row['fundingRate'] is None:
                    continue
            # 如果资金费率小于-0.02%则平仓
                elif float(row['fundingRate']) < -0.0002:
                    basetoken = row['instId'].split('-')[0]
                    await trade_executor.close_position(row[basetoken]+"-USDT-SWAP", 'cross', 'USDT', 'short')
                    spot_size = positions[positions['instId'] == row[basetoken]+"-USDT"]['pos'].values[0]
                    await trade_executor.place_order(row[basetoken]+"-USDT", 'cash', 'sell', 'market', spot_size)
                else:
                    continue

            unpaired_positions = position_monitor.unpaired_positions
            if not unpaired_positions:
                continue  # Skip the rest of the loop if unpaired_positions is empty

            for token, instType in unpaired_positions:
                if token not in unpaired_positions_time:
                    # Store the time when the unpaired position is first detected
                    unpaired_positions_time[token] = time.time()
                elif time.time() - unpaired_positions_time[token] > 60:
                    # If the unpaired position exists for more than 60 seconds, close the position
                    print(f"Closing unpaired position for {token}...")
                    if instType == 'SPOT':
                        size = positions[positions['instId'] == token + '-USDT']['pos'].values[0]
                        await trade_executor.place_order(token + "-USDT", 'cash', 'sell', 'market', size)
                    elif instType == 'SWAP':
                        await trade_executor.close_position(token + "-USDT-SWAP", 'cross', 'USDT', 'short')
                    # Remove the token from the dictionary after closing the position
                    del unpaired_positions_time[token]

            await asyncio.sleep(60)


        except Exception as e:
            print(f"An error occurred: {e}. Retrying in 1 minute.")
            await asyncio.sleep(60)

async def main():

    monitorws = asyncio.create_task(position_monitor.start())
    strategyws = asyncio.create_task(execute_trade_strategy())
    await asyncio.gather(monitorws, strategyws)


def start_event_loop():
    while True:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(main())
        except Exception as e:
            print(f"Program terminated with exception: {e}, will restart in 3 minutes.")
            time.sleep(180)  # 可选：等待一段3分钟再重启程序


if __name__ == "__main__":
    start_event_loop()
