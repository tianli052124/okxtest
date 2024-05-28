import asyncio
from okxv5_async.Trade import TradeAPI
from okxv5_async.Account import AccountAPI
from okxv5_async.MarketData import MarketAPI


class TradeExecutor:
    def __init__(self, api_key, api_secret_key, passphrase, flag):
        self.tradeapi = TradeAPI(api_key=api_key, api_secret_key=api_secret_key, passphrase=passphrase, flag=flag)
        self.accountapi = AccountAPI(api_key=api_key, api_secret_key=api_secret_key, passphrase=passphrase, flag=flag)
        self.marketapi = MarketAPI(api_key=api_key, api_secret_key=api_secret_key, passphrase=passphrase, flag=flag)

    async def get_cash_balance(self):
        try:
            result = await self.accountapi.get_account_balance()
            cash_balance = float(result["data"][0]["details"][0]["cashBal"])
            return cash_balance
        except Exception as e:
            print(f"Error getting cash balance: {e}")
            return None

    async def set_leverage(self, instId, lever):
        try:
            result = await self.accountapi.set_leverage(lever, 'cross', instId)
            print(f"Set leverage result: {result}")
        except Exception as e:
            print(f"Error setting leverage: {e}")

    async def place_order(self, instId, tdMode, side, ordType, sz, ccy=None, tgtCcy=None, posSide=None, px=None):
        try:
            result = await self.tradeapi.place_order(instId=instId, ccy=ccy, tdMode=tdMode, side=side, ordType=ordType,
                                                     sz=sz, tgtCcy=tgtCcy, posSide=posSide, px=px)
            order_id = result["data"][0]["ordId"]
            print(f"Placed order {order_id}: {result}")
            return order_id
        except Exception as e:
            print(f"Error placing order: {e}")
            return None

    async def get_order_status(self, instId, ordId):
        try:
            result = await self.tradeapi.get_order(instId, ordId)
            order_status = result["data"][0]["state"]
            print(f"Order status {ordId}: {order_status}")
            return order_status
        except Exception as e:
            print(f"Error getting order status: {e}")
            return None

    async def cancel_order(self, instId, ordId):
        try:
            result = await self.tradeapi.cancel_order(instId, ordId)
            print(f"Canceled order {ordId}: {result}")
            return result["data"]
        except Exception as e:
            print(f"Error canceling order: {e}")
            return None

    async def close_position(self, instId, mgnMode, ccy, posSide):
        try:
            result = await self.tradeapi.close_positions(instId, mgnMode, ccy, posSide)
            print(f"Closed position {instId} with posSide {posSide}: {result}")
            return result["data"]
        except Exception as e:
            print(f"Error closing position: {e}")
            return None

    async def get_liquidity_info(self, instId):
        try:
            result = await self.marketapi.get_orderbook(instId=instId)
            bids = result["data"][0]["bids"]
            asks = result["data"][0]["asks"]
            top_bid = float(bids[0][0]) if bids else 0
            top_ask = float(asks[0][0]) if asks else 0
            bid_size = float(bids[0][1]) if bids else 0
            ask_size = float(asks[0][1]) if asks else 0
            spread = top_ask - top_bid if top_bid and top_ask else float('inf')
            return top_bid, top_ask, bid_size, ask_size, spread
        except Exception as e:
            print(f"Error getting liquidity info: {e}")
            return None, None, None, None, float('inf')

    async def execute_arbitrage_trade(self, token, mode, portion_size, spot_price, contract_value):
        try:
            swap_instId = token + "-USDT-SWAP"
            margin_instId = token + "-USDT"

            swap_bid, swap_ask, swap_bid_size, swap_ask_size, swap_spread = await self.get_liquidity_info(swap_instId)
            margin_bid, margin_ask, margin_bid_size, margin_ask_size, margin_spread = await self.get_liquidity_info(
                margin_instId)

            if mode == "negative":
                max_size = await self.accountapi.get_max_order_size(token + "-USDT", "cross", "USDT")
                max_size = float(max_size["data"][0]["maxSell"])
                if max_size == 0:
                    print(f"Max size for selling {token} is zero. Skipping this token.")
                    return False
                amount = round(min(portion_size / spot_price, max_size) / contract_value, 0)
                await self.set_leverage(instId=token + "-USDT-SWAP", lever=3)
                await self.set_leverage(instId=token + "-USDT", lever=3)

                if swap_spread > margin_spread:
                    swap_order_id = await self.place_order(instId=swap_instId, tdMode="cross", side="buy",
                                                           posSide="long", ordType="limit", sz=amount, px=swap_ask)
                    if not swap_order_id:
                        print(f"Failed to place swap order for buying {token}")
                        return False

                    margin_order_id = await self.place_order(instId=margin_instId, ccy="USDT", tdMode="cross",
                                                             side="sell",
                                                             ordType="limit", sz=amount * contract_value, px=margin_bid,
                                                             tgtCcy="base_ccy")
                    if not margin_order_id:
                        print(f"Failed to place margin order for selling {token}")
                        await self.cancel_order(instId=swap_instId, ordId=swap_order_id)
                        return False
                else:
                    margin_order_id = await self.place_order(instId=margin_instId, ccy="USDT", tdMode="cross",
                                                             side="sell",
                                                             ordType="limit", sz=amount * contract_value, px=margin_bid,
                                                             tgtCcy="base_ccy")
                    if not margin_order_id:
                        print(f"Failed to place margin order for selling {token}")
                        return False

                    swap_order_id = await self.place_order(instId=swap_instId, tdMode="cross", side="buy",
                                                           posSide="long", ordType="limit", sz=amount, px=swap_ask)
                    if not swap_order_id:
                        print(f"Failed to place swap order for buying {token}")
                        await self.cancel_order(instId=margin_instId, ordId=margin_order_id)
                        return False

            else:
                max_size = await self.accountapi.get_max_order_size(instId=margin_instId, tdMode="cross", ccy="USDT")
                max_size = float(max_size["data"][0]["maxBuy"])
                if max_size == 0:
                    print(f"Max size for buying {token} is zero. Skipping this token.")
                    return False
                amount = round(min(portion_size / spot_price, max_size) / contract_value, 0)
                await self.set_leverage(instId=swap_instId, lever=3)
                await self.set_leverage(instId=margin_instId, lever=3)

                if swap_spread > margin_spread:
                    swap_order_id = await self.place_order(instId=swap_instId, tdMode="cross", side="sell",
                                                           posSide="short", ordType="limit", sz=amount, px=swap_bid)
                    if not swap_order_id:
                        print(f"Failed to place swap order for selling {token}")
                        return False

                    margin_order_id = await self.place_order(instId=margin_instId, ccy="USDT", tdMode="cross",
                                                             side="buy",
                                                             ordType="limit", sz=amount * contract_value, px=margin_ask)
                    if not margin_order_id:
                        print(f"Failed to place margin order for buying {token}")
                        await self.cancel_order(instId=swap_instId, ordId=swap_order_id)
                        return False
                else:
                    margin_order_id = await self.place_order(instId=margin_instId, ccy="USDT", tdMode="cross",
                                                             side="buy",
                                                             ordType="limit", sz=amount * contract_value, px=margin_ask)
                    if not margin_order_id:
                        print(f"Failed to place margin order for buying {token}")
                        return False

                    swap_order_id = await self.place_order(instId=swap_instId, tdMode="cross", side="sell",
                                                           posSide="short", ordType="limit", sz=amount, px=swap_bid)
                    if not swap_order_id:
                        print(f"Failed to place swap order for selling {token}")
                        await self.cancel_order(instId=margin_instId, ordId=margin_order_id)
                        return False

            # 确认订单状态
            await asyncio.sleep(10)  # 等待10秒钟以确保订单被处理
            margin_order_status = await self.get_order_status(instId=token + "-USDT", ordId=margin_order_id)
            swap_order_status = await self.get_order_status(instId=token + "-USDT-SWAP", ordId=swap_order_id)

            if margin_order_status == 'filled' and swap_order_status == 'filled':
                print(f"Both orders for {token} filled successfully.")
                return True
            else:
                print(
                    f"Order status check failed for {token}: Margin order status: {margin_order_status}, Swap order status: {swap_order_status}")
                if margin_order_status == 'filled' and swap_order_status != 'filled':
                    await self.cancel_order(instId=token + "-USDT-SWAP", ordId=swap_order_id)
                    await self.close_position(instId=token + "-USDT", mgnMode="cross", posSide="net", ccy="USDT")
                if swap_order_status == 'filled' and margin_order_status != 'filled':
                    await self.cancel_order(instId=token + "-USDT", ordId=margin_order_id)
                    posside = await self.tradeapi.get_order(instId=token + "-USDT-SWAP", ordId=swap_order_id)
                    await self.close_position(instId=token + "-USDT-SWAP", mgnMode="cross",  ccy="USDT", posSide=posside["data"][0]["posSide"])
                return False

        except Exception as e:
            print(f"Error executing arbitrage trade: {e}")
            return False
