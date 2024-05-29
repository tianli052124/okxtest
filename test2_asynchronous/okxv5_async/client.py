import httpx
from datetime import datetime, timezone
import json
from . import consts as c
from . import utils
from . import exceptions

import warnings


class OkxClient(httpx.AsyncClient):

    def __init__(self, api_key='-1', api_secret_key='-1', passphrase='-1', use_server_time=None, flag='1',
                 base_api=c.API_URL, debug='True', proxy=None):
        super().__init__(base_url=base_api, http2=True, proxy=proxy)
        self.API_KEY = api_key
        self.API_SECRET_KEY = api_secret_key
        self.PASSPHRASE = passphrase
        self.use_server_time = False
        self.flag = flag
        self.domain = base_api
        self.debug = debug
        if use_server_time is not None:
            warnings.warn("use_server_time parameter is deprecated. Please remove it.", DeprecationWarning)

    async def _request(self, method, request_path, params):
        if method == c.GET:
            request_path = request_path + utils.parse_params_to_str(params)
        timestamp = utils.get_timestamp()
        if self.use_server_time:
            timestamp = await self._get_timestamp()
        body = json.dumps(params) if method == c.POST else ""
        if self.API_KEY != '-1':
            sign = utils.sign(utils.pre_hash(timestamp, method, request_path, str(body), self.debug),
                              self.API_SECRET_KEY)
            header = utils.get_header(self.API_KEY, sign, timestamp, self.PASSPHRASE, self.flag, self.debug)
        else:
            header = utils.get_header_no_sign(self.flag, self.debug)
        response = None
        if self.debug == True:
            print('domain:', self.domain)
            print('url:', request_path)
        if method == c.GET:
            response = await self.get(request_path, headers=header)
        elif method == c.POST:
            response = await self.post(request_path, data=body, headers=header)
        return response.json()

    async def _request_without_params(self, method, request_path):
        return await self._request(method, request_path, {})

    async def _request_with_params(self, method, request_path, params):
        return await self._request(method, request_path, params)

    async def _get_timestamp(self):
        request_path = c.API_URL + c.SERVER_TIMESTAMP_URL
        response = await self.get(request_path)
        if response.status_code == 200:
            ts = datetime.fromtimestamp(int(response.json()['data'][0]['ts']) / 1000.0, tz=timezone.utc)
            return ts.isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        else:
            return ""