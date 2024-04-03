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

item = "BTC"

publicdataAPI = PublicData.PublicAPI(flag=flag)
accountAPI = Account.AccountAPI(api_key, secret_key, passphrase, False, flag)

# 获取资金费率信息
InstRate = publicdataAPI.get_funding_rate(
    instId="BTC-USDT-SWAP",
)

# 获取资金费
Feerate = InstRate["data"][0]["fundingRate"]

# 获取现货手续费dataset
SpotRate = accountAPI.get_fee_rates(instType="SPOT", instId="BTC-USDT")
# 获取合约手续费dataset
SwapRate = accountAPI.get_fee_rates(instType="SWAP", instFamily="BTC-USDT")


# 获取现货挂单手续费
SpotRateMaker = SpotRate["data"][0]["maker"]
# 获取现货吃单手续费
SpotRateTaker = SpotRate["data"][0]["taker"]

# 获取合约挂单手续费
SwapRateMaker = SwapRate["data"][0]["makerU"]
# 获取合约吃单手续费
SwapRateTaker = SwapRate["data"][0]["takerU"]


print(
    InstRate["data"][0]["fundingRate"],
    InstRate["data"][0]["settFundingRate"],
    InstRate["data"][0]["settState"],
    InstRate["data"][0]["method"],
)
