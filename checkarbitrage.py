list = [
    "BTC",
    "ETH",
    "SOL",
    "DOGE",
    "ORDI",
    "XRP",
    "PEPE",
    "LTC",
    "WLD",
    "FIL",
    "OP",
    "BCH",
    "SHIB",
    "CFX",
    "AVAX",
    "ARB",
    "APT",
    "BNB",
    "ADA",
    "FTM",
    "TON",
    "NEAR",
    "SATS",
    "MATIC",
    "SUI",
    "TRB",
    "STX",
    "LINK",
    "ETC",
    "TIA",
    "STRK",
    "YGG",
    "BIGTIME",
    "ZRX",
    "DOT",
    "RNDR",
    "DYDX",
    "GALA",
    "UNI",
    "PYTH",
    "ICP",
    "MKR",
    "AR",
    "JUP",
    "LUNA",
    "EOS",
    "AEVO",
    "PEOPLE",
    "ETHFI",
    "BSV",
]

import json
import okx.Account as Account
import okx.PublicData as PublicData


# 选择实盘还是模拟
flag = "1"  # live trading: 0, demo trading: 1

# 获取对应API信息
api_key = "e1b9fa18-438f-4186-8679-2e1a31cac369"
secret_key = "ED6A1408691C36597446782AA57D8BC3"
passphrase = "Llz0102!!"

item = "DOGE"

publicdataAPI = PublicData.PublicAPI(flag=flag)
accountAPI = Account.AccountAPI(api_key, secret_key, passphrase, False, flag)

# 获取资金费率信息
InstRate = publicdataAPI.get_funding_rate(
    instId=item+"-USDT-SWAP",
)

# 获取资金费
Feerate = float(InstRate["data"][0]["fundingRate"])

# 获取现货手续费dataset
SpotRate = accountAPI.get_fee_rates(instType="SPOT", instId=item+"-USDT")
# 获取合约手续费dataset
SwapRate = accountAPI.get_fee_rates(instType="SWAP", instFamily=item+"-USDT")


# 获取现货挂单手续费
SpotRateMaker = float(SpotRate["data"][0]["maker"])
# 获取现货吃单手续费
SpotRateTaker = float(SpotRate["data"][0]["taker"])

# 获取合约挂单手续费
SwapRateMaker = float(SwapRate["data"][0]["makerU"])
# 获取合约吃单手续费
SwapRateTaker = float(SwapRate["data"][0]["takerU"])

#获取标记价格
Markprice = float(publicdataAPI.get_mark_price(instType="SWAP",instId=item+"-USDT-SWAP")["data"][0]["markPx"])
Spotprice = float(publicdataAPI.get_mark_price(instType="MARGIN",instId=item+"-USDT")["data"][0]["markPx"])

print(
    Feerate*Markprice+SwapRateTaker*Markprice+SpotRateTaker*Spotprice
)
