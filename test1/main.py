from strategy import ArbitrageStrategy
from position1 import PositionMonitor
from trade1 import TradeExecutor
import configparser

# 读取配置文件
config = configparser.ConfigParser()
config.read('config.ini')

# 设置API密钥等信息
api_key = config['API']['api_key']
secret_key = config['API']['secret_key']
passphrase = config['API']['passphrase']
flag = config['SETTINGS']['flag']


if __name__ == "__main__":
    api_key = api_key
    secret_key = secret_key
    passphrase = passphrase
    flag = flag

    trade_executor = TradeExecutor(api_key, secret_key, passphrase, flag)
    position_monitor = PositionMonitor(api_key, secret_key, passphrase, flag)
    scraper = PotentialSetScraper()

    strategy = ArbitrageStrategy(trade_executor, position_monitor, scraper)
    strategy.execute()
