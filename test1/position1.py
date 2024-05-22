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

        self.message_queue = Queue()
        self.processing_thread = threading.Thread(target=self.process_message_queue)
        self.processing_thread.daemon = True
        self.processing_thread.start()

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
        sub_data = {"op": "subscribe", "args": [{"channel": "positions", "instType": "ANY"}]}
        ws.send(json.dumps(sub_data))

    def subscribe_funding_rate(self, ws, instId):
        sub_data = {"op": "subscribe", "args": [{"channel": "funding-rate", "instId": instId}]}
        ws.send(json.dumps(sub_data))

    def update_positions(self, message):
        print(message)
        new_positions = pd.DataFrame(message['data'], columns=['instId', 'instType', 'realizedPnl', 'upl', 'posSide'])
        new_positions['fundingRate'] = None

        for instId in new_positions['instId']:
            if instId not in self.subscribed_instruments:
                self.subscribe_funding_rate(self.public_ws, instId)
                self.subscribed_instruments.add(instId)
                print(f"Subscribed to funding rate for instrument {instId}")

        self.positions_df = new_positions

        if self.positions_df.empty:
            print("All positions have been closed.")
        else:
            print(f"the current positions are:{self.positions_df}")

        self.check_pairs()

    def check_pairs(self):
        currentpairs = []
        token_positions = {}
        for _, row in self.positions_df.iterrows():
            base_token = row['instId'].split('-')[0]
            if base_token not in token_positions:
                token_positions[base_token] = {'margin': None, 'swap': None, 'posSide': None}
            if row['instType'] == 'MARGIN':
                token_positions[base_token]['margin'] = row['instId']
            elif row['instType'] == 'SWAP':
                token_positions[base_token]['swap'] = row['instId']
                token_positions[base_token]['posSide'] = row['posSide']

        for base_token, positions in token_positions.items():
            if positions['margin'] and positions['swap']:
                mode = 'negative' if positions['posSide'] == 'long' else 'positive'
                currentpairs.append((base_token, mode))

        self.current_pairs = currentpairs

    def get_current_pairs_count(self):
        self.check_pairs()
        return len(self.current_pairs)

    def on_private_message(self, ws, message):
        message = json.loads(message)
        self.message_queue.put(("private", message))

    def on_public_message(self, ws, message):
        message = json.loads(message)
        self.message_queue.put(("public", message))

    def process_message_queue(self):
        while True:
            msg_type, message = self.message_queue.get()
            if msg_type == "private":
                self.reset_heartbeat_timer(self.private_ws)
                if message.get('event') == 'login' and message.get('code') == '0':
                    print("Private WebSocket login successful")
                    self.subscribe_positions(self.private_ws)
                elif message.get('event') == 'subscribe':
                    print(f"Subscribed to: {message.get('arg')}")
                elif 'arg' in message and message['arg']['channel'] == 'positions':
                    self.update_positions(message)
            elif msg_type == "public":
                self.reset_heartbeat_timer(self.public_ws)
                if 'arg' in message and message['arg']['channel'] == 'funding-rate' and 'data' in message:
                    for data in message['data']:
                        instId, fundingRate = data['instId'], data['fundingRate']
                        if instId and fundingRate:
                            self.positions_df.loc[self.positions_df['instId'] == instId, 'fundingRate'] = fundingRate
                            print(f"Updated funding rate for instrument {instId}: {fundingRate}")
                            print("Updated positions DataFrame:")
                            print(self.positions_df)

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
