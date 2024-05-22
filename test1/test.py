import time

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


# position1.py

import websocket
import json
import time
import hmac
import hashlib
import base64
import pandas as pd
import threading
from queue import Queue


class PositionMonitor:
    def __init__(self, api_key, secret_key, passphrase, flag):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.flag = flag
        self.positions_df = pd.DataFrame(columns=['instId', 'instType', 'realizedPnl', 'upl', 'fundingRate', 'posSide'])
        self.subscribed_instruments = set()
        self.current_pairs = []
        self.private_ws_url = "wss://wspap.okx.com:8443/ws/v5/private?brokerId=9999"
        self.public_ws_url = "wss://wspap.okx.com:8443/ws/v5/public?brokerId=9999"
        self.private_ws = None
        self.public_ws = None
        self.retry_attempts = 10  # Number of retry attempts
        self.retry_delay = 5  # Delay between retry attempts in seconds
        self.heartbeat_interval = 25  # Heartbeat interval in seconds
        self.heartbeat_timer = None


    def authenticate(self, ws):
        timestamp = str(int(time.time()))
        message = timestamp + 'GET' + '/users/self/verify'
        hmac_key = base64.b64encode(
            hmac.new(bytes(self.secret_key, 'utf-8'), bytes(message, 'utf-8'), digestmod=hashlib.sha256).digest()
        )
        auth_data = {
            "op": "login",
            "args": [
                {
                    "apiKey": self.api_key,
                    "passphrase": self.passphrase,
                    "timestamp": timestamp,
                    "sign": hmac_key.decode('utf-8')
                }
            ]
        }
        ws.send(json.dumps(auth_data))

    def subscribe_positions(self, ws):
        sub_data = {"op": "subscribe", "args": [{"channel": "balance_and_position"}]}
        ws.send(json.dumps(sub_data))

    def subscribe_funding_rate(self, ws, instId):
        sub_data = {"op": "subscribe", "args": [{"channel": "funding-rate", "instId": instId}]}
        ws.send(json.dumps(sub_data))

    def get_current_pairs_count(self):
        self.check_pairs()
        return len(self.current_pairs)

    def on_private_message(self, ws, message):
        message = json.loads(message)
        print(json.dumps(message, indent=4))
        if message.get('event') == 'login' and message.get('code') == '0':
            print("Private WebSocket login successful")
            self.subscribe_positions(self.private_ws)
        elif message.get('event') == 'subscribe':
            print(f"Subscribed to: {message.get('arg')}")
        elif 'arg' in message and message['arg']['channel'] == 'balance_and_position':
            print("Received balance and position data")
            posdata = message['data'][0]['posData']
            df = pd.DataFrame(posdata, columns=['instId', 'instType', 'posSide'])


    def on_public_message(self, ws, message):
        message = json.loads(message)
        print(message)

    def on_error(self, ws, error):
        print(f"Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print(f"Connection closed with code: {close_status_code}, message: {close_msg}")
        self.retry_connection(ws)

    def retry_connection(self, ws):
        for attempt in range(self.retry_attempts):
            try:
                print(f"Attempting to reconnect, attempt {attempt + 1}/{self.retry_attempts}")
                ws.run_forever()
                break
            except Exception as e:
                print(f"Reconnection attempt {attempt + 1} failed: {e}")
                time.sleep(self.retry_delay)

    def on_open_private(self, ws):
        print("Private connection opened")
        self.authenticate(ws)

    def on_open_public(self, ws):
        print("Public connection opened")

    def reset_heartbeat_timer(self, ws):
        if self.heartbeat_timer:
            self.heartbeat_timer.cancel()
        self.heartbeat_timer = threading.Timer(self.heartbeat_interval, self.send_ping, [ws])
        self.heartbeat_timer.start()

    def send_ping(self, ws):
        try:
            ws.send('ping')
            print("Ping sent")
        except Exception as e:
            print(f"Error sending ping: {e}")
            self.retry_connection(ws)

    def get_current_positions(self):
        return self.positions_df

    def start(self):
        self.private_ws = websocket.WebSocketApp(
            self.private_ws_url,
            on_message=self.on_private_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open_private
        )

        self.public_ws = websocket.WebSocketApp(
            self.public_ws_url,
            on_message=self.on_public_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open_public
        )

        private_ws_thread = threading.Thread(target=self.private_ws.run_forever)
        public_ws_thread = threading.Thread(target=self.public_ws.run_forever)

        private_ws_thread.daemon = True
        public_ws_thread.daemon = True

        private_ws_thread.start()
        public_ws_thread.start()

        print("Position monitoring started.")


# 初始化交易执行器
trade_executor = TradeExecutor(api_key, secret_key, passphrase, flag)

# # 初始化持仓监控器
position_monitor = PositionMonitor(api_key, secret_key, passphrase, flag)

position_monitor.start()

time.sleep(600)

