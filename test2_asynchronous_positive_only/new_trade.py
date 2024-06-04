import asyncio
import logging
from okxv5_async.Trade import TradeAPI
from okxv5_async.Account import AccountAPI
from okxv5_async.MarketData import MarketAPI
from utils import round_to, scientific_to_float

# 配置日志记录
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TradeExecutor:
    def __init__(self, api_key, api_secret_key, passphrase, flag):
        self.tradeapi = TradeAPI(api_key=api_key, api_secret_key=api_secret_key, passphrase=passphrase, flag=flag)
        self.accountapi = AccountAPI(api_key=api_key, api_secret_key=api_secret_key, passphrase=passphrase, flag=flag)
        self.marketapi = MarketAPI(api_key=api_key, api_secret_key=api_secret_key, passphrase=passphrase, flag=flag)

    async def get_cash_balance(self):
        try:
            result = await self.accountapi.get_account_balance()
            cash_balance = float(result["data"][0]["totalEq"])
            return cash_balance
        except Exception as e:
            logger.error(f"Error getting cash balance: {e}")
            return None

    async def set_leverage(self, instId, lever):
        try:
            result = await self.accountapi.set_leverage(lever, 'cross', instId)
            logger.info(f"Set leverage result: {result}")
        except Exception as e:
            logger.error(f"Error setting leverage: {e}")

    async def place_order(self, instId, tdMode, side, ordType, sz, ccy=None, tgtCcy=None, posSide=None, px=None):
        try:
            result = await self.tradeapi.place_order(instId=instId, ccy=ccy, tdMode=tdMode, side=side, ordType=ordType,
                                                     sz=sz, tgtCcy=tgtCcy, posSide=posSide, px=px)
            order_id = result["data"][0]["ordId"]
            logger.info(f"Placed order {order_id}: {result}")
            return order_id
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None

    async def get_order_status(self, instId, ordId):
        try:
            result = await self.tradeapi.get_order(instId, ordId)
            order_state = result["data"][0]["state"]
            order_fillsize = float(result["data"][0]["fillSz"]) + float(result["data"][0]["fee"])
            logger.info(f"Order status {ordId}: {order_state}, fill size: {order_fillsize}")
            return order_state, order_fillsize
        except Exception as e:
            logger.error(f"Error getting order status: {e}")
            return None

    async def cancel_order(self, instId, ordId):
        try:
            result = await self.tradeapi.cancel_order(instId, ordId)
            logger.info(f"Canceled order {ordId}: {result}")
            return result["data"]
        except Exception as e:
            logger.error(f"Error canceling order: {e}")
            return None

    async def close_position(self, instId, mgnMode, ccy, posSide):
        try:
            result = await self.tradeapi.close_positions(instId, mgnMode, ccy, posSide)
            logger.info(f"Closed position {instId} with posSide {posSide}: {result}")
            return result["data"]
        except Exception as e:
            logger.error(f"Error closing position: {e}")
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
            logger.error(f"Error getting liquidity info: {e}")
            return None, None, None, None, float('inf')

    async def open_arbitrage_trade(self, token, mode, portion_size, spot_price, contract_value, divider):
        try:
            swap_instId = token + "-USDT-SWAP"
            spot_id = token + "-USDT"

            swap_bid, swap_ask, swap_bid_size, swap_ask_size, swap_spread = await self.get_liquidity_info(swap_instId)
            margin_bid, margin_ask, margin_bid_size, margin_ask_size, margin_spread = await self.get_liquidity_info(spot_id)

            max_size = await self.accountapi.get_max_order_size(instId=spot_id, tdMode="cross", ccy="USDT")
            max_size = float(max_size["data"][0]["maxBuy"])
            if max_size == 0:
                logger.info(f"Max size for buying {token} is zero. Skipping this token.")
                return False
            amount = round(min(portion_size / margin_ask,max_size), 3)
            swap_amount = round(amount / contract_value,0)
            spot_amount = round_to(swap_amount * contract_value*(1+0.001),divider)

            await self.set_leverage(instId=swap_instId, lever=1)
            await self.set_leverage(instId=spot_id, lever=1)

            if swap_spread > margin_spread:
                    swap_order_id = await self.place_order(instId=swap_instId, tdMode="cross", side="sell",
                                                           posSide="short", ordType="limit", sz=swap_amount, px=swap_bid)

                    spot_order_id = await self.place_order(instId=spot_id, ccy="USDT", tdMode="cash",
                                                             side="buy", ordType="limit", sz=spot_amount,
                                                             px=scientific_to_float(margin_ask*0.998))

            else:
                    spot_order_id = await self.place_order(instId=spot_id, ccy="USDT", tdMode="cash",
                                                             side="buy", ordType="limit", sz=spot_amount,
                                                             px=margin_ask)

                    swap_order_id = await self.place_order(instId=swap_instId, tdMode="cross", side="sell",
                                                           posSide="short", ordType="limit", sz=swap_amount, px=scientific_to_float(swap_bid*1.002))

            # 确认订单状态
            await asyncio.sleep(10)  # 等待10秒钟以确保订单被处理
            spot_status = await self.get_order_status(instId=spot_id, ordId=spot_order_id)
            spot_state, spot_fillsize = spot_status
            swap_status = await self.get_order_status(instId=token + "-USDT-SWAP", ordId=swap_order_id)
            swap_state, swap_fillsize = swap_status

            if spot_state == 'filled' and swap_state == 'filled':
                logger.info(f"Both orders for {token} filled successfully.")
            elif spot_state == 'filled' and swap_state== 'partially_filled':
                logger.info(f"Margin order for {token} filled successfully, but swap order partially filled.")
                asyncio.sleep(10)
            elif spot_state == 'filled' and swap_state =='live':
                logger.info(f"Margin order for {token} filled successfully, but swap order still live.")
                await self.cancel_order(swap_instId, swap_order_id)
                await self.place_order(spot_id, 'cash', 'USDT', 'market', spot_fillsize, px=None)
            elif spot_state == 'live' and swap_state == 'filled':
                logger.info(f"Swap order for {token} filled successfully, but margin order still live.")
                await self.cancel_order(spot_id, spot_order_id)
                await self.close_position(swap_instId, 'cross', 'USDT', 'short')
            elif spot_state == 'partially_filled' and swap_state == 'filled':
                logger.info(f"Margin order for {token} partially filled, but swap order filled successfully.")
                asyncio.sleep(10)
            elif spot_state == 'live' and swap_state =='live':
                logger.info(f"Both orders for {token} still live.")
                await self.cancel_order(spot_id, spot_order_id)
                await self.cancel_order(swap_instId, swap_order_id)


        except Exception as e:
            logger.error(f"Error executing arbitrage trade: {e}")
            return False
