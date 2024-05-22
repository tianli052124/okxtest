# trade1.py

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
            print(f"Cash balance: {cash_balance}")
            return cash_balance
        except Exception as e:
            print(f"Error getting cash balance: {e}")
            return None

    def set_leverage(self, instId, lever):
        try:
            result = self.accountAPI.set_leverage(instId=instId, lever=lever, mgnMode="cross")
            print(f"Set leverage result: {result}")
        except Exception as e:
            print(f"Error setting leverage: {e}")

    def place_order(self, instId, tdMode, side, ordType, sz, ccy=None, tgtCcy=None, posSide=None, px=None):
        try:
            result = self.tradeAPI.place_order(instId=instId, ccy=ccy, tdMode=tdMode, side=side, ordType=ordType, sz=sz, tgtCcy=tgtCcy, posSide=posSide, px=px)
            order_id = result["data"][0]["ordId"]
            print(f"Placed order {order_id}: {result}")
            return order_id
        except Exception as e:
            print(f"Error placing order: {e}")
            return None

    def get_order_status(self, instId, ordId):
        try:
            result = self.tradeAPI.get_order(instId=instId, ordId=ordId)
            order_status = result["data"][0]["state"]
            print(f"Order status {ordId}: {order_status}")
            return order_status
        except Exception as e:
            print(f"Error getting order status: {e}")
            return None

    def cancel_order(self, instId, ordId):
        try:
            result = self.tradeAPI.cancel_order(instId=instId, ordId=ordId)
            print(f"Canceled order {ordId}: {result}")
            return result["data"]
        except Exception as e:
            print(f"Error canceling order: {e}")
            return None

    def close_position(self, instId, mgnMode, ccy, posSide):
        try:
            result = self.tradeAPI.close_positions(instId=instId, mgnMode=mgnMode, ccy=ccy, posSide=posSide)
            print(f"Closed position {instId} with posSide {posSide}: {result}")
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
                    print(f"Max size for selling {token} is zero. Skipping this token.")
                    return False
                amount = round(min(portion_size / token_info[3], max_size) / contract_value, 0)
                self.set_leverage(instId=token + "-USDT-SWAP", lever=3)
                self.set_leverage(instId=token + "-USDT", lever=3)

                margin_order_id = self.place_order(instId=token + "-USDT", ccy="USDT", tdMode="cross", side="sell",
                                                   ordType="market", sz=amount * contract_value, tgtCcy="base_ccy")
                if not margin_order_id:
                    print(f"Failed to place margin order for selling {token}")
                    return False

                swap_order_id = self.place_order(instId=token + "-USDT-SWAP", tdMode="cross", side="buy",
                                                 posSide="long", ordType="market", sz=amount)
                if not swap_order_id:
                    print(f"Failed to place swap order for buying {token}")
                    self.cancel_order(instId=token + "-USDT", ordId=margin_order_id)
                    return False

            else:
                max_size = float(
                    self.accountAPI.get_max_order_size(instId=token + "-USDT", tdMode="cross", ccy="USDT")["data"][0]["maxBuy"]
                )
                if max_size == 0:
                    print(f"Max size for buying {token} is zero. Skipping this token.")
                    return False
                amount = round(min(portion_size / token_info[3], max_size) / contract_value, 0)
                self.set_leverage(instId=token + "-USDT-SWAP", lever=3)
                self.set_leverage(instId=token + "-USDT", lever=3)

                margin_order_id = self.place_order(instId=token + "-USDT", ccy="USDT", tdMode="cross", side="buy",
                                                   ordType="limit", sz=amount * contract_value, px=token_info[3])
                if not margin_order_id:
                    print(f"Failed to place margin order for buying {token}")
                    return False

                swap_order_id = self.place_order(instId=token + "-USDT-SWAP", tdMode="cross", side="sell",
                                                 posSide="short", ordType="market", sz=amount)
                if not swap_order_id:
                    print(f"Failed to place swap order for selling {token}")
                    self.cancel_order(instId=token + "-USDT", ordId=margin_order_id)
                    return False

            # 确认订单状态
            time.sleep(10)  # 等待10秒钟以确保订单被处理
            margin_order_status = self.get_order_status(instId=token + "-USDT", ordId=margin_order_id)
            swap_order_status = self.get_order_status(instId=token + "-USDT-SWAP", ordId=swap_order_id)

            if margin_order_status == 'filled' and swap_order_status == 'filled':
                print(f"Both orders for {token} filled successfully.")
                return True
            else:
                print(f"Order status check failed for {token}: Margin order status: {margin_order_status}, Swap order status: {swap_order_status}")
                if margin_order_status == 'filled' and swap_order_status != 'filled':
                    self.cancel_order(instId=token + "-USDT-SWAP", ordId=swap_order_id)
                    self.close_position(instId=token + "-USDT", mgnMode="cross", ccy="USDT", posSide="net")
                if swap_order_status == 'filled' and margin_order_status != 'filled':
                    self.cancel_order(instId=token + "-USDT", ordId=margin_order_id)
                    self.close_position(instId=token + "-USDT-SWAP", mgnMode="cross", ccy="USDT", posSide=self.tradeAPI.get_order(instId=token + "-USDT-SWAP", ordId=swap_order_id)["data"][0]["posSide"])
                return False

        except Exception as e:
            print(f"Error executing arbitrage trade: {e}")
            return False
