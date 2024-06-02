from .client import OkxClient
from .consts import *
from .RateLimiter import RateLimiter


class MarketAPI(OkxClient):
    def __init__(self, api_key='-1', api_secret_key='-1', passphrase='-1', use_server_time=None, flag='1', domain = 'https://www.okx.com',debug = True, proxy=None):
        OkxClient.__init__(self, api_key, api_secret_key, passphrase, use_server_time, flag, domain, debug, proxy)

    # Get tickers
    GET_TICKERS_SEMAPHORE = RateLimiter(20, 2)
    async def get_tickers(self, instType, uly='', instFamily =''):
        if uly:
            params = {'instType': instType, 'uly': uly, 'instFamily': instFamily}
        else:
            params = {'instType': instType, 'instFamily': instFamily}
            async with self.GET_TICKERS_SEMAPHORE:
                return await self._request_with_params(GET, TICKERS_INFO, params)

    # Get Ticker
    GET_TICKER_SEMAPHORE = RateLimiter(20, 2)
    async def get_ticker(self, instId):
        params = {'instId': instId}
        async with self.GET_TICKER_SEMAPHORE:
            return await self._request_with_params(GET, TICKER_INFO, params)

    # Get Index Tickers
    async def get_index_tickers(self, quoteCcy='', instId=''):
        params = {'quoteCcy': quoteCcy, 'instId': instId}
        return await self._request_with_params(GET, INDEX_TICKERS, params)

    # Get Order Book
    GET_ORDER_BOOK_SEMAPHORE = RateLimiter(40, 2)
    async def get_orderbook(self, instId, sz=''):
        params = {'instId': instId, 'sz': sz}
        async with self.GET_ORDER_BOOK_SEMAPHORE:
            return await self._request_with_params(GET, ORDER_BOOKS, params)

    # Get Candlesticks
    async def get_candlesticks(self, instId, after='', before='', bar='', limit=''):
        params = {'instId': instId, 'after': after, 'before': before, 'bar': bar, 'limit': limit}
        return await self._request_with_params(GET, MARKET_CANDLES, params)

        # GGet Candlesticks History（top currencies only）
    async def get_history_candlesticks(self, instId, after='', before='', bar='', limit=''):
        params = {'instId': instId, 'after': after, 'before': before, 'bar': bar, 'limit': limit}
        return await self._request_with_params(GET, HISTORY_CANDLES, params)

        # Get Index Candlesticks
    async def get_index_candlesticks(self, instId, after='', before='', bar='', limit=''):
        params = {'instId': instId, 'after': after, 'before': before, 'bar': bar, 'limit': limit}
        return await self._request_with_params(GET, INDEX_CANSLES, params)

        # Get Mark Price Candlesticks
    async def get_mark_price_candlesticks(self, instId, after='', before='', bar='', limit=''):
        params = {'instId': instId, 'after': after, 'before': before, 'bar': bar, 'limit': limit}
        return await self._request_with_params(GET, MARKPRICE_CANDLES, params)

        # Get Index Candlesticks
    async def get_trades(self, instId, limit=''):
        params = {'instId': instId, 'limit': limit}
        return await self._request_with_params(GET, MARKET_TRADES, params)

        # Get Volume
    async def get_volume(self):
        return await self._request_without_params(GET, VOLUMNE)

        # Get Oracle
    async def get_oracle(self):
        return await self._request_without_params(GET, ORACLE)

    # Get Tier
    async def get_tier(self, instType='', tdMode='', uly='', instId='', ccy='', tier=''):
        params = {'instType': instType, 'tdMode': tdMode, 'uly': uly, 'instId': instId, 'ccy': ccy, 'tier': tier}
        return await self._request_with_params(GET, TIER, params)

    #GET /api/v5/market/index-components
    async def get_index_components(self,index = ''):
        param = {
            'index':index
        }
        return await self._request_with_params(GET,INDEX_COMPONENTS,param)


    #GET /api/v5/market/exchange-rate
    async def get_exchange_rate(self):
        return await self._request_without_params(GET, EXCHANGE_RATE)

    #GET /api/v5/market/history-trades
    async def get_history_trades(self,instId = '',type = '',after = '',before = '',limit = ''):
        params = {
            'instId':instId,
            'type':type,
            'after':after,
            'before':before,
            'limit':limit
        }
        return await self._request_with_params(GET,HISTORY_TRADES,params)

    #GET /api/v5/market/block-ticker
    async def get_block_ticker(self,instId = ''):
        params = {
            'instId':instId
        }
        return await self._request_with_params(GET,BLOCK_TICKER,params)

    #GET /api/v5/market/block-tickers
    async def get_block_tickers(self,instType = '',uly = '', instFamily = ''):
        params = {
            'instType':instType,
            'uly':uly,
            'instFamily':instFamily
        }
        return await self._request_with_params(GET, BLOCK_TICKERS, params)

    #GET /api/v5/market/block-trades
    async def get_block_trades(self,instId = ''):
        params = {
            'instId':instId
        }
        return await self._request_with_params(GET, BLOCK_TRADES, params)

    #- Get order lite book
    async def get_order_lite_book(self,instId = ''):
        params = {
            'instId':instId
        }
        return await self._request_with_params(GET, GET_ORDER_LITE_BOOK, params)

    #- Get option trades
    async def get_option_trades(self,instFamily = ''):
        params = {
            'instFamily':instFamily
        }
        return await self._request_with_params(GET, GET_OPTION_TRADES, params)

