# WebsocketManager.py

import asyncio
import websockets
import json
import hmac
import hashlib
import base64
import time
from okxv5_async.RateLimiter import RateLimiter

class WebSocketManager:
    def __init__(self, url, api_key=None, secret_key=None, passphrase=None):
        self.url = url
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.websocket = None


    async def connect(self, timeout=30):
        try:
            self.websocket = await asyncio.wait_for(websockets.connect(self.url), timeout=timeout)
            if self.api_key and self.secret_key and self.passphrase:
                await self.authenticate()
        except asyncio.exceptions.TimeoutError:
            print(f"Connection to {self.url} timed out.")
        except Exception as e:
            print(f"An error occurred while connecting to {self.url}: {e}")

    AUTHENTICATE_SEMAPHORE = RateLimiter(1, 1)
    async def authenticate(self):
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
        async with self.AUTHENTICATE_SEMAPHORE:
            await self.websocket.send(json.dumps(auth_data))

    SUBSCRIPTION_SEMAPHORE = RateLimiter(240, 3600)
    async def subscribe(self, channel, instType=None, instId=None):
        sub_data = {"op": "subscribe", "args": [{"channel": channel}]}
        if instType:
            sub_data["args"][0]["instType"] = instType
        if instId:
            sub_data["args"][0]["instId"] = instId
        async with self.SUBSCRIPTION_SEMAPHORE:
            await self.websocket.send(json.dumps(sub_data))

    async def unsubscribe(self, channel, instId):
        unsub_data = {"op": "unsubscribe", "args": [{"channel": channel, "instId": instId}]}
        await self.websocket.send(json.dumps(unsub_data))

    async def send_ping(self):
        try:
            await self.websocket.send('ping')
        except Exception as e:
            print(f"Error sending ping: {e}")

    async def receive(self):
        while True:
            try:
                message = await asyncio.wait_for(self.websocket.recv(), timeout=25)
                print("Message received, resetting timer.")
                yield json.loads(message)
            except asyncio.TimeoutError:
                print("No message received in 25 seconds, sending ping.")
                await self.send_ping()
                try:
                    pong = await asyncio.wait_for(self.websocket.recv(), timeout=5)
                    if pong != 'pong':
                        raise ValueError("Received message is not 'pong'")
                    print("Pong received, resetting timer.")
                except (asyncio.TimeoutError, ValueError):
                    print("No pong received in 5 seconds, reconnecting.")
                    await self.connect()

    async def close(self):
        await self.websocket.close()
