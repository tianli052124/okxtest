import okx.Account as Account
import okx.PublicData as PublicData
import okx.MarketData as MarketData
import pandas as pd
import getpotentialset

# API验证信息
api_key = "e1b9fa18-438f-4186-8679-2e1a31cac369"
secret_key = "ED6A1408691C36597446782AA57D8BC3"
passphrase = "Llz0102!!"
flag = "1"

# 初始化API
publicdataAPI = PublicData.PublicAPI(flag=flag)
marketdataAPI = MarketData.MarketAPI(flag=flag)
accountAPI = Account.AccountAPI(api_key, secret_key, passphrase, False, flag)

# 获取手续费
def get_fee_rates():
    spotrate = accountAPI.get_fee_rates(instType="SPOT", instId="BTC-USDT")
    swaprate = accountAPI.get_fee_rates(instType="SWAP", instFamily="BTC-USDT")
    return {
        "spot_maker": float(spotrate["data"][0]["maker"]),
        "spot_taker": float(spotrate["data"][0]["taker"]),
        "swap_maker": float(swaprate["data"][0]["makerU"]),
        "swap_taker": float(swaprate["data"][0]["takerU"]),
    }

fee_rates = get_fee_rates()

# 导入按市值排列前50的币的列表
token_list = getpotentialset.arbitrageset

def get_token_info(token):
    # 获取资金费率信息
    inst_rate = publicdataAPI.get_funding_rate(instId=f"{token}-USDT-SWAP")
    if inst_rate["code"] == "51001":
        print(f"{token}未上线")
        return None

    # 检查杠杆支持
    leverage_info = accountAPI.set_leverage(instId=f"{token}-USDT", lever="5", mgnMode="cross")
    if leverage_info["code"] == "54000":
        print(f"{token}不支持杠杆")
        return None

    # 获取其他必要信息
    feerate = float(inst_rate["data"][0]["fundingRate"])
    mark_price = float(publicdataAPI.get_mark_price(instType="SWAP", instFamily=f"{token}-USDT")["data"][0]["markPx"])
    spot_price = float(marketdataAPI.get_ticker(instId=f"{token}-USDT")["data"][0]["last"])
    ct_val = float(publicdataAPI.get_instruments(instType="SWAP", instFamily=f"{token}-USDT")["data"][0]["ctVal"])

    return token, feerate, mark_price, spot_price, ct_val

def check_arbitrage(token):
    threshold_funding_rate = 0.0001
    token_info = get_token_info(token)
    if not token_info:
        return None

    token, feerate, mark_price, spot_price, ct_val = token_info

    # 正向套利
    if feerate > threshold_funding_rate and mark_price / spot_price > 1.002:
        diff = mark_price * feerate - mark_price * fee_rates["swap_taker"] * 2.05 - spot_price * fee_rates["spot_taker"] * 2.05
        if diff > 0:
            print(f"{token}找到了一个正套标的")
            return token, diff, "positive", ct_val

    # 反向套利
    elif feerate < -threshold_funding_rate and mark_price / spot_price < 1.002:
        interest_rate = float(accountAPI.get_interest_rate(token)["data"][0]["interestRate"])
        diff = -mark_price * feerate - mark_price * fee_rates["swap_taker"] * 2.05 - spot_price * fee_rates["spot_taker"] * 2.05 - interest_rate / 24 * 4
        if diff > 0:
            print(f"{token}找到了一个反套标的")
            return token, diff, "negative", ct_val

    return None

results = [check_arbitrage(token) for token in token_list if check_arbitrage(token)]
arbitrage_set = pd.DataFrame(results, columns=["Token", "Difference", "Type", "ContractValue"])
print(arbitrage_set)

# 按差异值排序并取前3
portfolio = arbitrage_set.sort_values(by="Difference", ascending=False).head(3)
print(portfolio)
