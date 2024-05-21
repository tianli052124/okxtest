import time

from trade1 import TradeExecutor
from position1 import PositionMonitor

import configparser

# 读取配置文件
config = configparser.ConfigParser()
config.read('config.ini')

# 设置API密钥等信息
api_key = config['API']['api_key']
secret_key = config['API']['secret_key']
passphrase = config['API']['passphrase']
flag = config['SETTINGS']['flag']

# 初始化交易执行器
trade_executor = TradeExecutor(api_key, secret_key, passphrase, flag)

# 初始化持仓监控器
position_monitor = PositionMonitor(api_key, secret_key, passphrase, flag)

position_monitor.start()
