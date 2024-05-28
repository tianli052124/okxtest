import asyncio
from okxv5_async.Account import AccountAPI
from new_position import PositionMonitor
from okxv5_async.MarketData import MarketAPI
from okxv5_async.Trade import TradeAPI
from new_trade import TradeExecutor

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


    t = await tradeexecutor.get_cash_balance()

    print(t)


if __name__ == "__main__":
    asyncio.run(main())
