import json
import okx.Account as Account
import okx.Trade as Trade
import main

# 选择实盘还是模拟
flag = "1"  # live trading: 0, demo trading: 1

# 获取对应API信息
api_key = "e1b9fa18-438f-4186-8679-2e1a31cac369"
secret_key = "ED6A1408691C36597446782AA57D8BC3"
passphrase = "Llz0102!!"

# 获取账户信息
accountAPI = Account.AccountAPI(api_key, secret_key, passphrase, False, flag)
tradeAPI = Trade.TradeAPI(api_key, secret_key, passphrase, False, flag)
result = accountAPI.get_account_balance()

#杠杆率设定
leverage_ratio = 2

# 按收益率排序
portfolio = main.df.sort_values(by=1, ascending=False)

# 选预期收益率最高的3个
portfolio = portfolio.head(3)
print(portfolio)
# 获取现金余额
cash_balance = float(result["data"][0]["details"][0]["cashBal"])
# 用三分之一的现金进行套利
portion_size = cash_balance/4

for index, row in portfolio.iterrows():
    mode = row[2]
    tokeninfo = main.gettokeninfo(row[0])

    if mode == "negative":
        maxsize = float(accountAPI.get_max_order_size(instId=row[0] + "-USDT", tdMode="cross", ccy="USDT")["data"][0]["maxSell"])
        amount = round(min(portion_size / tokeninfo[3], maxsize)/row[3],0)
        accountAPI.set_leverage(instId=row[0] + "-USDT-SWAP", lever=3, mgnMode="cross")
        accountAPI.set_leverage(instId=row[0] + "-USDT", lever=3, mgnMode="cross")
        tradeAPI.place_order(instId=row[0]+"-USDT", ccy="USDT", tdMode="cross", side="sell", ordType="market",sz=amount*row[3], tgtCcy="base_ccy")
        tradeAPI.place_order(instId=row[0]+"-USDT-SWAP", tdMode="cross", side="buy", posSide="long", ordType="market", sz=amount)
    else:
        maxsize = float(accountAPI.get_max_order_size(instId=row[0] + "-USDT", tdMode="cross", ccy="USDT")["data"][0]["maxBuy"])
        amount = round(min(portion_size / tokeninfo[3], maxsize)/row[3],0)
        print(amount)
        print(row[3])
        accountAPI.set_leverage(instId=row[0] + "-USDT-SWAP", lever=3, mgnMode="cross")
        accountAPI.set_leverage(instId=row[0] + "-USDT", lever=3, mgnMode="cross")
        tradeAPI.place_order(instId=row[0] + "-USDT", ccy="USDT", tdMode="cross", side="buy", ordType="limit",sz = amount*row[3] , px=tokeninfo[3])
        tradeAPI.place_order(instId=row[0] + "-USDT-SWAP", tdMode="cross", side="sell", posSide="short", ordType="market", sz=amount)
