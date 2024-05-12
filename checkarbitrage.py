import okx.Account as Account
import okx.PublicData as PublicData
import okx.MarketData as MarketData
import time
import getmarketdata

# API验证信息
api_key = "e1b9fa18-438f-4186-8679-2e1a31cac369"
secret_key = "ED6A1408691C36597446782AA57D8BC3"
passphrase = "Llz0102!!"

# API验证
flag = "1"
publicdataAPI = PublicData.PublicAPI(flag=flag)
marketdataAPI = MarketData.MarketAPI(flag=flag)
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

set = []
def gettokeninfo(item):
    # 获取资金费率信息
    InstRate = publicdataAPI.get_funding_rate(instId=item + "-USDT-SWAP")
    # 检查crypto是否在交易所上市
    if InstRate["code"] == "51001":
        print(item+"未上线")
        return None
    else:
        # 获取资金费率
        feerate = float(InstRate["data"][0]["fundingRate"])
        # 获取标记价格
        mark_price = float(publicdataAPI.get_mark_price(instType="SWAP", instFamily=item+"-USDT")["data"][0]["markPx"])
        #获取现货价格
        spot_price = float(marketdataAPI.get_ticker(instId=item+"-USDT")["data"][0]["last"])
        return item, feerate, mark_price, spot_price

def checkarbitrage(token):
    threshold_funding_rate = 0.0001
    tokeninfo = gettokeninfo(token)
    if tokeninfo == None:
        return None
    else:
        # 费率为正，费率大于费率阈值则选择正套法，买入现货，卖出永续合约
        if tokeninfo[1] > threshold_funding_rate and tokeninfo[2] / tokeninfo[3] > 1.002:
            # 查看扣除手续费以后是否还有套利机会
            diff = tokeninfo[2] * tokeninfo[1] - tokeninfo[2] * swapratetaker * 2.05 - tokeninfo[
                3] * spotratetaker * 2.05
            if diff > 0:
                print(token, "找到了一个正套标的")
                return token, diff, "positive"
            else:
                print(diff)
        # 费率为负，费率小于费率阈值则选择反套法，上杠杆卖出现货，买入永续合约
        elif tokeninfo[1] < -threshold_funding_rate and tokeninfo[2] / tokeninfo[3] < 1.002:
            # 检查扣除手续费和杠杆利息后的套利机会情况
            interestrate = float(accountAPI.get_interest_rate(token)["data"][0]["interestRate"])
            diff = -tokeninfo[2] * tokeninfo[1] - tokeninfo[2] * swapratetaker * 2.05 - tokeninfo[
                3] * spotratetaker * 2.05 - interestrate / 24 * 4
            if diff > 0:
                print(token, "找到了一个反套标的")
                return token, diff, "negative"
            else:
                print(diff)

for token in tokenlist:
    time.sleep(1)
    result = checkarbitrage(token)
    if result is not None:
        set.append(result)

print(set)