import json
import okx.Account as Account
import okx.PublicData as PublicData


#选择实盘还是模拟
flag = "1"  # live trading: 0, demo trading: 1

#获取对应API信息
api_key = "e1b9fa18-438f-4186-8679-2e1a31cac369"
secret_key = "ED6A1408691C36597446782AA57D8BC3"
passphrase = "Llz0102!!"

#获取账户信息
accountAPI = Account.AccountAPI(api_key, secret_key, passphrase, False, flag)
result = accountAPI.get_positions()
print(json.dumps(result,sort_keys=True,indent=4))

#获取合约费率信息
publicdataAPI = PublicData.PublicAPI(flag=flag)
InstRate = publicdataAPI.get_funding_rate(
    instId="BTC-USD-SWAP",
)
print(InstRate)