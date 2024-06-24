import aiohttp
import ssl
import certifi


class HTTPService:
    def __init__(self):
        self.session = None
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())

    async def fetch_url(self, url, **params):
        async with self.session.get(url, ssl=self.ssl_context, **params) as response:
            return response

    async def connect(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()

    async def disconnect(self):
        if self.session:
            await self.session.close()
            self.session = None

    def get_session(self):
        if not self.session:
            raise RuntimeError("HTTP session is not initialized.")
        return self.session


# Create a single instance of HTTPService
http_service = HTTPService()


async def get_http_service():
    if not http_service.session:
        await http_service.connect()
    return http_service
