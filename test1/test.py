import asyncio
import json
import hmac
import hashlib
import base64
import time
import pandas as pd
from websockets import connect
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


class PositionMonitor:
    def __init__(self, api_key, secret_key, passphrase, flag):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.flag = flag
        self.positions_df = pd.DataFrame(
            columns=['instId', 'instType', 'realizedPnl', 'upl', 'fundingRate', 'posSide', 'pos'])
        self.subscribed_instruments = set()
        self.current_pairs = []
        self.private_ws_url = "wss://wspap.okx.com:8443/ws/v5/private?brokerId=9999"
        self.public_ws_url = "wss://wspap.okx.com:8443/ws/v5/public?brokerId=9999"
        self.retry_attempts = 10  # Number of retry attempts
        self.retry_delay = 5  # Delay between retry attempts in seconds
        self.heartbeat_interval = 25  # Heartbeat interval in seconds
        self.heartbeat_task = None

    async def authenticate(self, websocket):
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
        await websocket.send(json.dumps(auth_data))

    async def subscribe_positions(self, websocket):
        sub_data = {"op": "subscribe", "args": [{"channel": "positions", "instType": "ANY"}]}
        await websocket.send(json.dumps(sub_data))

    async def subscribe_funding_rate(self, websocket, instId):
        sub_data = {"op": "subscribe", "args": [{"channel": "funding-rate", "instId": instId}]}
        await websocket.send(json.dumps(sub_data))

    async def unsubscribe_funding_rate(self, websocket, instId):
        unsub_data = {"op": "unsubscribe", "args": [{"channel": "funding-rate", "instId": instId}]}
        await websocket.send(json.dumps(unsub_data))

    async def update_positions(self, message):
        new_positions = pd.DataFrame(message['data'],
                                     columns=['instId', 'instType', 'realizedPnl', 'upl', 'posSide', 'pos'])
        new_positions['fundingRate'] = None

        if 'fundingRate' not in self.positions_df.columns:
            self.positions_df['fundingRate'] = None
        if 'pos' not in self.positions_df.columns:
            self.positions_df['pos'] = None

        for _, new_position in new_positions.iterrows():
            instId = new_position['instId']
            pos = new_position['pos']

            if pos == '0':
                self.positions_df = self.positions_df[self.positions_df['instId'] != instId]
                if instId in self.subscribed_instruments:
                    await self.unsubscribe_funding_rate(self.public_ws, instId)
                    self.subscribed_instruments.remove(instId)
                    print(f"Unsubscribed from funding rate for instrument {instId}")
            else:
                if instId in self.positions_df['instId'].values:
                    self.positions_df.loc[
                        self.positions_df['instId'] == instId, ['instType', 'realizedPnl', 'upl', 'posSide', 'pos']] = \
                    new_position[['instType', 'realizedPnl', 'upl', 'posSide', 'pos']].values
                else:
                    self.positions_df = pd.concat([self.positions_df, pd.DataFrame([new_position])], ignore_index=True)
                    self.positions_df.loc[self.positions_df['instId'] == instId, 'fundingRate'] = None

                if instId not in self.subscribed_instruments:
                    await self.subscribe_funding_rate(self.public_ws, instId)
                    self.subscribed_instruments.add(instId)
                    print(f"Subscribed to funding rate for instrument {instId}")

        self.positions_df = self.positions_df[self.positions_df['pos'] != '0']

        if self.positions_df.empty:
            print("All positions have been closed.")
        else:
            print(f"Current positions:\n{self.positions_df}")

        self.check_pairs()
        print(self.current_pairs)

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

    async def handle_private_message(self, message):
        print(message)
        await self.reset_heartbeat_timer(self.private_ws)
        if message.get('event') == 'login' and message.get('code') == '0':
            print("Private WebSocket login successful")
            await self.subscribe_positions(self.private_ws)
        elif message.get('event') == 'subscribe':
            print(f"Subscribed to: {message.get('arg')}")
        elif 'arg' in message and message['arg']['channel'] == 'positions':
            await self.update_positions(message)

    async def handle_public_message(self, message):
        print(message)
        await self.reset_heartbeat_timer(self.public_ws)
        if 'arg' in message and message['arg']['channel'] == 'funding-rate' and 'data' in message:
            for data in message['data']:
                instId, fundingRate = data['instId'], data['fundingRate']
                if instId and fundingRate:
                    self.positions_df.loc[self.positions_df['instId'] == instId, 'fundingRate'] = fundingRate
                    print(f"Updated funding rate for instrument {instId}: {fundingRate}")
                    print("Updated positions DataFrame:")
                    print(self.positions_df)

    async def on_error(self, websocket, error):
        print(f"Error: {error}")

    async def on_close(self, websocket, close_status_code, close_msg):
        print(f"Connection closed with code: {close_status_code}, message: {close_msg}")
        await self.retry_connection(websocket)

    async def retry_connection(self, websocket):
        for attempt in range(self.retry_attempts):
            try:
                print(f"Attempting to reconnect, attempt {attempt + 1}/{self.retry_attempts}")
                await websocket.connect()
                break
            except Exception as e:
                print(f"Reconnection attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(self.retry_delay)

    async def on_open_private(self, websocket):
        print("Private connection opened")
        await self.authenticate(websocket)

    async def on_open_public(self, websocket):
        print("Public connection opened")

    async def reset_heartbeat_timer(self, websocket):
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        self.heartbeat_task = asyncio.create_task(self.send_ping(websocket))

    async def send_ping(self, websocket):
        try:
            await websocket.send('ping')
            print("Ping sent")
        except Exception as e:
            print(f"Error sending ping: {e}")
            await self.retry_connection(websocket)

    def get_current_positions(self):
        return self.positions_df

    async def start(self):
        async with connect(self.private_ws_url) as private_ws, connect(self.public_ws_url) as public_ws:
            self.private_ws = private_ws
            self.public_ws = public_ws

            await asyncio.gather(
                self.on_open_private(self.private_ws),
                self.on_open_public(self.public_ws),
                self.listen_to_ws(self.private_ws, self.handle_private_message),
                self.listen_to_ws(self.public_ws, self.handle_public_message)
            )

    async def listen_to_ws(self, websocket, message_handler):
        async for message in websocket:
            if message:  # Check if the message is not empty
                try:
                    await message_handler(json.loads(message))
                except json.JSONDecodeError:
                    print(f"Received an invalid JSON: {message}")
            else:
                print("Received an empty message.")


if __name__ == "__main__":
    monitor = PositionMonitor(api_key=api_key, secret_key=secret_key, passphrase=passphrase,
                              flag=flag)
    asyncio.run(monitor.start())
