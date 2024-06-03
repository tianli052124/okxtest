# new_position.py

import pandas as pd
import asyncio
import logging
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
        self.unpaired_positions = []

        self.private_ws_manager = WebSocketManager("wss://wspap.okx.com:8443/ws/v5/private?brokerId=9999", api_key, secret_key, passphrase)
        self.public_ws_manager = WebSocketManager("wss://wspap.okx.com:8443/ws/v5/public?brokerId=9999")

    async def update_positions(self, message):
        for item in message.get('data', []):
            self._update_balances(item.get('balData', []))
            await self._update_positions(item.get('posData', []))

        self.positions_df = self.positions_df[self.positions_df['pos'] != '0']
        if self.positions_df.empty:
            logging.info("All positions have been closed.")
        else:
            logging.info("Current positions:\n%s", self.positions_df)

        self.check_pairs()

    def _update_balances(self, bal_data):
        for token in bal_data:
            if token['ccy'] != 'USDT':
                self._update_or_add_position(token['ccy'] + '-USDT', 'SPOT', token['cashBal'], None)

    async def _update_positions(self, pos_data):
        for pos in pos_data:
            if pos['pos'] == '0':
                self._update_or_add_position(pos['instId'], pos['instType'], pos['pos'], pos['posSide'])
                await self.public_ws_manager.unsubscribe('funding-rate', pos['instId'])
                self.subscribed_instruments.discard(pos['instId'])
            else:
                self._update_or_add_position(pos['instId'], pos['instType'], pos['pos'], pos['posSide'])
                if pos['instId'] not in self.subscribed_instruments:
                    await self.public_ws_manager.subscribe('funding-rate', instId=pos['instId'])
                    self.subscribed_instruments.add(pos['instId'])

    def _update_or_add_position(self, inst_id, inst_type, pos, pos_side):
        if inst_id in self.positions_df['instId'].values:
            self.positions_df.loc[self.positions_df['instId'] == inst_id, ['instType', 'pos', 'posSide']] = inst_type, pos, pos_side
        else:
            new_row = {'instId': inst_id, 'instType': inst_type, 'pos': pos, 'posSide': pos_side, 'fundingRate': None}
            self.positions_df = pd.concat([self.positions_df, pd.DataFrame([new_row])], ignore_index=True)

    def check_pairs(self):
        token_positions = {}
        for _, row in self.positions_df.iterrows():
            base_token = row['instId'].split('-')[0]
            token_positions.setdefault(base_token, {'spot': None, 'swap': None, 'posSide': None})
            if row['instType'] == 'SPOT':
                token_positions[base_token]['spot'] = row['instId']
            elif row['instType'] == 'SWAP':
                token_positions[base_token]['swap'] = row['instId']
                token_positions[base_token]['posSide'] = row['posSide']

        self.current_pairs = [(token, 'negative' if pos['posSide'] == 'long' else 'positive')
                              for token, pos in token_positions.items() if pos['spot'] and pos['swap']]

        self.unpaired_positions = [(token, 'SPOT') if pos['spot'] else (token, 'SWAP') for token, pos in
                                   token_positions.items() if not (pos['spot'] and pos['swap'])]

    def get_current_pairs_count(self):
        self.check_pairs()
        return len(self.current_pairs)

    def get_updated_current_pairs(self):
        self.check_pairs()
        return self.current_pairs

    async def handle_private_message(self):
        async for message in self.private_ws_manager.receive():
            if message.get('event') == 'login' and message.get('code') == '0':
                logging.info("Private WebSocket login successful")
                await self.private_ws_manager.subscribe('balance_and_position')
            elif message.get('event') == 'subscribe':
                logging.info("Subscribed to: %s", message.get('arg'))
            elif message.get('arg', {}).get('channel') == 'balance_and_position':
                logging.info("%s", message)
                await self.update_positions(message)

    async def handle_public_message(self):
        async for message in self.public_ws_manager.receive():
            if message.get('arg', {}).get('channel') == 'funding-rate':
                for data in message.get('data', []):
                    self.positions_df.loc[self.positions_df['instId'] == data['instId'], 'fundingRate'] = data['fundingRate']
                    logging.info("Updated funding rate for instrument %s: %s", data['instId'], data['fundingRate'])
                    logging.info("Updated positions DataFrame:\n%s", self.positions_df)

    async def start(self):
        await self.private_ws_manager.connect()
        await self.public_ws_manager.connect()
        await asyncio.gather(self.handle_private_message(), self.handle_public_message())
