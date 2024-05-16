import okx.Account as Account
import okx.PublicData as PublicData
import okx.MarketData as MarketData
import pandas as pd

# API验证信息
api_key = "e1b9fa18-438f-4186-8679-2e1a31cac369"
secret_key = "ED6A1408691C36597446782AA57D8BC3"
passphrase = "Llz0102!!"

# API验证
flag = "1"
publicdataAPI = PublicData.PublicAPI(flag=flag)
marketdataAPI = MarketData.MarketAPI(flag=flag)
accountAPI = Account.AccountAPI(api_key, secret_key, passphrase, False, flag)

a = [('BTC', 30.934661749999997, 'positive', 0.01),  ('BNB', 1.8795050833333333e-07, 'negative', 10000000.0), ('SOL', 1.3711654187944498, 'negative', 0.01), ('FIL', 0.05954909207076776, 'positive', 0.1), ('SUI', 0.01708637525, 'positive', 1.0), ('ETHFI', 0.06161915, 'positive', 1.0), ('LINK', 0.138999275, 'positive', 1.0), ('EOS', 0.005470965889338956, 'positive', 10.0), ('DOT', 0.069227525, 'positive', 0.1), ('ATOM', 0.13472288367901394, 'positive', 0.1), ('CFX', 0.0027205511361473532, 'positive', 10.0), ('UNI', 0.05713043093388166, 'positive', 1.0), ('FTM', 0.0118124025, 'positive', 10.0)]

df = pd.DataFrame(a)
def gettokeninfo(item):
    # 获取资金费率信息
    InstRate = publicdataAPI.get_funding_rate(instId=item + "-USDT-SWAP")
    # 检查crypto是否在交易所上市
    if InstRate["code"] == "51001":
        print(item+"未上线")
        return None
    elif accountAPI.set_leverage(instId=item + "-USDT",lever="5",mgnMode="cross")["code"] == "54000":
        print(item + "不支持杠杆")
        return None
    else:
        # 获取资金费率
        feerate = float(InstRate["data"][0]["fundingRate"])
        # 获取标记价格
        mark_price = float(publicdataAPI.get_mark_price(instType="SWAP", instFamily=item+"-USDT")["data"][0]["markPx"])
        #获取现货价格
        spot_price = float(marketdataAPI.get_ticker(instId=item+"-USDT")["data"][0]["last"])
        return item, feerate, mark_price, spot_price

