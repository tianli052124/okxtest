# 纯测试用文件，用于测试异步调用的各个函数的功能

import logging
import json
import asyncio
import pandas as pd
from WebsocketManager import WebSocketManager
from okxv5_async.Account import AccountAPI
from new_position import PositionMonitor
from okxv5_async.MarketData import MarketAPI
from okxv5_async.Trade import TradeAPI
from okxv5_async.PublicData import PublicAPI
from new_trade import TradeExecutor
from arbitragechecker import ArbitrageChecker
from utils import round_to, scientific_to_float
from decimal import Decimal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PositionMonitor1:
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
        if message.get('arg', {}).get('channel') == 'account':
            # print(message.get('data')[0].get('details', []))
             self._update_balances(message.get('data')[0].get('details', []))
        elif message.get('arg', {}).get('channel') == 'positions':
            await self._update_positions(message.get('data', []))

        self.positions_df = self.positions_df[self.positions_df['pos'] != '0']
        if self.positions_df.empty:
            logging.info("All positions have been closed.")
        else:
            logging.info("Current positions:\n%s", self.positions_df)

        self.check_pairs()

    def _update_balances(self, bal_data):
        for token in bal_data:
            print(token)
            if token['ccy'] != 'USDT':
                self._update_or_add_position(token['ccy'] + '-USDT', 'SPOT', token['cashBal'], None)
            if token['eqUsd'] < 0.01:
                self._update_or_add_position(token['ccy'] + '-USDT', 'SPOT', '0', None)

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

        self.unpaired_positions = [(token, 'SPOT') if pos['spot'] else (token, 'SWAP') for token, pos in token_positions.items() if not (pos['spot'] and pos['swap'])]


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
                await self.private_ws_manager.subscribe('positions', 'ANY')
                await self.private_ws_manager.subscribe('account')
            elif message.get('event') == 'subscribe':
                logging.info("Subscribed to: %s", message.get('arg'))
            elif message.get('arg', {}).get('channel') == 'positions':
                logging.info("%s", message)
                await self.update_positions(message)
            elif message.get('arg', {}).get('channel') == 'account':
                logging.info("%s", message) # Print account info
                await self.update_positions(message)

    async def handle_public_message(self):
        async for message in self.public_ws_manager.receive():
            if message.get('arg', {}).get('channel') == 'funding-rate':
                for data in message.get('data', []):
                    self.positions_df.loc[self.positions_df['instId'] == data['instId'], 'fundingRate'] = data['fundingRate']
                    logging.info("Updated funding rate for instrument %s: %s", data['instId'], data['fundingRate'])
                    logging.info("Updated positions DataFrame:\n%s", self.positions_df)
                    print("unpaired: ", self.unpaired_positions)

    async def start(self):
        await self.private_ws_manager.connect()
        await self.public_ws_manager.connect()
        await asyncio.gather(self.handle_private_message(), self.handle_public_message())

async def main():
    api_key = "e1b9fa18-438f-4186-8679-2e1a31cac369"
    secret = "ED6A1408691C36597446782AA57D8BC3"
    passphrase = "Llz0102!!"
    flag = "1"

    account_api = AccountAPI(api_key=api_key, api_secret_key=secret, passphrase=passphrase, flag=flag)
    position_monitor = PositionMonitor(api_key, secret, passphrase, flag)
    position_monitor1 = PositionMonitor1(api_key, secret, passphrase, flag)
    marketapi = MarketAPI(api_key, secret, passphrase, flag)
    tradeexecutor = TradeExecutor(api_key, secret, passphrase, flag)
    tradeapi = TradeAPI(api_key, secret, passphrase, flag)
    arbitragechecker = ArbitrageChecker(api_key, secret, passphrase, flag)
    publicapi = PublicAPI(api_key, secret, passphrase, flag)
    basetoken = "KISHU"
    # await tradeexecutor.place_order("SOL-USDT", "cash", "sell", "limit", "100", "USDT", px=166)
    # await tradeexecutor.close_position(basetoken + "-USDT-SWAP", 'cross', 'USDT', 'short')
    # await tradeexecutor.close_position(basetoken + "-USDT", 'cross', 'USDT', 'net')
    await position_monitor1.start()
    # res = await tradeexecutor.get_order_status("SOL-USDT", "1508697189027889152")
    # spot_state, spot_fillsize = res
    # await tradeexecutor.place_order("SOL-USDT", "cash", "sell", "limit", spot_fillsize, "USDT", px=166)










if __name__ == "__main__":
    asyncio.run(main())


