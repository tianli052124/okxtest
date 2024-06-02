from .client import OkxClient
from .consts import *
from .RateLimiter import RateLimiter


class PublicAPI(OkxClient):

    def __init__(self, api_key='-1', api_secret_key='-1', passphrase='-1', use_server_time=None, flag='1', domain = 'https://www.okx.com',debug = True, proxy=None):
        OkxClient.__init__(self, api_key, api_secret_key, passphrase, use_server_time, flag, domain, debug, proxy)

    # Get Instruments
    GET_INSTRUMENTS_SEMAPHORE = RateLimiter(20, 2)
    async def get_instruments(self, instType, uly='', instId='',instFamily = ''):
        params = {'instType': instType, 'uly': uly, 'instId': instId,'instFamily':instFamily}
        async with self.GET_INSTRUMENTS_SEMAPHORE:
            return await self._request_with_params(GET, INSTRUMENT_INFO, params)

    # Get Delivery/Exercise History
    async def get_delivery_exercise_history(self, instType, uly = '', after='', before='', limit='',instFamily = ''):
        params = {'instType': instType, 'uly': uly, 'after': after, 'before': before, 'limit': limit,'instFamily':instFamily}
        return await self._request_with_params(GET, DELIVERY_EXERCISE, params)

    # Get Open Interest
    async def get_open_interest(self, instType, uly='', instId='' ,instFamily =''):
        params = {'instType': instType, 'uly': uly, 'instId': instId,'instFamily':instFamily}
        return await self._request_with_params(GET, OPEN_INTEREST, params)

    # Get Funding Rate
    GET_FUNDING_RATE_SEMAPHORE = RateLimiter(20, 2)
    async def get_funding_rate(self, instId):
        params = {'instId': instId}
        async with self.GET_FUNDING_RATE_SEMAPHORE:
            return await self._request_with_params(GET, FUNDING_RATE, params)

    # Get Funding Rate History
    async def funding_rate_history(self, instId, after='', before='', limit=''):
        params = {'instId': instId, 'after': after, 'before': before, 'limit': limit}
        return await self._request_with_params(GET, FUNDING_RATE_HISTORY, params)

    # Get Limit Price
    async def get_price_limit(self, instId):
        params = {'instId': instId}
        return await self._request_with_params(GET, PRICE_LIMIT, params)

    # Get Option Market Data
    async def get_opt_summary(self, uly = '', expTime='',instFamily=''):
        params = {'uly': uly, 'expTime': expTime,'instFamily':instFamily}
        return await self._request_with_params(GET, OPT_SUMMARY, params)

    # Get Estimated Delivery/Excercise Price
    async def get_estimated_price(self, instId):
        params = {'instId': instId}
        return await self._request_with_params(GET, ESTIMATED_PRICE, params)

    # Get Discount Rate And Interest-Free Quota
    async def discount_interest_free_quota(self, ccy=''):
        params = {'ccy': ccy}
        return await self._request_with_params(GET, DICCOUNT_INTETEST_INFO, params)

    # Get System Time
    async def get_system_time(self):
        return await self._request_without_params(GET, SYSTEM_TIME)

    # Get Mark Price
    GET_MARK_PRICE_SEMAPHORE = RateLimiter(20, 2)
    async def get_mark_price(self, instType, uly='', instId='',instFamily = ''):
        params = {'instType': instType, 'uly': uly, 'instId': instId,'instFamily':instFamily}
        async with self.GET_MARK_PRICE_SEMAPHORE:
            return await self._request_with_params(GET, MARK_PRICE, params)

    # Get Tier
    async def get_position_tiers(self, instType, tdMode, uly='', instId='', ccy='', tier='',instFamily =''):
        params = {'instType': instType, 'tdMode': tdMode, 'uly': uly, 'instId': instId, 'ccy': ccy, 'tier': tier,'instFamily':instFamily}
        return await self._request_with_params(GET, TIER, params)

    #GET /api/v5/public/interest-rate-loan-quota
    async def get_interest_rate_loan_quota(self):
        return await self._request_without_params(GET,INTEREST_LOAN)

    #GET /api/v5/public/vip-interest-rate-loan-quota
    async def get_vip_interest_rate_loan_quota(self):
        return await self._request_without_params(GET, VIP_INTEREST_RATE_LOAN_QUOTA)

    #GET /api/v5/public/underlying
    async def get_underlying(self,instType = ''):
        params = {
            'instType':instType
        }
        return await self._request_with_params(GET, UNDERLYING, params)

    #GET /api/v5/public/insurance-fund
    async def get_insurance_fund(self,instType = '',type = '',uly = '',ccy='',before = '',after = '',limit = '',instFamily=''):
        params = {
            'instType':instType,
            'type':type,
            'uly':uly,
            'ccy':ccy,
            'before':before,
            'after':after,
            'limit':limit,
            'instFamily':instFamily
        }
        return await self._request_with_params(GET, INSURANCE_FUND, params)

    #GET /api/v5/public/convert-contract-coin
    async def get_convert_contract_coin(self,type = '',instId = '',sz = '',px = '',unit = ''):
        params = {
            'type':type,
            'instId':instId,
            'sz':sz,
            'px':px,
            'unit':unit
        }
        return await self._request_with_params(GET, CONVERT_CONTRACT_COIN, params)

    # Get option tickBands
    async def get_option_tickBands(self, instType='', instFamily=''):
        params = {
            'instType': instType,
            'instFamily': instFamily
        }
        return await self._request_with_params(GET, GET_OPTION_TICKBANDS, params)

    # Get option trades
    async def get_option_trades(self, instId='', instFamily='', optType=''):
        params = {
            'instId': instId,
            'instFamily': instFamily,
            'optType': optType
        }
        return await self._request_with_params(GET, GET_OPTION_TRADES, params)
