# 纯测试用文件，用于测试异步调用的各个函数的功能

import logging
import json
import asyncio
from okxv5_async.Account import AccountAPI
from new_position import PositionMonitor
from okxv5_async.MarketData import MarketAPI
from okxv5_async.Trade import TradeAPI
from okxv5_async.PublicData import PublicAPI
from new_trade import TradeExecutor
from arbitragechecker import ArbitrageChecker
from utils import round_to, scientific_to_float
from decimal import Decimal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    api_key = "e1b9fa18-438f-4186-8679-2e1a31cac369"
    secret = "ED6A1408691C36597446782AA57D8BC3"
    passphrase = "Llz0102!!"
    flag = "1"

    account_api = AccountAPI(api_key=api_key, api_secret_key=secret, passphrase=passphrase, flag=flag)
    position_monitor = PositionMonitor(api_key, secret, passphrase, flag)
    marketapi = MarketAPI(api_key, secret, passphrase, flag)
    tradeexecutor = TradeExecutor(api_key, secret, passphrase, flag)
    tradeapi = TradeAPI(api_key, secret, passphrase, flag)
    arbitragechecker = ArbitrageChecker(api_key, secret, passphrase, flag)
    publicapi = PublicAPI(api_key, secret, passphrase, flag)

    # await tradeexecutor.place_order("ATOM-USDT", "cross", "sell", "limit", "100", "USDT", posSide="short", px=scientific_to_float(5.580000e-08))
    t= await  tradeexecutor.get_cash_balance()
    print(t)


if __name__ == "__main__":
    # asyncio.run(main())
    while True:
        try:
            asyncio.run(main())
        except Exception as e:
            print(f"Program terminated with exception: {e}")
            print("Restarting program...")
            time.sleep(180)  # 可选：等待一段3分钟再重启程序

