from origin.arbitragestrategy import ArbitrageStrategy
from tradeexecutor import TradeExecutor
from position import PositionMonitor


if __name__ == "__main__":
    import configparser

    # 读取配置文件
    config = configparser.ConfigParser()
    config.read('config.ini')

    # 设置API密钥等信息
    api_key = config['API']['api_key']
    secret_key = config['API']['secret_key']
    passphrase = config['API']['passphrase']
    flag = config['SETTINGS']['flag']

    # 初始化策略
    arbitrage_strategy = ArbitrageStrategy(api_key, secret_key, passphrase, flag)

    # 初始化交易执行器
    trade_executor = TradeExecutor(api_key, secret_key, passphrase, flag)

    # 初始化仓位监控
    position_monitor = PositionMonitor(api_key, secret_key, passphrase, flag)
    position_monitor.start()

    # 示例: 检查并执行套利机会
    token = "ETH"
    arbitrage_opportunity = arbitrage_strategy.check_arbitrage(token)
    if arbitrage_opportunity:
        token, diff, mode, contract_value = arbitrage_opportunity
        portion_size = 1000  # 示例值，请根据实际情况调整
        if trade_executor.execute_arbitrage_trade(token, mode, portion_size, arbitrage_opportunity, contract_value):
            print("Arbitrage trade executed successfully.")
        else:
            print("Arbitrage trade execution failed.")
