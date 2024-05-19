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

    def get_cash_balance(self):
        try:
            result = self.accountAPI.get_account_balance()
            cash_balance = float(result["data"][0]["details"][0]["cashBal"])
            return cash_balance
        except Exception as e:
            print(f"Error getting cash balance: {e}")
            return None

    def set_leverage(self, instId, lever):
        try:
            self.accountAPI.set_leverage(instId=instId, lever=lever, mgnMode="cross")
        except Exception as e:
            print(f"Error setting leverage: {e}")

    def place_order(self, instId, tdMode, side, ordType, sz, ccy=None, tgtCcy=None, posSide=None, px=None):
        try:
            result = self.tradeAPI.place_order(instId=instId, ccy=ccy, tdMode=tdMode, side=side, ordType=ordType, sz=sz, tgtCcy=tgtCcy, posSide=posSide, px=px)
            return result["data"][0]["ordId"]  # 返回订单ID
        except Exception as e:
            print(f"Error placing order: {e}")
            return None

    def get_order_status(self, instId, ordId):
        try:
            result = self.tradeAPI.get_order(instId=instId, ordId=ordId)
            return result["data"][0]["state"]
        except Exception as e:
            print(f"Error getting order status: {e}")
            return None

    def cancel_order(self, instId, ordId):
        try:
            result = self.tradeAPI.cancel_order(instId=instId, ordId=ordId)
            return result["data"]
        except Exception as e:
            print(f"Error canceling order: {e}")
            return None

    def close_position(self, instId, tdMode, side, posSide, sz):
        try:
            close_side = "sell" if side == "buy" else "buy"
            result = self.tradeAPI.place_order(instId=instId, tdMode=tdMode, side=close_side, posSide=posSide, ordType="market", sz=sz)
            return result["data"]
        except Exception as e:
            print(f"Error closing position: {e}")
            return None

    def execute_arbitrage_trade(self, token, mode, portion_size, token_info, contract_value):
        try:
            if mode == "negative":
                max_size = float(
                    self.accountAPI.get_max_order_size(instId=token + "-USDT", tdMode="cross", ccy="USDT")["data"][0]["maxSell"]
                )
                if max_size == 0:
                    return False
                amount = round(min(portion_size / token_info[3], max_size) / contract_value, 0)
                self.set_leverage(instId=token + "-USDT-SWAP", lever=3)
                self.set_leverage(instId=token + "-USDT", lever=3)

                margin_order_id = self.place_order(instId=token + "-USDT", ccy="USDT", tdMode="cross", side="sell",
                                                   ordType="market", sz=amount * contract_value, tgtCcy="base_ccy")
                if not margin_order_id:
                    return False

                swap_order_id = self.place_order(instId=token + "-USDT-SWAP", tdMode="cross", side="buy",
                                                 posSide="long", ordType="market", sz=amount)
                if not swap_order_id:
                    self.cancel_order(instId=token + "-USDT", ordId=margin_order_id)  # 撤销未执行的订单
                    return False

            else:
                max_size = float(
                    self.accountAPI.get_max_order_size(instId=token + "-USDT", tdMode="cross", ccy="USDT")["data"][0]["maxBuy"]
                )
                if max_size == 0:
                    return False
                amount = round(min(portion_size / token_info[3], max_size) / contract_value, 0)
                self.set_leverage(instId=token + "-USDT-SWAP", lever=3)
                self.set_leverage(instId=token + "-USDT", lever=3)

                margin_order_id = self.place_order(instId=token + "-USDT", ccy="USDT", tdMode="cross", side="buy",
                                                   ordType="limit", sz=amount * contract_value, px=token_info[3])
                if not margin_order_id:
                    return False

                swap_order_id = self.place_order(instId=token + "-USDT-SWAP", tdMode="cross", side="sell",
                                                 posSide="short", ordType="market", sz=amount)
                if not swap_order_id:
                    self.cancel_order(instId=token + "-USDT", ordId=margin_order_id)  # 撤销未执行的订单
                    return False

            # 确认订单状态
            time.sleep(2)  # 等待5秒钟以确保订单被处理
            margin_order_status = self.get_order_status(instId=token + "-USDT", ordId=margin_order_id)
            swap_order_status = self.get_order_status(instId=token + "-USDT-SWAP", ordId=swap_order_id)

            if margin_order_status == 'filled' and swap_order_status == 'filled':
                return True
            else:
                # 如果一个订单被完全执行，而另一个订单未被执行，则撤销未执行的订单，并平仓已执行的订单
                if margin_order_status == 'filled' and swap_order_status != 'filled':
                    time.sleep(5)
                    self.cancel_order(instId=token + "-USDT-SWAP", ordId=swap_order_id)
                    self.close_position(instId=token + "-USDT", tdMode="cross", side="sell", posSide="net", sz=amount * contract_value)
                if swap_order_status == 'filled' and margin_order_status != 'filled':
                    time.sleep(5)
                    self.cancel_order(instId=token + "-USDT", ordId=margin_order_id)
                    self.close_position(instId=token + "-USDT-SWAP", tdMode="cross", side="buy", posSide="long", sz=amount)
                print(f"Order status check failed: Margin order status: {margin_order_status}, Swap order status: {swap_order_status}")
                return False

        except Exception as e:
            print(f"Error executing arbitrage trade: {e}")
            return False
