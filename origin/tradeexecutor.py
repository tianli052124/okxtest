import okx.Account as Account
import okx.Trade as Trade
import time

class TradeExecutor:
    def __init__(self, api_key, secret_key, passphrase, flag="1"):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.flag = flag
        self.accountAPI = Account.AccountAPI(api_key, secret_key, passphrase, False, flag)
        self.tradeAPI = Trade.TradeAPI(api_key, secret_key, passphrase, False, flag)

    def set_leverage(self, instId, lever):
        try:
            self.accountAPI.set_leverage(instId=instId, lever=lever, mgnMode="cross")
        except Exception as e:
            print(f"Error setting leverage: {e}")

    def place_order(self, instId, tdMode, side, ordType, sz, ccy=None, tgtCcy=None, posSide=None, px=None):
        try:
            order_id = self.tradeAPI.place_order(instId=instId, ccy=ccy, tdMode=tdMode, side=side, ordType=ordType, sz=sz, tgtCcy=tgtCcy, posSide=posSide, px=px)["data"][0]["ordId"]
            return order_id
        except Exception as e:
            print(f"Error placing order: {e}")
            return None

    def check_order_status(self, order_id):
        try:
            order_status = self.tradeAPI.get_order(order_id)["data"][0]["state"]
            return order_status
        except Exception as e:
            print(f"Error checking order status: {e}")
            return None

    def cancel_order(self, instId, ordId):
        try:
            self.tradeAPI.cancel_order(instId=instId, ordId=ordId)
        except Exception as e:
            print(f"Error cancelling order: {e}")

    def execute_arbitrage_trade(self, token, mode, portion_size, token_info, contract_value):
        try:
            if mode == "negative":
                max_size = float(self.accountAPI.get_max_order_size(instId=token + "-USDT", tdMode="cross", ccy="USDT")["data"][0]["maxSell"])
                if max_size == 0:
                    return False
                amount = round(min(portion_size / token_info[3], max_size) / contract_value, 0)
                self.set_leverage(instId=token + "-USDT-SWAP", lever=3)
                self.set_leverage(instId=token + "-USDT", lever=3)
                sell_order_id = self.place_order(instId=token + "-USDT", ccy="USDT", tdMode="cross", side="sell", ordType="market", sz=amount * contract_value, tgtCcy="base_ccy")
                buy_order_id = self.place_order(instId=token + "-USDT-SWAP", tdMode="cross", side="buy", posSide="long", ordType="market", sz=amount)
            else:
                max_size = float(self.accountAPI.get_max_order_size(instId=token + "-USDT", tdMode="cross", ccy="USDT")["data"][0]["maxBuy"])
                if max_size == 0:
                    return False
                amount = round(min(portion_size / token_info[3], max_size) / contract_value, 0)
                self.set_leverage(instId=token + "-USDT-SWAP", lever=3)
                self.set_leverage(instId=token + "-USDT", lever=3)
                buy_order_id = self.place_order(instId=token + "-USDT", ccy="USDT", tdMode="cross", side="buy", ordType="limit", sz=amount * contract_value, px=token_info[3])
                sell_order_id = self.place_order(instId=token + "-USDT-SWAP", tdMode="cross", side="sell", posSide="short", ordType="market", sz=amount)

            if not sell_order_id or not buy_order_id:
                print("Order placement failed")
                return False

            # Check order status
            max_wait_time = 30  # Max wait time in seconds
            start_time = time.time()
            while time.time() - start_time < max_wait_time:
                sell_status = self.check_order_status(sell_order_id)
                buy_status = self.check_order_status(buy_order_id)
                if sell_status == 'filled' and buy_status == 'filled':
                    return True
                time.sleep(1)

            # Cancel orders if not filled
            print("Single leg transaction detected, cancelling orders")
            self.cancel_order(instId=token + "-USDT", ordId=sell_order_id)
            self.cancel_order(instId=token + "-USDT-SWAP", ordId=buy_order_id)
            return False

        except Exception as e:
            print(f"Error executing arbitrage trade: {e}")
            return False
