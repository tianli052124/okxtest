# OKXTEST小小的说明

### 套利原理

在加密货币交易所中，如果持有永续合约（swap）的话，是有一个资金费率（funding rate）指标的。资金费率是一个动态的指标，每8小时结算一次。
<p align="center">
<img alt="fundingrate" height="500" src="https://www.okx.com/cdn/assets/plugins/announcements/contentful/tofttmniq0qv/7qPES7FdPRnqwPywfZIbIR/15a7c6b3b0d9a1fd0a93a27b7dfbf6c7/11.jpg" width="250"/>
</p>
结算时间在GMT+8的每天的00:00、08:00、16:00。所以在结算时间前，如果持有永续合约，会有一个资金费率的收入或支出。所以我们只要在每个结算时间前15-20分钟持有永续合约，就可以获得资金费率的收入。由于永续合约本质上是一种期货，价格也会波动，所以我们要同时持有现货进行对冲。

### 套利策略
- 正套利：
  - 开单策略：当资金费率为正，一般资金费为正，说明市场中做多人数较多，永续合约价格大概率高于现货价格，持有做空方向的永续合约，同时买入现货实现对冲。
  - 平仓策略：当资金费转为负数并小于平仓阈值时平仓。
- 反套利：
  - 开单策略：当资金费率为负，一般资金费为负，说明市场中做空人数较多，永续合约价格大概率低于现货价格，持有做多方向的永续合约，同时借币卖出现货对冲。
  - 平仓策略：当资金费转为正数并大于平仓阈值时平仓。
- 注意事项：
  - 反套的时候要卖出现货比较麻烦。一般需要借币卖出，所以会产生利息，会摊薄本来就少的收益。

### 项目
test2_positive_only是纯正套策略，只在资金费率为正时进行套利，只要资金费率大于阈值并且期现价差足够大就开仓，一直持仓直到资金费率小于平仓阈值。这样可以避免频繁开关仓造成的手续费损失。

### 细节

1. 下单逻辑：目前重心还是在防止单腿成交上。在执行套利组合时，先检查现货和永续合约的价格差，如果价格差大于千分之二，就进行套利。套利时，需要根据组合流动性来下单防止单腿成交，从流动性较差的一腿开始，成交了再下单另一腿。

### 已经完成的点

1. 从OKX的网站上找到适合进行套利的token，处理以后按币的市值排序，选前50大的币编入套利set。

2. arbitragechecker检测套利set中所有币是否有潜在机会套利，机会属于正套还是反套。

3. 检查套利机会时，暂时全部使用了限价单手续费。

4. origin是项目最初原始草稿代码，test1（已废弃）是使用okx提供的sdk完成的同步代码，test2是根据api文档自己重新封装的异步代码。
5. 基本框架基本上都已完成，6月主要考虑用模拟api进行测试。

### 可以改善的点

1. 检查套利机会时倒入了合约与现货价差大于千分之二的条件，可以进一步优化，如增加记录过去7天平均价差的功能，可以根据历史数据修改开仓时的价差阈值。一般情况下价差会收敛，所以肯定是在价差越大时开仓越安全，也可以考虑在价差反转时平仓。

2. 下单时可以用冰山委托，这样可以避免单腿成交并减少对盘口的影响。但是冰山委托的问题是，如果对手盘不够深，可能会导致单腿成交。可以考虑在下单时，先检查对手盘深度，如果不够深，就不下单。

3. test2的策略是所有套利模式都上3倍杠杆，提升资金利用率进行套利，但是面临交易所利息较高的问题，不能长时间持仓。
   之后可以考虑在正套时采用纯现货不加杠杆的模式，这样进行正套时可以长时间持仓，可以避免频繁开关仓造成的手续费损失。要不然干脆就承担手续费损失在资金费结算前半小时内开仓，结算以后就平仓。

4. 平仓时目前采用的是市价平仓，可以考虑使用限价平仓，这样可以避免市价波动导致的损失，但是可能会导致平仓失败。在没有更好的数学支持前暂时采用市价平仓。

5. 之后可以考虑在反套的时候，不使用现货对冲，而是换成远期合约。

6. arbitrage的token list可以另写一个爬虫脚本，每天定时更新，这样可以保证token list的实时性。