import time
from okxv5_async.PublicData import PublicAPI
from okxv5_async.Account import AccountAPI
from okxv5_async.MarketData import MarketAPI


class ArbitrageChecker:
    def __init__(self, api_key, secret_key, passphrase, flag):
        self.publicAPI = PublicAPI(api_key, secret_key, passphrase, flag)
        self.accountAPI = AccountAPI(api_key, secret_key, passphrase, flag)
        self.marketAPI = MarketAPI(api_key, secret_key, passphrase, flag)
        self.cache = {}
        self.cache_timeout = 60  # Cache timeout in seconds

    async def get_fee_rates(self):
        if 'fee_rates' in self.cache and time.time() - self.cache['fee_rates']['timestamp'] < self.cache_timeout:
            return self.cache['fee_rates']['data']

        spot_rate = await self.accountAPI.get_fee_rates(instType="SPOT", instId="BTC-USDT")
        swap_rate = await self.accountAPI.get_fee_rates(instType="SWAP", instFamily="BTC-USDT")
        fee_rates = {
            "spot_maker": float(spot_rate["data"][0]["maker"]),
            "spot_taker": float(spot_rate["data"][0]["taker"]),
            "swap_maker": float(swap_rate["data"][0]["makerU"]),
            "swap_taker": float(swap_rate["data"][0]["takerU"]),
        }

        self.cache['fee_rates'] = {'data': fee_rates, 'timestamp': time.time()}
        return fee_rates

    async def get_token_info(self, token):
        cache_key = f'token_info_{token}'
        if cache_key in self.cache and time.time() - self.cache[cache_key]['timestamp'] < self.cache_timeout:
            return self.cache[cache_key]['data']

        inst_rate = await self.publicAPI.get_funding_rate(instId=f"{token}-USDT-SWAP")
        if inst_rate["code"] == "51001":
            print(f"{token}未上线")
            return None

        leverage_info = await self.accountAPI.set_leverage(instId=f"{token}-USDT", lever="5", mgnMode="cross")
        if leverage_info["code"] == "54000":
            print(f"{token}不支持杠杆")
            return None

        feerate = float(inst_rate["data"][0]["fundingRate"])
        swap_price = await self.marketAPI.get_ticker(f"{token}-USDT-SWAP")
        swap_price = float(swap_price["data"][0]["last"])
        spot_price = await self.marketAPI.get_ticker(instId=f"{token}-USDT")
        spot_price = float(spot_price["data"][0]["last"])
        ct_val = await self.publicAPI.get_instruments(instType="SWAP", instFamily=f"{token}-USDT")
        ct_val = float(ct_val["data"][0]["ctVal"])

        token_info = (token, feerate, swap_price, spot_price, ct_val)
        self.cache[cache_key] = {'data': token_info, 'timestamp': time.time()}
        return token_info

    async def check_arbitrage(self, token):
        fee_rates = await self.get_fee_rates()
        threshold_funding_rate = 0.00001
        token_info = await self.get_token_info(token)
        if not token_info:
            return None

        token, feerate, swap_price, spot_price, ct_val = token_info

        if feerate > threshold_funding_rate and swap_price / spot_price > 1.001:
            diff = swap_price * feerate - swap_price * fee_rates["swap_maker"] * 2 - spot_price * fee_rates[
                "spot_maker"] * 2
            if diff > 0:
                print(f"{token}找到了一个正套标的")
                return token, diff, "positive", ct_val

        elif feerate < -threshold_funding_rate and spot_price / swap_price > 1.001:
            interest_rate = await self.accountAPI.get_interest_rate(token)
            interest_rate = float(interest_rate["data"][0]["interestRate"])
            diff = -swap_price * feerate - swap_price * fee_rates["swap_maker"] * 2 - spot_price * fee_rates[
                "spot_maker"] * 2 - interest_rate / 24 * 4
            if diff > 0:
                print(f"{token}找到了一个反套标的")
                return token, diff, "negative", ct_val

        return None
