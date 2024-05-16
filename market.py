import websocket
import json
import time
import hmac
import hashlib
import base64
import pandas as pd
import threading

# Replace these with your actual API key, secret, and passphrase
API_KEY = 'e1b9fa18-438f-4186-8679-2e1a31cac369'
SECRET_KEY = 'ED6A1408691C36597446782AA57D8BC3'
PASSPHRASE = 'Llz0102!!'

PRIVATE_WS_URL = "wss://wspap.okx.com:8443/ws/v5/private?brokerId=9999"
PUBLIC_WS_URL = "wss://wspap.okx.com:8443/ws/v5/public?brokerId=9999"

# Initialize DataFrame for positions
positions_columns = ['instId', 'instType', 'realizedPnl', 'upl', 'fundingRate']
positions_df = pd.DataFrame(columns=positions_columns)

# Store subscribed instrument IDs to avoid duplicate subscriptions
subscribed_instruments = set()


def on_private_message(ws, message):
    global positions_df
    message = json.loads(message)

    print(f"Received message: {message}")

    if message.get('event') == 'login':
        if message.get('code') == '0':
            print("Private WebSocket login successful")
            subscribe_positions(ws)
        else:
            print(f"Login failed: {message}")
    elif message.get('event') == 'subscribe':
        print(f"Subscribed to: {message.get('arg')}")
    else:
        # Handle position data
        if 'arg' in message and message['arg']['channel'] == 'positions':
            for pos in message['data']:
                instId = pos.get('instId')
                instType = pos.get('instType')
                realizedPnl = pos.get('realizedPnl')
                upl = pos.get('upl')

                # Check if the position already exists
                if instId in positions_df['instId'].values:
                    # Update existing position
                    positions_df.loc[positions_df['instId'] == instId, ['instType', 'realizedPnl', 'upl']] = [instType,
                                                                                                              realizedPnl,
                                                                                                              upl]
                else:
                    # Add new position
                    new_row = pd.DataFrame([[instId, instType, realizedPnl, upl, None]], columns=positions_columns)
                    positions_df = pd.concat([positions_df, new_row], ignore_index=True)

                # Subscribe to funding rate channel for the current instrument if it's a swap
                if instType == 'SWAP' and instId not in subscribed_instruments:
                    subscribe_funding_rate(public_ws, instId)
                    subscribed_instruments.add(instId)

            print("Updated positions DataFrame:")
            print(positions_df)


def on_error(ws, error):
    print(f"Error: {error}")


def on_close(ws):
    print("Connection closed")


def on_open_private(ws):
    print("Private connection opened")
    authenticate(ws)


def authenticate(ws):
    timestamp = str(int(time.time()))
    message = timestamp + 'GET' + '/users/self/verify'
    hmac_key = base64.b64encode(
        hmac.new(bytes(SECRET_KEY, 'utf-8'), bytes(message, 'utf-8'), digestmod=hashlib.sha256).digest())
    auth_data = {
        "op": "login",
        "args": [
            {
                "apiKey": API_KEY,
                "passphrase": PASSPHRASE,
                "timestamp": timestamp,
                "sign": hmac_key.decode('utf-8')
            }
        ]
    }
    ws.send(json.dumps(auth_data))


def subscribe_positions(ws):
    sub_data = {
        "op": "subscribe",
        "args": [{"channel": "positions", "instType": "ANY"}]
    }
    ws.send(json.dumps(sub_data))


def subscribe_funding_rate(ws, instId):
    sub_data = {
        "op": "subscribe",
        "args": [{"channel": "funding-rate", "instId": instId}]
    }
    ws.send(json.dumps(sub_data))


def on_public_message(ws, message):
    global positions_df
    message = json.loads(message)
    print(f"Received public message: {message}")
    # Handle funding rate updates
    if 'arg' in message and 'channel' in message['arg'] and message['arg'][
        'channel'] == 'funding-rate' and 'data' in message:
        for data in message['data']:
            instId = data.get('instId')
            fundingRate = data.get('fundingRate')
            if instId and fundingRate:
                positions_df.loc[positions_df['instId'] == instId, 'fundingRate'] = fundingRate
                print(f"Updated funding rate for instrument {instId}: {fundingRate}")
                print("Updated positions DataFrame:")
                print(positions_df)


def on_public_error(ws, error):
    print(f"Public WebSocket Error: {error}")


def on_public_close(ws):
    print("Public WebSocket connection closed")


def on_open_public(ws):
    print("Public WebSocket connection opened")


# Create WebSocket connections
private_ws = websocket.WebSocketApp(PRIVATE_WS_URL,
                                    on_message=on_private_message,
                                    on_error=on_error,
                                    on_close=on_close,
                                    on_open=on_open_private)

public_ws = websocket.WebSocketApp(PUBLIC_WS_URL,
                                   on_message=on_public_message,
                                   on_error=on_public_error,
                                   on_close=on_public_close,
                                   on_open=on_open_public)

# Run the WebSocket connections
private_ws_thread = threading.Thread(target=private_ws.run_forever)
public_ws_thread = threading.Thread(target=public_ws.run_forever)

private_ws_thread.start()
public_ws_thread.start()
