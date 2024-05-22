import base64
import hashlib
import hmac
import json
import threading
import time
from queue import Queue
import pandas as pd
import websocket

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
        self.retry_attempts = 10
        self.retry_delay = 5
        self.heartbeat_interval = 25
        self.heartbeat_timer = None

        self.message_queue = Queue()
        self.processing_thread = threading.Thread(target=self.process_message_queue)
        self.processing_thread.daemon = True
        self.processing_thread.start()

        # 定时刷新数据的线程
        self.refresh_interval = 10  # 每10秒刷新一次数据
        self.refresh_thread = threading.Thread(target=self.periodic_refresh)
        self.refresh_thread.daemon = True
        self.refresh_thread.start()

    def authenticate(self, ws):
        try:
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
        except Exception as e:
            print(f"Error during authentication: {e}")

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            self.message_queue.put(data)
        except Exception as e:
            print(f"Error processing message: {e}")

    def on_error(self, ws, error):
        print(f"WebSocket error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print(f"WebSocket closed: {close_status_code} - {close_msg}")
        self.reconnect()

    def on_open(self, ws):
        print("WebSocket connection opened")
        self.authenticate(ws)
        if ws == self.private_ws:
            self.subscribe_to_positions()

    def reconnect(self):
        for attempt in range(self.retry_attempts):
            try:
                if self.private_ws:
                    self.private_ws.close()
                self.private_ws = websocket.WebSocketApp(
                    self.private_ws_url,
                    on_message=self.on_message,
                    on_error=self.on_error,
                    on_close=self.on_close,
                    on_open=self.on_open,
                )
                self.private_ws.run_forever()
                break
            except Exception as e:
                print(f"Reconnect attempt {attempt + 1}/{self.retry_attempts} failed: {e}")
                time.sleep(self.retry_delay)

    def subscribe_to_positions(self):
        if self.private_ws:
            sub_data = {
                "op": "subscribe",
                "args": [{"channel": "positions"}]
            }
            self.private_ws.send(json.dumps(sub_data))

    def process_message_queue(self):
        while True:
            data = self.message_queue.get()
            if data['arg']['channel'] == 'positions':
                self.update_positions(data['data'])

    def update_positions(self, data):
        for pos in data:
            inst_id = pos['instId']
            pos_side = pos['posSide']
            # 更新 positions_df
            self.positions_df = self.positions_df.append(
                {
                    'instId': inst_id,
                    'instType': pos['instType'],
                    'realizedPnl': pos['realizedPnl'],
                    'upl': pos['upl'],
                    'fundingRate': pos.get('fundingRate', 0),
                    'posSide': pos_side
                },
                ignore_index=True
            )

    def send_heartbeat(self):
        if self.private_ws:
            self.private_ws.send('ping')
        self.heartbeat_timer = threading.Timer(self.heartbeat_interval, self.send_heartbeat)
        self.heartbeat_timer.start()

    def periodic_refresh(self):
        while True:
            self.refresh_positions()
            time.sleep(self.refresh_interval)

    def refresh_positions(self):
        try:
            positions = self.accountAPI.get_account_positions()
            if 'data' in positions:
                self.update_positions(positions['data'])
            else:
                print("Failed to refresh positions")
        except Exception as e:
            print(f"Error refreshing positions: {e}")

    def start(self):
        self.reconnect()
        self.send_heartbeat()
