# okxtest

1.getdata.py从OKX的网站上找到适合进行套利的token，处理以后按币的市值排序，选前50大的币编入套利set

2.checkarbitrage.py检测套利set中所有币是否有潜在机会套利，机会属于正套还是反套。

资金费用 = 持仓仓位价值 × 本周期资金费率

持仓仓位价值为： 标记价格 × 合约张数 × 合约面值 × 合约乘数