import websocket
import json
import time
import hmac
import hashlib
import base64
import pandas as pd
import threading


class PositionMonitor:
    def __init__(self, api_key, secret_key, passphrase, flag):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.flag = flag
        self.positions_df = pd.DataFrame(columns=['instId', 'instType', 'realizedPnl', 'upl', 'fundingRate'])
        self.subscribed_instruments = set()
        self.calculated_pairs = []
        self.private_ws_url = "wss://wspap.okx.com:8443/ws/v5/private?brokerId=9999"
        self.public_ws_url = "wss://wspap.okx.com:8443/ws/v5/public?brokerId=9999"
        self.private_ws = None
        self.public_ws = None

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

    def unsubscribe_funding_rate(self, ws, instId):
        sub_data = {"op": "unsubscribe", "args": [{"channel": "funding-rate", "instId": instId}]}
        ws.send(json.dumps(sub_data))

    def update_positions(self, message):
        for pos in message['data']:
            instId, instType, realizedPnl, upl = pos['instId'], pos['instType'], pos['realizedPnl'], pos['upl']
            if instId in self.positions_df['instId'].values:
                self.positions_df.loc[self.positions_df['instId'] == instId, ['instType', 'realizedPnl', 'upl']] = [
                    instType, realizedPnl, upl]
            else:
                new_row = pd.DataFrame([[instId, instType, realizedPnl, upl, None]], columns=self.positions_df.columns)
                self.positions_df = pd.concat([self.positions_df, new_row], ignore_index=True)
            if instType == 'SWAP' and instId not in self.subscribed_instruments:
                self.subscribe_funding_rate(self.public_ws, instId)
                self.subscribed_instruments.add(instId)
        self.unsubscribe_from_old_instruments()
        self.check_new_pairs()

    def unsubscribe_from_old_instruments(self):
        instruments_to_unsubscribe = self.subscribed_instruments.difference(set(self.positions_df['instId'].values))
        for instId in instruments_to_unsubscribe:
            self.unsubscribe_funding_rate(self.public_ws, instId)
            self.subscribed_instruments.remove(instId)
            print(f"Unsubscribed from funding rate for instrument {instId}")

    def check_new_pairs(self):
        self.calculated_pairs.clear()  # 清空 calculated_pairs 列表
        token_positions = {}
        for index, row in self.positions_df.iterrows():
            base_token = row['instId'].split('-')[0]
            if base_token not in token_positions:
                token_positions[base_token] = {'margin': None, 'swap': None}
            if row['instType'] == 'MARGIN':
                token_positions[base_token]['margin'] = row['instId']
            elif row['instType'] == 'SWAP':
                token_positions[base_token]['swap'] = row['instId']

        for base_token, positions in token_positions.items():
            if positions['margin'] and positions['swap']:
                self.calculated_pairs.append((positions['margin'], positions['swap']))

    def get_current_pairs_count(self):
        return len(self.calculated_pairs)

    def on_private_message(self, ws, message):
        message = json.loads(message)
        print(f"Received private message: {message}")
        if message.get('event') == 'login' and message.get('code') == '0':
            print("Private WebSocket login successful")
            self.subscribe_positions(ws)
        elif message.get('event') == 'subscribe':
            print(f"Subscribed to: {message.get('arg')}")
        elif 'arg' in message and message['arg']['channel'] == 'positions':
            self.update_positions(message)

    def on_public_message(self, ws, message):
        message = json.loads(message)
        print(f"Received public message: {message}")
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

    def on_close(self, ws):
        print("Connection closed")

    def on_open_private(self, ws):
        print("Private connection opened")
        self.authenticate(ws)

    def on_open_public(self, ws):
        print("Public connection opened")

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

        private_ws_thread.start()
        public_ws_thread.start()
