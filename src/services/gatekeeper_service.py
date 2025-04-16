from fastapi import FastAPI
import httpx

from src.core import config
from src.services.base import MicroserviceClient

class GatekeeperServiceClient(MicroserviceClient):

    def __init__(self, app: FastAPI):
        super().__init__(base_url=config.GATEKEEPER_URL, service_name="Gatekeeper", app=app)


    # Login to gatekeeper using credentials from config file
    @staticmethod
    async def gk_get_jwt_token() -> str:
        login_credentials = {
            'username': config.WEATHER_SRV_GATEKEEPER_USER,
            'password': config.WEATHER_SRV_GATEKEEPER_PASSWORD
        }

        async with httpx.AsyncClient() as client:
            url = f'{config.GATEKEEPER_URL}/api/login/'
            r = await client.post(url, data=login_credentials)
            r.raise_for_status()
            return (r.json()['access'], r.json()['refresh'])


    # Logout to gatekeeper using credentials from config file
    async def gk_logout(self, refresh_token):
        return await self.post('/api/logout/', json={"refresh": refresh_token})


    # List registered endpoints in gatekeeper
    async def gk_service_directory(self) -> dict:
        return await self.get('/api/service_directory/')


    # Register a specific endpoint and method in gatekeeper
    async def gk_service_register(self, service_data: dict) -> dict:
        return await self.post('/api/register_service/', json=service_data)
