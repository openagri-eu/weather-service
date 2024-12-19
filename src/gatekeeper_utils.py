from fastapi import FastAPI
import httpx

from src.core import config


# Login to gatekeeper using credentials from config file
async def gk_login() -> str:
    login_credentials = {
        'username': config.WEATHER_SRV_GATEKEEPER_USER,
        'password': config.WEATHER_SRV_GATEKEEPER_PASSWORD
    }
    async with httpx.AsyncClient() as client:
        url = f'{config.GATEKEEPER_URL}:{config.GATEKEEPER_APP_PORT}/api/login/'
        r = await client.post(url, data=login_credentials)
        r.raise_for_status()
        return (r.json()['access'], r.json()['refresh'])


# Logout to gatekeeper using credentials from config file
async def gk_logout(refresh_token):
    async with httpx.AsyncClient() as client:
        url = f'{config.GATEKEEPER_URL}:{config.GATEKEEPER_APP_PORT}/api/logout/'
        r = await client.post(url, json={"refresh": refresh_token})
        r.raise_for_status()
        return


# List registered endpoints in gatekeeper
async def gk_service_directory(token: str) -> dict:
    async with httpx.AsyncClient() as client:
        headers = {
            "Authorization": f"Bearer {token}"
        }
        r = await client.get(f'{config.GATEKEEPER_URL}:{config.GATEKEEPER_APP_PORT}/api/service_directory/', headers=headers)
        r.raise_for_status()
        return r.json()


# Register a specific endpoint and method in gatekeeper
async def gk_service_register(token: str, service_data: dict) -> dict:
    async with httpx.AsyncClient() as client:
        headers = {
            "Authorization": f"Bearer {token}"
        }
        r = await client.post(f'{config.GATEKEEPER_URL}:{config.GATEKEEPER_APP_PORT}/api/register_service/', headers=headers, json=service_data)
        r.raise_for_status()
        return r.json()