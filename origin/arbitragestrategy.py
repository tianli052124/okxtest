import okx.Account as Account
import okx.PublicData as PublicData
import okx.MarketData as MarketData

class ArbitrageStrategy:
    def __init__(self, api_key, secret_key, passphrase, flag="1"):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.flag = flag
        self.publicdataAPI = PublicData.PublicAPI(flag=flag)
        self.marketdataAPI = MarketData.MarketAPI(flag=flag)
        self.accountAPI = Account.AccountAPI(api_key, secret_key, passphrase, False, flag)

    def get_fee_rates(self):
        try:
            fee_data = self.accountAPI.get_fee_rates()
            spot_taker = float(fee_data["data"]["spot"]["taker"])
            swap_taker = float(fee_data["data"]["swap"]["taker"])
            return {"spot_taker": spot_taker, "swap_taker": swap_taker}
        except Exception as e:
            print(f"Error getting fee rates: {e}")
            return {"spot_taker": 0.001, "swap_taker": 0.001}  # 默认值

    def get_token_info(self, token):
        try:
            inst_rate = self.publicdataAPI.get_funding_rate(instId=f"{token}-USDT-SWAP")
            if inst_rate["code"] == "51001":
                print(f"{token}未上线")
                return None

            leverage_info = self.accountAPI.set_leverage(instId=f"{token}-USDT", lever="5", mgnMode="cross")
            if leverage_info["code"] == "54000":
                print(f"{token}不支持杠杆")
                return None

            feerate = float(inst_rate["data"][0]["fundingRate"])
            mark_price = float(self.publicdataAPI.get_mark_price(instType="SWAP", instFamily=f"{token}-USDT")["data"][0]["markPx"])
            spot_price = float(self.marketdataAPI.get_ticker(instId=f"{token}-USDT")["data"][0]["last"])
            ct_val = float(self.publicdataAPI.get_instruments(instType="SWAP", instFamily=f"{token}-USDT")["data"][0]["ctVal"])

            return token, feerate, mark_price, spot_price, ct_val
        except Exception as e:
            print(f"Error getting token info: {e}")
            return None

    def check_arbitrage(self, token):
        threshold_funding_rate = 0.0001
        fee_rates = self.get_fee_rates()
        token_info = self.get_token_info(token)
        if not token_info:
            return None

        token, feerate, mark_price, spot_price, ct_val = token_info

        if feerate > threshold_funding_rate and mark_price / spot_price > 1.001:
            diff = mark_price * feerate - mark_price * fee_rates["swap_taker"] * 2 - spot_price * fee_rates["spot_taker"] * 2
            if diff > 0:
                print(f"{token}找到了一个正套标的")
                return token, diff, "positive", ct_val

        elif feerate < -threshold_funding_rate and spot_price / mark_price > 1.001:
            interest_rate = float(self.accountAPI.get_interest_rate(token)["data"][0]["interestRate"])
            diff = -mark_price * feerate - mark_price * fee_rates["swap_taker"] * 2 - spot_price * fee_rates["spot_taker"] * 2 - interest_rate / 24 * 4
            if diff > 0:
                print(f"{token}找到了一个反套标的")
                return token, diff, "negative", ct_val

        return None
