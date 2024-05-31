# new_position.py

import pandas as pd
import asyncio
from WebsocketManager import WebSocketManager

class PositionMonitor:
    def __init__(self, api_key, secret_key, passphrase, flag):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.flag = flag
        self.positions_df = pd.DataFrame(columns=['instId', 'instType', 'pos', 'posSide', 'fundingRate'])
        self.subscribed_instruments = set()
        self.current_pairs = []

        private_ws_url = "wss://wspap.okx.com:8443/ws/v5/private?brokerId=9999"
        public_ws_url = "wss://wspap.okx.com:8443/ws/v5/public?brokerId=9999"

        self.private_ws_manager = WebSocketManager(private_ws_url, api_key, secret_key, passphrase)
        self.public_ws_manager = WebSocketManager(public_ws_url)

    async def update_positions(self, message):
        new_positions = pd.DataFrame(message['data'], columns=['instId', 'instType', 'posSide', 'pos'])
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
                asyncio.create_task(self.public_ws_manager.unsubscribe('funding-rate', instId))
                self.subscribed_instruments.remove(instId)
            else:
                if instId in self.positions_df['instId'].values:
                    self.positions_df.loc[self.positions_df['instId'] == instId, ['instType', 'posSide', 'pos']] = \
                    new_position[['instType', 'posSide', 'pos']].values
                else:
                    self.positions_df = pd.concat([self.positions_df, pd.DataFrame([new_position])], ignore_index=True)
                    self.positions_df.loc[self.positions_df['instId'] == instId, 'fundingRate'] = None

                if instId not in self.subscribed_instruments:
                    asyncio.create_task(self.public_ws_manager.subscribe('funding-rate', instId=instId))
                    self.subscribed_instruments.add(instId)

        self.positions_df = self.positions_df[self.positions_df['pos'] != '0']

        if self.positions_df.empty:
            print("All positions have been closed.")
        else:
            print(f"Current positions:\n{self.positions_df}")

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

    def get_updated_current_pairs(self):
        self.check_pairs()
        return self.current_pairs

    async def handle_private_message(self):
        async for message in self.private_ws_manager.receive():
            if message.get('event') == 'login' and message.get('code') == '0':
                print("Private WebSocket login successful")
                await self.private_ws_manager.subscribe('positions', instType='ANY')
            elif message.get('event') == 'subscribe':
                print(f"Subscribed to: {message.get('arg')}")
            elif 'arg' in message and message['arg']['channel'] == 'positions':
                await self.update_positions(message)

    async def handle_public_message(self):
        async for message in self.public_ws_manager.receive():
            if 'arg' in message and message['arg']['channel'] == 'funding-rate' and 'data' in message:
                for data in message['data']:
                    instId, fundingRate = data['instId'], data['fundingRate']
                    if instId and fundingRate:
                        self.positions_df.loc[self.positions_df['instId'] == instId, 'fundingRate'] = fundingRate
                        print(f"Updated funding rate for instrument {instId}: {fundingRate}")
                        print("Updated positions DataFrame:")
                        print(self.positions_df)

    async def start(self):
        await self.private_ws_manager.connect()
        await self.public_ws_manager.connect()

        private_ws_task = asyncio.create_task(self.handle_private_message())
        public_ws_task = asyncio.create_task(self.handle_public_message())

        await asyncio.gather(private_ws_task, public_ws_task)
