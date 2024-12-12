from fastapi import FastAPI
import httpx

from src.core import config

GATEKEEPER_ACCESS_TOKEN = ''

# Login to gatekeeper using credentials from config file
async def gk_login():
    login_credentials = {
        'username': config.GATEKEEPER_USERNAME,
        'password': config.GATEKEEPER_PASSWORD
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(f'{config.GATEKEEPER_URL}/api/login/', data=login_credentials)
        r.raise_for_status()
        GATEKEEPER_ACCESS_TOKEN = r.json()['access']
        return r.json()['access']


# List registered endpoints in gatekeeper
async def gk_service_directory(token: str) -> dict:
    async with httpx.AsyncClient() as client:
        headers = {
            "Authorization": f"Bearer {token}"
        }
        r = await client.get(f'{config.GATEKEEPER_URL}/api/service_directory', headers=headers)
        r.raise_for_status()
        return r.json()


# Register a specific endpoint and method in gatekeeper
async def gk_service_register(token: str, service_data: dict) -> dict:
    async with httpx.AsyncClient() as client:
        headers = {
            "Authorization": f"Bearer {token}"
        }
        r = await client.post(f'{config.GATEKEEPER_URL}/api/service_directory', headers=headers, json=service_data)
        r.raise_for_status()
        return r.json()