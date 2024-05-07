import okx.Account as Account
import okx.PublicData as PublicData
import time
import getmarketdata

# API验证信息
api_key = "e1b9fa18-438f-4186-8679-2e1a31cac369"
secret_key = "ED6A1408691C36597446782AA57D8BC3"
passphrase = "Llz0102!!"

# API验证
flag = "1"
publicdataAPI = PublicData.PublicAPI(flag=flag)
accountAPI = Account.AccountAPI(api_key, secret_key, passphrase, False, flag)

# 查询手续费（由于全品种手续费都一样，所以用BTC查询）
# 获取现货手续费dataset
spotrate = accountAPI.get_fee_rates(instType="SPOT", instId="BTC-USDT")
# 获取合约手续费dataset
swaprate = accountAPI.get_fee_rates(instType="SWAP", instFamily="BTC-USDT")
# 获取现货挂单手续费
spotratemaker = float(spotrate["data"][0]["maker"])
# 获取现货吃单手续费
spotratetaker = float(spotrate["data"][0]["taker"])
# 获取合约挂单手续费
swapratemaker = float(swaprate["data"][0]["makerU"])
# 获取合约吃单手续费
swapratetaker = float(swaprate["data"][0]["takerU"])

# 导入按市值排列前50的币的列表
tokenlist = getmarketdata.arbitrageset

def gettokeninfo(item):
    # 获取资金费率信息
    InstRate = publicdataAPI.get_funding_rate(instId=item + "-USDT-SWAP",)
    # 获取资金费率
    feerate = float(InstRate["data"][0]["fundingRate"])
    # 获取标记价格
    mark_price = float(publicdataAPI.get_mark_price(instType="SWAP", instFamily=item+"-USDT")["data"][0]["markPx"])
    return item, feerate, mark_price

def checkarbitrage(token):
    threshold_funding_rate = 0.0001
    tokeninfo = gettokeninfo(token)
    # 费率大于0则选择正套法，买入现货，卖出永续合约
    if tokeninfo[1]>threshold_funding_rate and :
        # 查看扣除手续费以后是否还有套利机会
        diff = token[1]-
        if diff > 0:


for token in tokenlist:
    try:
        print(gettokeninfo(token) [2])
        time.sleep(2)
    except:
        print("数据获取失败")
