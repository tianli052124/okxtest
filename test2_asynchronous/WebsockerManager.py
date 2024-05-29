import asyncio
import websockets
import json
import hmac
import hashlib
import base64
import time

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
        await self.websocket.send(json.dumps(auth_data))

    async def subscribe(self, channel, instType=None, instId=None):
        sub_data = {"op": "subscribe", "args": [{"channel": channel}]}
        if instType:
            sub_data["args"][0]["instType"] = instType
        if instId:
            sub_data["args"][0]["instId"] = instId
        await self.websocket.send(json.dumps(sub_data))

    async def unsubscribe(self, channel, instId):
        unsub_data = {"op": "unsubscribe", "args": [{"channel": channel, "instId": instId}]}
        await self.websocket.send(json.dumps(unsub_data))

    async def send_ping(self):
        try:
            await self.websocket.send('ping')
            print("Ping sent")
        except Exception as e:
            print(f"Error sending ping: {e}")

    async def receive(self):
        async for message in self.websocket:
            yield json.loads(message)

    async def close(self):
        await self.websocket.close()
